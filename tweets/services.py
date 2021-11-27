from tweets.models import TweetPhoto, Tweet
from twitter.cache import USER_TWEETS_PATTERN
from utils.redis_helper import RedisHelper


def lazy_load_tweets(user_id):
    def _lazy_load(limit):
        return Tweet.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
    return _lazy_load


class TweetService:

    @classmethod
    def create_photos_from_files(cls, tweet, files):
        photos = []
        for index, file in enumerate(files):
            photo = TweetPhoto(
                tweet=tweet,
                user=tweet.user,
                file=file,
                order=index,
            )
            photos.append(photo)

        TweetPhoto.objects.bulk_create(photos)

    @classmethod
    def get_cached_tweets(cls, user_id):
        # queryset 是 lazy loading 模式，
        # 未真正访问 / 转换成 list 结果，就不会真正触发数据库的查询
        key = USER_TWEETS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(
            key=key,
            lazy_load_func=lazy_load_tweets(user_id)
        )

    @classmethod
    def push_tweet_to_cache(cls, tweet):
        key = USER_TWEETS_PATTERN.format(user_id=tweet.user_id)
        RedisHelper.push_object(
            key=key,
            obj=tweet,
            lazy_load_func=lazy_load_tweets(tweet.user_id)
        )
