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

        # lisa 能看到 2 个 notifications
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # emma 看不到任何 notifications
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

        # 验证不能用get
        response = self.lisa_client.get(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # emma 不能把 lisa 的 notifications 标记成已读
        response = self.emma_client.post(NOTIFICATION_MARK_ALL_AS_READ_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 0)
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # lisa 成功把自己的 notification 标记为全部已读
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

        # 验证匿名用户无法访问 api
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # emma 看不到任何 notifications
        response = self.emma_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

        # lisa 看到两个 notifications
        response = self.lisa_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # 验证标记之后只看到一个未读
        notification = self.lisa.notifications.first()
        notification.unread = False
        notification.save()
        response = self.lisa_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.lisa_client.get(NOTIFICATION_URL, {'unread': True}) # 针对 filterset_fields 筛选
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

        # 验证 post 不行，需要用 put
        response = self.emma_client.post(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 验证不可以被其他人改变 notification 状态
        response = self.anonymous_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 因为 queryset 是按照当前登陆用户来，所以会返回 404 而不是 403
        response = self.emma_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 成功标记为已读
        response = self.lisa_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 1)

        # 再标记为未读
        response = self.lisa_client.put(url, {'unread': True})
        response = self.lisa_client.get(NOTIFICATION_UNREAD_COUNT_URL)
        self.assertEqual(response.data['unread_count'], 2)

        # 验证必须带 unread
        response = self.lisa_client.put(url, {'verb': 'newverb'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证不可修改其他的信息
        response = self.lisa_client.put(url, {'verb': 'newverb', 'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()  # 重新载入，确保变量 notification 存的是 database 的信息
        self.assertNotEqual(notification.verb, 'newverb')
