from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import pre_delete, post_save

from likes.listeners import decr_likes_count, incr_likes_count
from utils.memcached_helper import MemcachedHelper


# Create your models here.
class Like(models.Model):
    """
    可以点赞一个 tweet，也可以点赞一个 comment
    """

    # https://docs.djangoproject.com/en/3.1/ref/contrib/contenttypes/#generic-relations
    object_id = models.PositiveIntegerField()  # tweet_id or comment_id
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
    )
    # user liked content_object at created_at
    content_object = GenericForeignKey('content_type', 'object_id') # 并不会实际记录在表单当中，只是一个快捷方式
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 实际存储在 db 中的 field 为：id, object_id, content_type_id, user_id, created_at

    class Meta:
        # 这里使用 unique together 也就会建一个 <user, content_type, object_id> 的索引。
        # web 是高并发环境，可能会同时创建两个相同 like，必须从数据库层面确保是 unique 的
        # 这个索引同时还可以具备查询某个 user like 了哪些不同的 objects 的功能
        # 因此如果 unique together 改成 <content_type, object_id, user> 就没有这样的效果了
        unique_together = (('user', 'content_type', 'object_id'),)
        index_together = (
            ('content_type', 'object_id', 'created_at'), # 可以按时间排序某个被 like 的 content_object 的所有 likes
            ('user', 'content_type', 'created_at'), # 查询某个 user 在哪些 tweet/comment 上点了赞
        )

    def __str__(self):
        return '{} - {} liked {} {}'.format(
            self.created_at,
            self.user,
            self.content_type,
            self.object_id,
        )

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)


pre_delete.connect(decr_likes_count, sender=Like)
post_save.connect(incr_likes_count, sender=Like)
