from rest_framework import serializers
from accounts.api.serializers import UserSerializerForTweet, UserSerializer
from comments.api.serializers import CommentSerializer
from likes.api.serializers import LikeSerializer
from likes.services import LikeService
from tweets.models import Tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()  # 会返回具体user被serialize过的信息，若不指定只会返回user_id
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()

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
        )

    def get_comments_count(self, obj):
        """
        查看有多少人评论了当前 object (tweet)
        """
        return obj.comment_set.count()  # django的ForeignKey的反查机制

    def get_likes_count(self, obj):
        """
        查看有多少人点赞了当前 object (tweet)
        """
        return obj.like_set.count()  # like_set为自定义的 Tweet 的 property

    def get_has_liked(self, obj):
        """
        查看当前登录的用户是否赞过这个 object (tweet)
        """
        return LikeService.has_liked(user=self.context['request'].user, target=obj)


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)

    class Meta:
        model = Tweet
        fields = ('content',)  # 'user_id'应根据当前用户状态，而不可作为写入的field

    # will be called when save() is called
    def create(self, validated_data):
        user = self.context['request'].user  # 根据当前用户登陆状态
        content = validated_data['content']
        tweet = Tweet.objects.create(user=user, content=content)
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
        )
