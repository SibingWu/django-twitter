from django.utils import timezone
from rest_framework import status

from comments.models import Comment
from testing.testcases import TestCase
from rest_framework.test import APIClient

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class CommentApiTests(TestCase):

    def setUp(self):
        super(CommentApiTests, self).setUp()
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

        # 验证 content 太长不行
        response = self.lisa_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,  # max_length=140
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content' in response.data['errors'], True)

        # 验证 tweet_id 和 content 都带才行
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

    def test_list(self):
        # 验证必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证带了 tweet_id 可以访问
        # 一开始没有评论
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 0)

        # 验证评论按照时间顺序排序
        self.create_comment(self.lisa, self.tweet, '1')
        self.create_comment(self.emma, self.tweet, '2')
        self.create_comment(self.emma, self.create_tweet(self.emma), '3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 验证同时提供 user_id 和 tweet_id 只有 tweet_id 会在 filter 中生效
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.lisa.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.lisa)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.emma_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments_count'], 0)

        # test tweet list api
        self.create_comment(self.lisa, tweet)
        response = self.emma_client.get(TWEET_LIST_API, {'user_id': self.lisa.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['comments_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.emma, tweet)
        self.create_newsfeed(self.emma, tweet)
        response = self.emma_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['tweet']['comments_count'], 2)

    def test_comments_count_with_cache(self):
        tweet_url = '/api/tweets/{}/'.format(self.tweet.id)
        response = self.lisa_client.get(tweet_url)
        self.assertEqual(self.tweet.comments_count, 0)
        self.assertEqual(response.data['comments_count'], 0)

        data = {'tweet_id': self.tweet.id, 'content': 'a comment'}
        for i in range(2):
            _, client = self.create_user_and_client('user{}'.format(i))
            client.post(COMMENT_URL, data)
            response = client.get(tweet_url)
            self.assertEqual(response.data['comments_count'], i + 1)
            self.tweet.refresh_from_db()
            self.assertEqual(self.tweet.comments_count, i + 1)

        comment_data = self.emma_client.post(COMMENT_URL, data).data
        response = self.emma_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # update comment shouldn't update comments_count
        comment_url = '{}{}/'.format(COMMENT_URL, comment_data['id'])
        response = self.emma_client.put(comment_url, {'content': 'updated'})
        self.assertEqual(response.status_code, 200)
        response = self.emma_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # delete a comment will update comments_count
        response = self.emma_client.delete(comment_url)
        self.assertEqual(response.status_code, 200)
        response = self.lisa_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 2)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 2)
