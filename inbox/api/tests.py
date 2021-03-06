from notifications.models import Notification
from rest_framework import status

from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'
NOTIFICATION_UNREAD_COUNT_URL = '/api/notifications/unread-count/'
NOTIFICATION_MARK_ALL_AS_READ_URL = '/api/notifications/mark-all-as-read/'
NOTIFICATION_UPDATE_URL = '/api/notifications/{}/'


class NotificationTests(TestCase):

    def setUp(self):
        super(NotificationTests, self).setUp()
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


class NotificationApiTests(TestCase):

    def setUp(self):
        self.lisa, self.lisa_client = self.create_user_and_client('lisa')
        self.emma, self.emma_client = self.create_user_and_client('emma')
        self.lisa_tweet = self.create_tweet(self.lisa)

    def test_unread_count(self):
        self.emma_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.lisa_tweet.id,
        })

        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(self.lisa, self.lisa_tweet)
        self.emma_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        # lisa ????????? 2 ??? notifications
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # emma ??????????????? notifications
        response = self.emma_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 0)

    def test_mark_all_as_read(self):
        self.emma_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.lisa_tweet.id,
        })
        comment = self.create_comment(self.lisa, self.lisa_tweet)
        self.emma_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # ???????????????get
        response = self.lisa_client.get(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # emma ????????? lisa ??? notifications ???????????????
        response = self.emma_client.post(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 0)
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # lisa ?????????????????? notification ?????????????????????
        response = self.lisa_client.post(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.emma_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.lisa_tweet.id,
        })
        comment = self.create_comment(self.lisa, self.lisa_tweet)
        self.emma_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        # ?????????????????????????????? api
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # emma ??????????????? notifications
        response = self.emma_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

        # lisa ???????????? notifications
        response = self.lisa_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # ???????????????????????????????????????
        notification = self.lisa.notifications.first()
        notification.unread = False
        notification.save()
        response = self.lisa_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.lisa_client.get(NOTIFICATION_URL, {'unread': True}) # ?????? filterset_fields ??????
        self.assertEqual(response.data['count'], 1)
        response = self.lisa_client.get(NOTIFICATION_URL, {'unread': False})
        self.assertEqual(response.data['count'], 1)

    def test_update(self):
        self.emma_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.lisa_tweet.id,
        })
        comment = self.create_comment(self.lisa, self.lisa_tweet)
        self.emma_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })
        notification = self.lisa.notifications.first()

        url = NOTIFICATION_UPDATE_URL.format(notification.id)

        # ?????? post ?????????????????? put
        response = self.emma_client.post(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # ????????????????????????????????? notification ??????
        response = self.anonymous_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # ?????? queryset ???????????????????????????????????????????????? 404 ????????? 403
        response = self.emma_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # ?????????????????????
        response = self.lisa_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 1)

        # ??????????????????
        response = self.lisa_client.put(url, {'unread': True})
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # ??????????????? unread
        response = self.lisa_client.put(url, {'verb': 'newverb'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # ?????????????????????????????????
        response = self.lisa_client.put(url, {'verb': 'newverb', 'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()  # ??????????????????????????? notification ????????? database ?????????
        self.assertNotEqual(notification.verb, 'newverb')
