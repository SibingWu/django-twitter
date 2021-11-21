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
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            friendships = HBaseFollower.filter(prefix=(to_user_id, None))
        else:
            friendships = Friendship.objects.filter(to_user_id=to_user_id)
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):
        # TODO: cache in redis set
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            friendships = HBaseFollowing.filter(prefix=(from_user_id, None))
        else:
            friendships = Friendship.objects.filter(from_user_id=from_user_id)

        user_id_set = set([
            friendship.to_user_id
            for friendship in friendships
        ])
        return user_id_set

    @classmethod
    def invalidate_following_cache(cls, from_user_id):
        """
        若数据库出现更新，为了防止并发导致的不一致性，一般直接失效 key
        """
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        cache.delete(key)

    @classmethod
    def get_follow_instance(cls, from_user_id, to_user_id):
        followings = HBaseFollowing.filter(prefix=(from_user_id, None))
        for follow in followings:
            if follow.to_user_id == to_user_id:
                return follow
        return None

    @classmethod
    def has_followed(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return False

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # MySQL
            return Friendship.objects.filter(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            ).exists()

        instance = cls.get_follow_instance(from_user_id, to_user_id)
        return instance is not None

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

    @classmethod
    def unfollow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return 0

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # MySQL
            # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#delete
            # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
            # 为什么会出现多种类型数据的删除？因为可能因为 foreign key 设置了 cascade 出现级联
            # 删除，也就是比如 A model 的某个属性是 B model 的 foreign key，并且设置了
            # on_delete=models.CASCADE, 那么当 B 的某个数据被删除的时候，A 中的关联也会被删除。
            # 所以 CASCADE 是很危险的，我们一般最好不要用，而是用 on_delete=models.SET_NULL
            # 取而代之，这样至少可以避免误删除操作带来的多米诺效应。
            deleted, _ = Friendship.objects.filter(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            ).delete()
            return deleted

        # HBase
        instance = cls.get_follow_instance(from_user_id, to_user_id)
        if instance is None:
            return 0

        HBaseFollowing.delete(from_user_id=from_user_id, created_at=instance.created_at)
        HBaseFollower.delete(to_user_id=to_user_id, created_at=instance.created_at)
        return 1

    @classmethod
    def get_following_count(cls, from_user_id):
        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # MySQL
            return Friendship.objects.filter(from_user_id=from_user_id).count()
        # HBase
        followings = HBaseFollowing.filter(prefix=(from_user_id, None))
        return len(followings)
