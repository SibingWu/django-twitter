from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForTweet, UserSerializer
from comments.api.serializers import CommentSerializer
from likes.api.serializers import LikeSerializer
from likes.services import LikeService
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from tweets.models import Tweet
from tweets.services import TweetService


class TweetSerializer(serializers.ModelSerializer):
    # 会返回具体user被serialize过的信息，若不指定只会返回user_id
    user = UserSerializerForTweet()
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    photo_urls = serializers.SerializerMethodField()

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',
            'comments_count',
            'likes_count',
            'has_liked',
            'photo_urls',
        )

    def get_comments_count(self, obj: Tweet):
        """
        查看有多少人评论了当前 object (tweet)
        """
        return obj.comment_set.count()  # django的ForeignKey的反查机制

    def get_likes_count(self, obj: Tweet):
        """
        查看有多少人点赞了当前 object (tweet)
        """
        return obj.like_set.count()  # like_set为自定义的 Tweet 的 property

    def get_has_liked(self, obj: Tweet):
        """
        查看当前登录的用户是否赞过这个 object (tweet)
        """
        return LikeService.has_liked(
            user=self.context['request'].user,
            target=obj
        )

    def get_photo_urls(self, obj: Tweet):
        """
        查看当前 obj (tweet) 上传的 photo
        """
        photo_urls = []
        for photo in obj.tweetphoto_set.all().order_by('order'):
            photo_urls.append(photo.file.url)
        return photo_urls


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=True,
        required=False,
    )

    class Meta:
        model = Tweet
        fields = ('content', 'files')
        # 'user_id'应根据当前用户状态，而不可作为写入的field

    def validate(self, data):
        # 上传照片数不可超过上限
        if len(data.get('files', [])) > TWEET_PHOTOS_UPLOAD_LIMIT:
            raise ValidationError({
                'message': f'You can only upload at most '
                           f'{TWEET_PHOTOS_UPLOAD_LIMIT} photos'
            })
        return data

    # will be called when save() is called
    def create(self, validated_data):
        user = self.context['request'].user  # 根据当前用户登陆状态
        content = validated_data['content']
        tweet = Tweet.objects.create(user=user, content=content)

        # 若有上传 photo，则需创建对应的文件
        if validated_data.get('files'):
            TweetService.create_photos_from_files(
                tweet=tweet,
                files=validated_data['files'],
            )

        return tweet


class TweetSerializerForDetail(TweetSerializer):
    user = UserSerializer()
    comments = CommentSerializer(source='comment_set', many=True)
    likes = LikeSerializer(source='like_set', many=True)

    # # 使用 serializers.SerializerMethodField 实现 comments
    # comments = serializers.SerializerMethodField()
    #
    # def get_comments(self, obj):
    #     return CommentSerializer(obj.comment_set.all(), many=True).data

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'comments',
            'created_at',
            'content',
            'likes',
            'comments',
            'likes_count',
            'comments_count',
            'has_liked',
            'photo_urls',
        )
