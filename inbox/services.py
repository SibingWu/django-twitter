from django.contrib.contenttypes.models import ContentType
from notifications.signals import notify

from comments.models import Comment
from likes.models import Like
from tweets.models import Tweet


class NotificationService:

    @classmethod
    def send_like_notification(cls, like: Like):
        target = like.content_object

        # 点赞的人与点赞的对象相同
        if like.user == target.user:
            return

        # 点赞了一条 tweet
        if like.content_type == ContentType.objects.get_for_model(Tweet):
            notify.send(
                sender=like.user,
                recipient=target.user,
                verb='liked your tweet',
                target=target,
            )

        # 点赞了一个 comment
        if like.content_type == ContentType.objects.get_for_model(Comment):
            notify.send(
                sender=like.user,
                recipient=target.user,
                verb='liked your comment',
                target=target,
            )

    @classmethod
    def send_comment_notification(cls, comment: Comment):
        # 评论的人与被评论的 tweet 的发起人相同
        if comment.user == comment.tweet.user:
            return

        notify.send(
            sender=comment.user,
            recipient=comment.tweet.user,
            verb='commented on your tweet',
            target=comment.tweet,
        )
