from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper


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

        # bulk create 不会触发 post_save 的 signal，所以需要手动 push 到 cache 里
        # post_save 的 signal 只会单个触发，不会批量触发，所以得手动写触发机制
        for newsfeed in newsfeeds:
            cls.push_newsfeed_to_cache(newsfeed)

        # 其实若是一个 1kw 粉丝的博主发了一个 144字节的 tweet，
        # 如果把整个 tweet 去 fan out 到 1kw 粉丝中，会给 redis 的内存带来 1G 的耗费
        # 可进一步优化：在 newsfeed cache 中，不直接存储整个 tweet，而是只存 tweet id
        # 即不是把整个 newsfeed push 进 cache，而是只是 push 有哪些 id
        # 但这里可以不优化的原因：newsfeed 在 serialize 时，
        # 只有 user_id，tweet_id，和 created_at，并没有整条 tweet

        # 本质优化方法：对于明星用户，不要用 push model，而要用 pull model

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        # queryset 是 lazy loading 模式，
        # 未真正访问 / 转换成 list 结果，就不会真正触发数据库的查询
        queryset = NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(key, queryset)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        queryset = NewsFeed.objects.filter(user_id=newsfeed.user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_object(key, newsfeed, queryset)
