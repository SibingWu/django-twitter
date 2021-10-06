from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from friendships.services import FriendshipService


class FollowingUserIdSetMixin:

    @property
    def following_user_id_set(self: serializers.ModelSerializer):
        """
        通过一次的 cache 访问将当前登录用户的 following user id 存进 object level 的内存中，
        甚至都无需访问 memcached 的 cache

        object level cache: 存在进程的内存中
        当一个 HTTP request 的请求结束后，该空间会被释放掉
        """
        if self.context['request'].user.is_anonymous:
            return {}
        if hasattr(self, '_cached_following_user_id_set'):
            return self._cached_following_user_id_set
        user_id_set = FriendshipService.get_following_user_id_set(
            self.context['request'].user.id,
        )
        setattr(self, '_cached_following_user_id_set', user_id_set)
        return user_id_set


class FollowerSerializer(serializers.ModelSerializer, FollowingUserIdSetMixin):
    # 可以通过 source=xxx 指定去访问每个 model instance 的 xxx field或property
    # 即 model_instance.xxx 来获得数据
    user = UserSerializerForFriendship(source='cached_from_user')
    created_at = serializers.DateTimeField()
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj: Friendship):
        # if self.context['request'].user.is_anonymous:
        #     return False
        # # 这个部分会对每个 object 都去执行一次 SQL 查询，速度会很慢，如何优化呢？
        # # 我们将在后序优化中会用 cache 解决这个问题
        # return FriendshipService.has_followed(
        #     from_user=self.context['request'].user,
        #     to_user=obj.from_user,
        # )

        # 将数据库查询转化为对 cache 的查询
        return obj.from_user_id in self.following_user_id_set


class FollowingSerializer(serializers.ModelSerializer, FollowingUserIdSetMixin):
    user = UserSerializerForFriendship(source='cached_to_user')
    created_at = serializers.DateTimeField()
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj: Friendship):
        # if self.context['request'].user.is_anonymous:
        #     return False
        # # 这个部分会对每个 object 都去执行一次 SQL 查询，速度会很慢，如何优化呢？
        # # 我们将在后序优化中会用 cache 解决这个问题
        # return FriendshipService.has_followed(
        #     from_user=self.context['request'].user,
        #     to_user=obj.to_user,
        # )
        return obj.to_user_id in self.following_user_id_set


class FriendshipSerializerForCreate(serializers.ModelSerializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()

    class Meta:
        model = Friendship
        fields = ('from_user_id', 'to_user_id')

    def validate(self, attrs):
        if attrs['from_user_id'] == attrs['to_user_id']:
            raise ValidationError({
                'message': 'from_user_id and to_user_id should be different'
            })

        if not User.objects.filter(id=attrs['to_user_id']).exists():
            raise ValidationError({
                'message': 'You cannot follow a non-exist user.',
            })

        return attrs

    def create(self, validated_data):
        from_user_id = validated_data['from_user_id']
        to_user_id = validated_data['to_user_id']
        return Friendship.objects.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
        )
