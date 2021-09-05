from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializer
from comments.models import Comment
from likes.models import Like
from tweets.models import Tweet


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Like
        fields = ('user', 'created_at',)


class BaseLikeSerializerForCreateAndCancel(serializers.ModelSerializer):
    # choices 可以与前端约定，因为这个并非写在数据库中的
    content_type = serializers.ChoiceField(choices=['comment', 'tweet'])
    object_id = serializers.IntegerField()

    class Meta:
        model = Like
        fields = ('content_type', 'object_id',)

    def _get_model_class(self, data):
        if data['content_type'] == 'comment':
            return Comment
        if data['content_type'] == 'tweet':
            return Tweet
        return None

    def validate(self, data):
        # 验证 content_type 是否合法
        model_class = self._get_model_class(data)
        if model_class is None:
            raise ValidationError({
                'content_type': 'Content type does not exist'
            })

        # 验证被点赞的 object 是否存在
        # liked_object = model_class.objects.filter(id=data['object_id']).first()
        # if liked_object is None:
        if not model_class.objects.filter(id=data['object_id']).exists():
            raise ValidationError({
                'object_id': 'Object does not exist'
            })

        return data


class LikeSerializerForCreate(BaseLikeSerializerForCreateAndCancel):

    def get_or_create(self):
        validated_data = self.validated_data
        model_class = self._get_model_class(validated_data)
        # 只能创建一次，故用 get_or_create
        instance, created = Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model=model_class),
            object_id=validated_data['object_id'],
            user=self.context['request'].user,
        )
        return instance, created


class LikeSerializerForCancel(BaseLikeSerializerForCreateAndCancel):

    def cancel(self):
        """
        cancel 方法是一个自定义的方法，cancel 不会被 serializer.save 调用
        所以需要直接调用 serializer.cancel()
        """
        model_class = self._get_model_class(self.validated_data)
        # 无论 filter 返回是否为空， delete 方法都不会报错，可以删除多项，也可以删除零项
        # 故不需要特意查看 user 是否点过这个赞
        deleted, _ = Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model_class),
            object_id=self.validated_data['object_id'],
            user=self.context['request'].user,
        ).delete()
        return deleted
