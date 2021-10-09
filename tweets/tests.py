from datetime import timedelta

from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto
from tweets.services import TweetService
from twitter.cache import USER_TWEETS_PATTERN
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from utils.time_helpers import utc_now


# Create your tests here.
class TweetTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.lisa = self.create_user(username='lisa')
        self.tweet = self.create_tweet(user=self.lisa)

    def test_hours_to_now(self):
        self.tweet.created_at = utc_now() - timedelta(hours=10)
        self.tweet.save()
        self.assertEqual(self.tweet.hours_to_now, 10)

    def test_like_set(self):
        # 自己给自己点赞
        self.create_like(user=self.lisa, target=self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        # 验证只能点赞一次
        self.create_like(user=self.lisa, target=self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        # 别人给自己点赞
        emma = self.create_user(username='emma')
        self.create_like(user=emma, target=self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 2)

    def test_create_photo(self):
        # 测试可以成功创建 TweetPhoto 的数据对象
        photo = TweetPhoto.objects.create(
            tweet=self.tweet,
            user=self.lisa,
        )
        self.assertEqual(photo.user, self.lisa)
        self.assertEqual(photo.status, TweetPhotoStatus.PENDING)
        self.assertEqual(self.tweet.tweetphoto_set.count(), 1)  # 反查机制

    def test_cache_tweet_in_redis(self):
        # 将 tweet 存进 redis 中
        tweet = self.create_tweet(self.lisa)
        conn = RedisClient.get_connection()
        serialized_data = DjangoModelSerializer.serialize(tweet)
        conn.set(f'tweet:{tweet.id}', serialized_data)
        data = conn.get(f'tweet:not_exists')
        self.assertEqual(data, None)

        # 测试可以成功读取 redis 中刚刚创建的 tweet
        data = conn.get(f'tweet:{tweet.id}')
        cached_tweet = DjangoModelSerializer.deserialize(data)
        self.assertEqual(tweet, cached_tweet)  # 发现是两个 ORM model，会比较内容


class TweetServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.lisa = self.create_user('lisa')

    def test_get_user_tweets(self):
        tweet_ids = []
        for i in range(3):
            tweet = self.create_tweet(self.lisa, 'tweet {}'.format(i))
            tweet_ids.append(tweet.id)
        tweet_ids = tweet_ids[::-1]

        RedisClient.clear()
        conn = RedisClient.get_connection()

        # cache miss
        tweets = TweetService.get_cached_tweets(self.lisa.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

        # cache hit
        tweets = TweetService.get_cached_tweets(self.lisa.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

        # cache updated
        new_tweet = self.create_tweet(self.lisa, 'new tweet')
        tweets = TweetService.get_cached_tweets(self.lisa.id)
        tweet_ids.insert(0, new_tweet.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

    def test_create_new_tweet_before_get_cached_tweets(self):
        tweet1 = self.create_tweet(self.lisa, 'tweet1')

        RedisClient.clear()
        conn = RedisClient.get_connection()

        key = USER_TWEETS_PATTERN.format(user_id=self.lisa.id)
        self.assertEqual(conn.exists(key), False)
        tweet2 = self.create_tweet(self.lisa, 'tweet2')
        self.assertEqual(conn.exists(key), True)

        tweets = TweetService.get_cached_tweets(self.lisa.id)
        self.assertEqual([t.id for t in tweets], [tweet2.id, tweet1.id])
