from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from friendships.api.paginations import FriendshipPagination
from friendships.api.serializers import (
    FollowerSerializer,
    FollowingSerializer, FriendshipSerializerForCreate,
)
from friendships.models import Friendship


class FriendshipViewSet(viewsets.GenericViewSet):
    # 希望 POST /api/friendships/1/follow/ 是当前用户去 follow user_id=1 的用户
    queryset = User.objects.all()
    serializer_class = FriendshipSerializerForCreate
    # 一般来说，不同的 views 所需要的 pagination 规则肯定是不同的，因此一般都需要自定义
    pagination_class = FriendshipPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followers(self, request: Request, pk):
        """
        GET /api/friendships/<pk>/followers/ 返回 user_id=<pk> 的用户的所有粉丝
        """
        friendships = Friendship.objects.filter(to_user_id=pk)\
            .order_by('-created_at')
        page = self.paginate_queryset(queryset=friendships)
        serializer = FollowerSerializer(
            instance=page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followings(self, request: Request, pk):
        """
        GET /api/friendships/<pk>/followings/ 返回 user_id=<pk> 的用户关注的所有用户
        """
        friendships = Friendship.objects.filter(from_user_id=pk)\
            .order_by('-created_at')
        page = self.paginate_queryset(queryset=friendships)
        serializer = FollowingSerializer(
            instance=page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def follow(self, request: Request, pk):
        """
        POST /api/friendships/<pk>/follow/ 当前用户去关注 user_id=<pk> 的用户
        """

        # 特殊判断重复 follow 的情况（比如前端猛点好多少次 follow)
        # 静默处理，不报错，因为这类重复操作因为网络延迟的原因会比较多，没必要当做错误处理
        if Friendship.objects\
                .filter(from_user_id=request.user.id, to_user_id=pk)\
                .exists():
            return Response({
                'success': True,
                'duplicate': True,
            }, status=status.HTTP_201_CREATED)

        # check if user with id-pk exists
        self.get_object()

        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': pk,
        })

        # validate input
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({
            'success': True,
        }, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def unfollow(self, request: Request, pk):
        """
        POST /api/friendships/<pk>/unfollow/ 当前用户去取关 user_id=<pk> 的用户
        """

        # raise 404 if no user with id-pk
        unfollow_user = self.get_object()

        # # 注意 pk 的类型是 str，所以要做类型转换
        # if request.user.id == int(pk):
        if request.user.id == unfollow_user.id:
            return Response({
                'success': False,
                'message': 'You cannot unfollow yourself.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
        deleted, _ = Friendship.objects.filter(
            from_user_id=request.user.id,
            to_user_id=pk,
        ).delete()
        return Response({
            'success': True,
            'deleted': deleted,
        })

    def list(self, request: Request):
        """
        GET /api/friendships/
        便于在根目录页面显示
        """
        return Response({'message': 'This is friendship home page'})

