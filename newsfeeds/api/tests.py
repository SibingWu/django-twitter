from rest_framework import status
from rest_framework.test import APIClient

from testing.testcases import TestCase

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.lisa = self.create_user(username='lisa')
        self.lisa_client = APIClient()
        self.lisa_client.force_authenticate(self.lisa)

        self.emma = self.create_user(username='emma')
        self.emma_client = APIClient()
        self.emma_client.force_authenticate(self.emma)

    def test_list(self):
        # 验证需要登录
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 验证不能用 post
        response = self.lisa_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 验证一开始啥都没有
        response = self.lisa_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['newsfeeds']), 0)
        # 验证自己发的信息是可以看到的
        self.lisa_client.post(POST_TWEETS_URL, {'content': 'Hello World'})
        response = self.lisa_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 1)
        # 验证关注之后可以看到别人发的
        self.lisa_client.post(FOLLOW_URL.format(self.emma.id))
        response = self.emma_client.post(POST_TWEETS_URL, {
            'content': 'Hello Twitter',
        })
        posted_tweet_id = response.data['id']
        response = self.lisa_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 2)  # 看到自己发了一条，看到emma发了一条
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['id'], posted_tweet_id)
