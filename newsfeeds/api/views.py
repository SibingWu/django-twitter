from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    # def get_queryset(self):
    #     # 重载以自定义 queryset，因为 newsfeed 的查看是有权限的
    #     # 只能看 user=当前登录用户的 newsfeed
    #     return NewsFeed.objects.filter(user_id=self.request.user.id)

    def list(self, request: Request):
        """
        GET /api/newsfeeds/
        """
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        # 用 EndlessPagination 的自己实现的 paginated_cached_list
        page = self.paginator.paginate_cached_list(cached_newsfeeds, request)
        # page 是 None 说明我现在请求的数据可能不在 cache 里，需要直接去 db 获取
        if page is None:
            queryset = NewsFeed.objects.filter(user=request.user)
            page = self.paginate_queryset(queryset)
        serializer = NewsFeedSerializer(
            instance=page,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(data=serializer.data)
