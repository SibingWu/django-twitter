from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import caches

from accounts.models import UserProfile
from twitter.cache import USER_PROFILE_PATTERN
from utils.memcached_helper import MemcachedHelper

cache = caches['testing'] if settings.TESTING else caches['default']


class UserService:

    @classmethod
    def get_user_by_id(cls, user_id):
        return MemcachedHelper.get_object_through_cache(User, user_id)

    @classmethod
    def get_profile_through_cache(cls, user_id):
        # 该方法无法被 MemcachedHelper.get_object_through_cache 取代，
        # 因为这里取的不是user profile id，而是 user id
        key = USER_PROFILE_PATTERN.format(user_id=user_id)

        # read from cache first
        profile = cache.get(key)
        # cache hit, return
        if profile is not None:
            return profile

        # cache miss, read from db
        # 因为历史原因，user profile 是后面加进来的。可能有一些历史数据没有 profile
        profile, _ = UserProfile.objects.get_or_create(user_id=user_id)
        cache.set(key, profile)
        return profile

    @classmethod
    def invalidate_profile(cls, user_id):
        key = USER_PROFILE_PATTERN.format(user_id=user_id)
        cache.delete(key)
