from django.utils import timezone
from rest_framework import status

from comments.models import Comment
from testing.testcases import TestCase
from rest_framework.test import APIClient


COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'


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

    def test_destroy(self):
        comment = self.create_comment(self.lisa, self.tweet)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # 验证匿名不可以删除
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 验证非本人不能删除
        response = self.emma_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 验证本人可以删除
        count = Comment.objects.count()
        response = self.lisa_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.lisa, self.tweet, 'original')
        another_tweet = self.create_tweet(self.emma)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # 使用 put 的情况下
        # 验证匿名不可以更新
        response = self.anonymous_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 验证非本人不能更新
        response = self.emma_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotEqual(comment.content, 'new')
        # 验证不能更新除 content 外的内容，静默处理，只更新内容
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()
        response = self.lisa_client.put(url, {
            'content': 'new',
            'user_id': self.emma.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()  # 从 db 中把被更新的 comment 给 load 进来以替换还存在内存中的 comment
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.lisa)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)
