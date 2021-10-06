from rest_framework import status
from rest_framework.test import APIClient

from testing.testcases import TestCase
from utils.paginations import EndlessPagination

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
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
        self.assertEqual(len(response.data['results']), 0)
        # 验证自己发的信息是可以看到的
        self.lisa_client.post(POST_TWEETS_URL, {'content': 'Hello World'})
        response = self.lisa_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)
        # 验证关注之后可以看到别人发的
        self.lisa_client.post(FOLLOW_URL.format(self.emma.id))
        response = self.emma_client.post(POST_TWEETS_URL, {
            'content': 'Hello Twitter',
        })
        posted_tweet_id = response.data['id']
        response = self.lisa_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)  # 看到自己发了一条，看到emma发了一条
        self.assertEqual(response.data['results'][0]['tweet']['id'], posted_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeed = self.create_newsfeed(user=self.lisa, tweet=tweet)
            newsfeeds.append(newsfeed)

        newsfeeds = newsfeeds[::-1]

        # pull the first page
        response = self.lisa_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # pull the second page
        response = self.lisa_client.get(
            NEWSFEEDS_URL,
            {'created_at__lt': newsfeeds[page_size - 1].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[2 * page_size - 1].id,
        )

        # pull latest newsfeeds
        response = self.lisa_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(followed_user)
        new_newsfeed = self.create_newsfeed(user=self.lisa, tweet=tweet)

        response = self.lisa_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        # newsfeeds -> tweet -> user -> profile
        # update in profile ---> update in newsfeeds

        # change user profile
        profile = self.emma.profile
        profile.nickname = 'emma nickname'
        profile.save()

        self.assertEqual(self.lisa.username, 'lisa')
        self.create_newsfeed(self.emma, self.create_tweet(self.lisa))
        self.create_newsfeed(self.emma, self.create_tweet(self.emma))

        # validate change in newsfeeds
        response = self.emma_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'emma')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'emma nickname')
        self.assertEqual(results[1]['tweet']['user']['username'], 'lisa')

        # change user profile
        self.lisa.username = 'lisa wu'
        self.lisa.save()
        # change emma profile again
        profile.nickname = 'emma nickname2'
        profile.save()

        # validate change in newsfeeds
        response = self.emma_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'emma')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'emma nickname2')
        self.assertEqual(results[1]['tweet']['user']['username'], 'lisa wu')
