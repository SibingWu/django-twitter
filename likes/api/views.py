from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from likes.api.serializers import LikeSerializerForCreate, LikeSerializer
from likes.models import Like
from utils.decorators import required_params


class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LikeSerializerForCreate

    @required_params(request_attr='data', params=['content_type', 'object_id'])
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

        like = serializer.save()
        return Response(
            data=LikeSerializer(instance=like).data,
            status=status.HTTP_201_CREATED,
        )
