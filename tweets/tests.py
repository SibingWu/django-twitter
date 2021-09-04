from datetime import timedelta

from testing.testcases import TestCase
from utils.time_helpers import utc_now


# Create your tests here.
class TweetTests(TestCase):

    def setUp(self):
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
