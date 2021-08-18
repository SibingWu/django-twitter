from rest_framework import status
from rest_framework.test import APIClient
from testing.testcases import TestCase


# 注意要加 '/' 结尾，要不然会产生 301 redirect
from tweets.models import Tweet

TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'


class TweetApiTests(TestCase):

    def setUp(self):
        self.user1 = self.create_user(username='user1', email='user1@twitter.com')
        self.tweets1 = [
            self.create_tweet(user=self.user1)
            for _ in range(3)
        ]
        self.user1_client = APIClient()
        self.user1_client.force_authenticate(user=self.user1)  # 强制用user1用户去访问所有API

        self.user2 = self.create_user(username='user2', email='user2@twitter.com')
        self.tweets2 = [
            self.create_tweet(user=self.user2)
            for _ in range(2)
        ]

    def test_list_api(self):
        # 验证必须在参数列表中带user_id
        response = self.anonymous_client.get(TWEET_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 正常request
        response = self.anonymous_client.get(TWEET_LIST_API, {'user_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tweets']), 3)

        response = self.anonymous_client.get(TWEET_LIST_API, {'user_id': self.user2.id})
        self.assertEqual(len(response.data['tweets']), 2)
        # 检测排序是按照新创建的在前面的顺序来的，即按created_at倒序排列
        self.assertEqual(response.data['tweets'][0]['id'], self.tweets2[1].id)
        self.assertEqual(response.data['tweets'][1]['id'], self.tweets2[0].id)

    def test_create_api(self):
        # 验证必须登录
        response = self.anonymous_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 验证必须带 content
        response = self.user1_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 验证content 不能太短
        response = self.user1_client.post(TWEET_CREATE_API, {'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 验证content 不能太长
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': '0' * 141
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 正常发帖
        tweets_count = Tweet.objects.count()
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'Hello World, this is my first tweet!'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(Tweet.objects.count(), tweets_count + 1)
