from rest_framework import serializers

from newsfeeds.models import NewsFeed
from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.ModelSerializer):
    tweet = TweetSerializer()  # 因 TweetSerializer 中需传入 context，故用到 NewsFeedSerializer 的地方也需要传入context

    class Meta:
        model = NewsFeed
        fields = ('id', 'created_at', 'tweet')  # 不需要user，TweetSerializer中包含user
