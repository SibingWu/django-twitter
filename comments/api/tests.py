from rest_framework import status

from testing.testcases import TestCase
from rest_framework.test import APIClient


COMMENT_URL = '/api/comments/'


class CommentApiTests(TestCase):

    def setUp(self):
        self.lisa = self.create_user('lisa')
        self.lisa_client = APIClient()
        self.lisa_client.force_authenticate(self.lisa)

        self.emma = self.create_user('emma')
        self.emma_client = APIClient()
        self.emma_client.force_authenticate(self.emma)

        self.tweet = self.create_tweet(self.lisa)

    def test_create(self):
        # 验证匿名不可以创建
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 验证啥参数都没带不行
        response = self.lisa_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证只带 tweet_id 不行
        response = self.lisa_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证只带 content 不行
        response = self.lisa_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证content 太长不行
        response = self.lisa_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,  # max_length=140
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content' in response.data['errors'], True)

        # 验证tweet_id 和 content 都带才行
        response = self.lisa_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.lisa.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')
