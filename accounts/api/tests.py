from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserProfile
from testing.testcases import TestCase


LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL_URL = '/api/profiles/{}/'


class AccountApiTests(TestCase):

    def setUp(self):
        # 这个函数会在每个 test function 执行的时候被执行
        self.clear_cache()
        self.client = APIClient()
        self.user = self.create_user(
            username='test',
            email='test@twitter.com',
            password='correct password',
        )

    def test_login(self):
        # 每个测试函数必须以 test_ 开头，才会被自动调用进行测试

        # 验证必须用 post 而不是 get
        response = self.client.get(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # 登陆失败，http status code 返回 405 = METHOD_NOT_ALLOWED
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 用了 post 但是密码错了
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证还没有登录
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

        # 用正确的密码登录
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['user'], None)
        self.assertEqual(response.data['user']['id'], self.user.id)
        # 验证已经登录了
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # 用了 post 但是username错了
        response = self.client.post(LOGIN_URL, {
            'username': 'not_exists',
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout(self):
        # 先登录
        self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # 验证用户已经登录
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # 验证必须用 post 而不是 get
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 改用 post 成功 logout
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 验证用户已经登出
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'someone',
            'email': 'someone@twitter.com',
            'password': 'any password',
        }

        # 验证 get 请求失败
        response = self.client.get(SIGNUP_URL, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 测试错误的邮箱
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'not a correct email',
            'password': 'any password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 测试过短密码
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'someone@twitter.com',
            'password': '123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 测试过长用户名
        response = self.client.post(SIGNUP_URL, {
            'username': 'username is tooooooooooooooooo loooooooong',
            'email': 'someone@twitter.com',
            'password': 'any password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证成功注册
        response = self.client.post(SIGNUP_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'someone')

        # 验证 user profile 已经被创建
        created_user_id = response.data['user']['id']
        profile = UserProfile.objects.filter(user_id=created_user_id).first()
        self.assertNotEqual(profile, None)

        # 验证用户已经登入
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)


class UserProfileAPITests(TestCase):

    def test_update(self):
        lisa, lisa_client = self.create_user_and_client('lisa')
        profile = lisa.profile
        profile.nickname = 'old nickname'
        profile.save()
        url = USER_PROFILE_DETAIL_URL.format(profile.id)

        # anonymous user cannot update profile
        response = self.anonymous_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')

        # test can only be updated by user himself.
        _, emma_client = self.create_user_and_client('emma')
        response = emma_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'You do not have permission to access this object')
        profile.refresh_from_db()
        self.assertEqual(profile.nickname, 'old nickname') # emma did not update successfully

        # update nickname
        response = lisa_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertEqual(profile.nickname, 'a new nickname')

        # update avatar
        response = lisa_client.put(url, {
            'avatar': SimpleUploadedFile(
                name='my-avatar.jpg',
                content=str.encode('a fake image'),
                content_type='image/jpeg',
            ),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual('my-avatar' in response.data['avatar'], True)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.avatar)
