from django.contrib.auth.models import User
from django.db import models

from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from tweets.models.tweet import Tweet


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
