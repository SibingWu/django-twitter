from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed


class NewsFeedService:

    @classmethod
    def fanout_to_followers(cls, tweet):
        # 获取当前发帖人的所有粉丝
        newsfeeds = [
            NewsFeed(user=follower, tweet=tweet)
            for follower in FriendshipService.get_followers(tweet.user)
        ]
        newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))  # 自己也能看自己发的帖子

        # 一次性写入
        NewsFeed.objects.bulk_create(objs=newsfeeds)
