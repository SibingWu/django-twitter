from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from newsfeeds.tasks import fanout_newsfeeds_main_task
from testing.testcases import TestCase

from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_client import RedisClient


# Create your tests here.
class NewsFeedServiceTests(TestCase):

    def setUp(self):
        super(NewsFeedServiceTests, self).setUp()
        self.lisa = self.create_user('lisa')
        self.emma = self.create_user('emma')

    def test_get_user_newsfeeds(self):
        newsfeed_ids = []
        for i in range(3):
            tweet = self.create_tweet(self.emma)
            newsfeed = self.create_newsfeed(self.lisa, tweet)
            newsfeed_ids.append(newsfeed.id)
        newsfeed_ids = newsfeed_ids[::-1]

        # cache miss
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # cache hit
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # cache updated
        tweet = self.create_tweet(self.lisa)
        new_newsfeed = self.create_newsfeed(self.lisa, tweet)
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        newsfeed_ids.insert(0, new_newsfeed.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

    def test_create_new_newsfeed_before_get_cached_newsfeeds(self):
        feed1 = self.create_newsfeed(self.lisa, self.create_tweet(self.lisa))

        RedisClient.clear()
        conn = RedisClient.get_connection()

        key = USER_NEWSFEEDS_PATTERN.format(user_id=self.lisa.id)
        self.assertEqual(conn.exists(key), False)
        feed2 = self.create_newsfeed(self.lisa, self.create_tweet(self.lisa))
        self.assertEqual(conn.exists(key), True)

        feeds = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        self.assertEqual([f.id for f in feeds], [feed2.id, feed1.id])


class NewsFeedTaskTests(TestCase):

    def setUp(self):
        super(NewsFeedTaskTests, self).setUp()
        self.lisa = self.create_user('lisa')
        self.emma = self.create_user('emma')

    def test_fanout_main_task(self):
        tweet = self.create_tweet(self.lisa, 'tweet 1')
        self.create_friendship(self.emma, self.lisa)
        msg = fanout_newsfeeds_main_task(tweet.id, self.lisa.id)
        self.assertEqual(msg, '1 newsfeeds going to fanout, 1 batches created.')
        self.assertEqual(1 + 1, NewsFeed.objects.count())
        cached_list = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        self.assertEqual(len(cached_list), 1)

        for i in range(2):
            user = self.create_user('user{}'.format(i))
            self.create_friendship(user, self.lisa)
        tweet = self.create_tweet(self.lisa, 'tweet 2')
        msg = fanout_newsfeeds_main_task(tweet.id, self.lisa.id)
        self.assertEqual(msg, '3 newsfeeds going to fanout, 1 batches created.')
        self.assertEqual(4 + 2, NewsFeed.objects.count())
        cached_list = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        self.assertEqual(len(cached_list), 2)

        user = self.create_user('another user')
        self.create_friendship(user, self.lisa)
        tweet = self.create_tweet(self.lisa, 'tweet 3')
        msg = fanout_newsfeeds_main_task(tweet.id, self.lisa.id)
        self.assertEqual(msg, '4 newsfeeds going to fanout, 2 batches created.')
        self.assertEqual(8 + 3, NewsFeed.objects.count())
        cached_list = NewsFeedService.get_cached_newsfeeds(self.lisa.id)
        self.assertEqual(len(cached_list), 3)
        cached_list = NewsFeedService.get_cached_newsfeeds(self.emma.id)
        self.assertEqual(len(cached_list), 3)
