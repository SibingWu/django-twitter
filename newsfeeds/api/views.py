from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from gatekeeper.models import GateKeeper
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.services import NewsFeedService
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        # 重载以自定义 queryset，因为 newsfeed 的查看是有权限的
        # 只能看 user=当前登录用户的 newsfeed
        return NewsFeed.objects.filter(user_id=self.request.user.id)

    @method_decorator(ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request: Request):
        """
        GET /api/newsfeeds/
        """
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        # 用 EndlessPagination 的自己实现的 paginated_cached_list
        paginator = self.paginator
        page = paginator.paginate_cached_list(cached_newsfeeds, request)
        # page 是 None 说明我现在请求的数据可能不在 cache 里，需要直接去 db 获取
        if page is None:
            if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
                page = paginator.paginate_hbase(
                    HBaseNewsFeed,
                    (request.user.id,),
                    request
                )
            else:
                queryset = NewsFeed.objects.filter(user=request.user)
                page = paginator.paginate_queryset(queryset=queryset, request=request)

        serializer = NewsFeedSerializer(
            instance=page,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(data=serializer.data)
