from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from inbox.services import NotificationService
from likes.api.serializers import (
    LikeSerializerForCreate,
    LikeSerializer,
    LikeSerializerForCancel,
)
from likes.models import Like
from utils.decorators import required_params


class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LikeSerializerForCreate

    @required_params(method='POST', params=['content_type', 'object_id'])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def create(self, request: Request):
        """
        POST /api/likes/
        """
        serializer = LikeSerializerForCreate(
            data=request.data,
            context={'request': request},  # 用 context 传入当前登录的用户是谁
        )

        # validate input
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        like, created = serializer.get_or_create()

        # send notification for newly created like
        if created:
            NotificationService.send_like_notification(like)

        return Response(
            data=LikeSerializer(instance=like).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=False)
    @required_params(method='POST', params=['content_type', 'object_id'])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def cancel(self, request: Request):
        """
        POST /api/likes/cancel/
        """
        serializer = LikeSerializerForCancel(
            data=request.data,
            context={'request': request},
        )

        # validate input
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted = serializer.cancel()
        return Response({
            'success': True,
            'deleted': deleted,
        }, status=status.HTTP_200_OK)
