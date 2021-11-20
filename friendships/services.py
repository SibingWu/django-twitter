import time

from django.conf import settings
from django.core.cache import caches

from friendships.hbase_models import HBaseFollower, HBaseFollowing
from friendships.models import Friendship
from gatekeeper.models import GateKeeper
from twitter.cache import FOLLOWINGS_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class FriendshipService:

    @classmethod
    def get_followers(cls, user):
        # friendships = Friendship.objects.filter(to_user=user)
        # follower_ids = [friendship.from_user_id for friendship in friendships]
        # followers = User.objects.filter(id__in=follower_ids)

        friendships = Friendship.objects.filter(
            to_user=user
        ).prefetch_related('from_user')  # 避免 N + 1 Queries 的问题
        followers = [friendship.from_user for friendship in friendships]
        return followers

    @classmethod
    def get_follower_ids(cls, to_user_id):
        friendships = Friendship.objects.filter(to_user_id=to_user_id)
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):
        """
        通过一次的数据库访问将当前登录用户的 following user id 存进 memcached 的 cache 中

        多台 web 服务器访问同一个 memcached，都能得到数据，
        且 HTTP request 结束后，缓存空间并不会释放，
        除非 1.超时了 2.手动删除 3.内存不够用了，LRU 策略 evict
        """
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        user_id_set = cache.get(key)
        if user_id_set is not None:
            return user_id_set

        # cache miss，则从数据库中取
        friendships = Friendship.objects.filter(from_user_id=from_user_id)
        user_id_set = set([
            friendship.to_user_id
            for friendship in friendships
        ])
        cache.set(key, user_id_set)
        return user_id_set

    @classmethod
    def invalidate_following_cache(cls, from_user_id):
        """
        若数据库出现更新，为了防止并发导致的不一致性，一般直接失效 key
        """
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        cache.delete(key)

    @classmethod
    def follow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return None

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # create data in mysql
            return Friendship.objects.create(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            )

        # create data in hbase
        now = int(time.time() * 1000000)
        HBaseFollower.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )
        return HBaseFollowing.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )
