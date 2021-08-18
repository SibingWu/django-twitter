from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 重载以自定义 queryset，因为 newsfeed 的查看是有权限的
        # 只能看 user=当前登录用户的 newsfeed
        return NewsFeed.objects.filter(user_id=self.request.user.id)

    def list(self, request: Request):
        serializer = NewsFeedSerializer(instance=self.get_queryset(), many=True)
        return Response({
            'newsfeeds': serializer.data
        }, status=status.HTTP_200_OK)
