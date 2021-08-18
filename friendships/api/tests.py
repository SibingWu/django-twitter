from rest_framework import status
from rest_framework.test import APIClient

from friendships.models import Friendship
from testing.testcases import TestCase

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

    def setUp(self):
        self.lisa = self.create_user(username='lisa')
        self.lisa_client = APIClient()
        self.lisa_client.force_authenticate(self.lisa)

        self.emma = self.create_user(username='emma')
        self.emma_client = APIClient()
        self.emma_client.force_authenticate(self.emma)

        # create followings and followers for emma
        for i in range(2):
            follower = self.create_user('emma_follower{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.emma)
        for i in range(3):
            following = self.create_user('emma_following{}'.format(i))
            Friendship.objects.create(from_user=self.emma, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL.format(self.lisa.id)

        # 验证需要登录才能 follow 别人
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 验证要用 get 来 follow
        response = self.emma_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 验证不可以 follow 自己
        response = self.lisa_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # follow 成功
        response = self.emma_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # 重复 follow 静默成功
        response = self.emma_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['duplicate'], True)
        # 验证反向关注会创建新的数据
        count = Friendship.objects.count()
        response = self.lisa_client.post(FOLLOW_URL.format(self.emma.id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Friendship.objects.count(), count + 1)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.lisa.id)

        # 验证需要登录才能 unfollow 别人
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 验证不能用 get 来 unfollow 别人
        response = self.emma_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 验证不能用 unfollow 自己
        response = self.lisa_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # unfollow 成功
        Friendship.objects.create(from_user=self.emma, to_user=self.lisa)
        count = Friendship.objects.count()
        response = self.emma_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        # 验证未 follow 的情况下 unfollow 静默处理
        count = Friendship.objects.count()
        response = self.emma_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 0)  # 未删掉任何数据
        self.assertEqual(Friendship.objects.count(), count)

    def test_followings(self):
        url = FOLLOWINGS_URL.format(self.emma.id)
        # 验证不能用 post
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 用 get 成功获取
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['followings']), 3)
        # 验证按照时间倒序
        ts0 = response.data['followings'][0]['created_at']
        ts1 = response.data['followings'][1]['created_at']
        ts2 = response.data['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['followings'][0]['user']['username'],
            'emma_following2',
        )
        self.assertEqual(
            response.data['followings'][1]['user']['username'],
            'emma_following1',
        )
        self.assertEqual(
            response.data['followings'][2]['user']['username'],
            'emma_following0',
        )

    def test_followers(self):
        url = FOLLOWERS_URL.format(self.emma.id)
        # 验证不能用 post
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 用 get 成功获取
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['followers']), 2)
        # 验证按照时间倒序
        ts0 = response.data['followers'][0]['created_at']
        ts1 = response.data['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['followers'][0]['user']['username'],
            'emma_follower1',
        )
        self.assertEqual(
            response.data['followers'][1]['user']['username'],
            'emma_follower0',
        )
