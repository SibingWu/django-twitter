from rest_framework import serializers
from accounts.api.serializers import UserSerializerForTweet
from tweets.models import Tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'created_at', 'content')


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
