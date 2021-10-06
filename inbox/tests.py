from notifications.models import Notification

from inbox.services import NotificationService
from testing.testcases import TestCase


# Create your tests here.
class NotificationServiceTest(TestCase):

    def setUp(self):
        self.clear_cache()
        self.lisa = self.create_user('lisa')
        self.emma = self.create_user('emma')
        self.lisa_tweet = self.create_tweet(self.lisa)

    def test_send_comment_notification(self):
        # do not dispatch notification if tweet user == comment user
        comment = self.create_comment(self.lisa, self.lisa_tweet)
        NotificationService.send_comment_notification(comment)
        self.assertEqual(Notification.objects.count(), 0)

        # dispatch notification if tweet user != comment user
        comment = self.create_comment(self.emma, self.lisa_tweet)
        NotificationService.send_comment_notification(comment)
        self.assertEqual(Notification.objects.count(), 1)

    def test_send_like_notification(self):
        # do not dispatch notification if tweet user == like user
        like = self.create_like(self.lisa, self.lisa_tweet)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 0)

        # dispatch notification if tweet user != like user
        like = self.create_like(self.emma, self.lisa_tweet)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 1)

        # do not dispatch notification if comment user == like user
        emma_comment = self.create_comment(self.emma, self.lisa_tweet)
        like = self.create_like(self.emma, emma_comment)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 1) # 之前已有一个 Notification object

        # dispatch notification if comment user != like user
        emma_comment = self.create_comment(self.emma, self.lisa_tweet)
        like = self.create_like(self.lisa, emma_comment)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 2)
