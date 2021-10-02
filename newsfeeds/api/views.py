from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        # 重载以自定义 queryset，因为 newsfeed 的查看是有权限的
        # 只能看 user=当前登录用户的 newsfeed
        return NewsFeed.objects.filter(user_id=self.request.user.id)

    def list(self, request: Request):
        """
        GET /api/newsfeeds/
        """
        page = self.paginate_queryset(self.get_queryset())
        serializer = NewsFeedSerializer(
            instance=page,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(data=serializer.data)
