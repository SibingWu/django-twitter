from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_delete

from likes.models import Like
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from tweets.listeners import push_tweet_to_cache
from utils.listeners import invalidate_object_cache
from utils.memcached_helper import MemcachedHelper
from utils.time_helpers import utc_now


# Create your models here.
class Tweet(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='who posts this tweet',
    )
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    # 新增的 field 一定要设置 null=True，否则 default = 0 会遍历整个表单去设置
    # 导致 Migration 过程非常慢，从而把整张表单锁死，从而正常用户无法创建新的 tweets
    # 原有的数据需要在数据迁移后，用额外的回填脚本把 0 填上，这样不会锁死表单
    likes_count = models.IntegerField(default=0, null=True)
    comments_count = models.IntegerField(default=0, null=True)

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at')

    def __str__(self):
        # 这里是你执行 print(tweet instance) 的时候会显示的内容
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def hours_to_now(self):
        # datetime.now 不带时区信息，需要增加上 utc 的时区信息
        return (utc_now() - self.created_at).seconds // 3600

    # @property
    # def comments(self):
    #     # return Comment.objects.filter(tweet=self)
    #     return self.comment_set.all()  # 使用 comment_set 反向查询无需import Comment，避免了 recursive import

    @property
    def like_set(self):
        """
        模仿反查机制，返回 tweet 下的所有点赞
        """

        # 只与当前 model 有关，不传入参数的，需在 models.py 中定义
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)


class TweetPhoto(models.Model):
    # 图片在哪个 Tweet 下面
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # 谁上传了这张图片，这个信息虽然可以从 tweet 中通过 tweet.user 获取到，
    # 但是重复的记录在 TweetPhoto 里可以在使用上带来很多便利，
    # 比如某个人经常上传一些不合法的照片，那么这个人新上传的照片可以被标记为重点审查对象。
    # 或者我们需要封禁某个用户上传的所有照片的时候，就可以通过这个 model 快速进行筛选
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # 图片文件
    file = models.FileField()
    order = models.IntegerField(default=0)  # 同一个 tweet 下上传多张照片的顺序

    # 图片状态，用于审核等情况
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # 软删除(soft delete)标记，当一个照片被删除的时候，首先会被标记为已经被删除，在一定时间之后才会被真正的删除。
    # 这样做的目的是，如果在 tweet 被删除的时候马上执行真删除的通常会花费一定的时间，影响效率。
    # 可以用异步任务在后台慢慢做真删除。
    # 而且软删除可以类似一个回收站
    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('user', 'created_at'),  # 查询某个用户发的所有照片，按时间排序
            ('has_deleted', 'created_at'),  # 查询最近被删除的照片
            ('status', 'created_at'),  # 查询所有 pending 的照片
            ('tweet', 'order'),  # 查询同一个 tweet 下的所有照片，按 order 排序
        )

    def __str__(self):
        return f'{self.tweet_id}: {self.file}'

# hook up with listeners to invalidate cache
pre_delete.connect(invalidate_object_cache, sender=Tweet)
post_save.connect(invalidate_object_cache, sender=Tweet)
post_save.connect(push_tweet_to_cache, sender=Tweet)
