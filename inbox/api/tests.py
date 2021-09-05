from notifications.models import Notification

from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'


class NotificationTests(TestCase):

    def setUp(self):
        self.lisa, self.lisa_client = self.create_user_and_client('lisa')
        self.emma, self.emma_client = self.create_user_and_client('emma')
        self.emma_tweet = self.create_tweet(self.emma)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.lisa_client.post(COMMENT_URL, {
            'tweet_id': self.emma_tweet.id,
            'content': 'a ha',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.lisa_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.emma_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)
