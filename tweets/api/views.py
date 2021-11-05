from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from newsfeeds.services import NewsFeedService
from tweets.api.serializers import (
    TweetSerializerForCreate,
    TweetSerializer,
    TweetSerializerForDetail,
)
from tweets.models import Tweet
from tweets.services import TweetService
from utils.decorators import required_params
from utils.paginations import EndlessPagination


class TweetViewSet(viewsets.GenericViewSet):
    """
    API endpoint that allows users to create, list tweets
    """
    queryset = Tweet.objects.all()
    serializer_class = TweetSerializerForCreate
    pagination_class = EndlessPagination

    def get_permissions(self):
        # self.action对应具体的带request的方法
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @required_params(method='GET', params=['user_id'])
    def list(self, request: Request):
        """
        GET /api/tweets/?user_id=xxx
        重载 list 方法，不列出所有 tweets，必须要求指定 user_id 作为筛选条件
        """

        # tweets = Tweet.objects.filter(
        #     user_id=request.query_params['user_id']
        # ).order_by('-created_at')

        # tweets = TweetService.get_cached_tweets(
        #     user_id=request.query_params['user_id'],
        # )
        # tweets = self.paginate_queryset(tweets)  # 增加翻页

        user_id = request.query_params['user_id']
        # tweets = Tweet.objects.filter(user_id=user_id).prefetch_related('user')
        cached_tweets = TweetService.get_cached_tweets(user_id)
        page = self.paginator.paginate_cached_list(cached_tweets, request)
        if page is None:
            # 这句查询会被翻译为
            # select * from twitter_tweets
            # where user_id = xxx
            # order by created_at desc
            # 这句 SQL 查询会用到 user 和 created_at 的联合索引
            # 单纯的 user 索引是不够的
            queryset = Tweet.objects.filter(user_id=user_id).order_by('-created_at')
            page = self.paginate_queryset(queryset)
        serializer = TweetSerializer(
            instance=page,
            context={'request': request},
            many=True,  # list of dict
        )
        # 一般来说 json 格式的 response 默认都要用 hash/dict 的格式
        # 而不能用 list 的格式（约定俗成）
        return self.get_paginated_response(data=serializer.data)

    @method_decorator(ratelimit(key='user_or_ip', rate='5/s', method='GET', block=True))
    def retrieve(self, request: Request, *args, **kwargs):
        """
        GET /api/tweets/<pk>/
        展示某一条具体的 tweet
        """
        tweet = self.get_object()
        return Response(
            data=TweetSerializerForDetail(
                instance=tweet,
                context={'request': request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @method_decorator(ratelimit(key='user', rate='1/s', method='POST', block=True))
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def create(self, request: Request):
        """
        POST /api/tweets/
        重载 create 方法，因为需要默认用当前登录用户作为 tweet.user
        """
        serializer = TweetSerializerForCreate(
            data=request.data,
            context={'request': request},  # 通过context传递额外参数给serializer
        )

        # validate input
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # save() will trigger create() method in TweetSerializerForCreate
        tweet = serializer.save()  # 存入数据库

        # news feed流进行fan out
        NewsFeedService.fanout_to_followers(tweet)

        # 使用展示的serializer
        serializer = TweetSerializer(
            instance=tweet,
            context={'request': request},
        )
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )
