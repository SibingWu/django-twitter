from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from likes.models import Like


class LikeService:

    @classmethod
    def has_liked(cls, user: User, target):
        """
        查看 user 是否点赞过这个 object (tweet / comment)
        """
        if user.is_anonymous:
            return False

        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.id,
            user=user,
        ).exists()
