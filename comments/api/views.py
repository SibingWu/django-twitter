from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from comments.api.permissions import IsObjectOwner
from comments.api.serializers import (
    CommentSerializerForCreate,
    CommentSerializerForUpdate,
    CommentSerializer,
)
from comments.models import Comment


class CommentViewSet(viewsets.GenericViewSet):
    """
    只实现 list, create, update, destroy 的方法
    不实现 retrieve（查询单个 comment） 的方法，因为没这个需求
    """
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    filterset_fields = ('tweet_id',)  # 用 filterset_fields去filter queryset

    def get_permissions(self):
        # 注意要加用 AllowAny() / IsAuthenticated() 实例化出对象
        # 而不是 AllowAny / IsAuthenticated 这样只是一个类名
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['destroy', 'update']:
            return [IsAuthenticated(), IsObjectOwner()]
        return [AllowAny()]

    def list(self, request: Request):
        """
        重载 list 方法，不列出所有 comments，
        必须要求指定 tweet_id 作为筛选条件，列出某 tweet 下的所有 comments
        GET /api/comments/?tweet_id=xxx
        """
        if 'tweet_id' not in request.query_params:
            return Response({
                'message': 'missing tweet_id in request',
                'success': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        # tweet_id = request.query_params['tweet_id']
        # comments = Comment.objects.filter(tweet_id=tweet_id).order_by('created_at')

        # 使用 django-filter
        queryset = self.get_queryset()  # 取到被 filter 后的 queryset
        comments = self.filter_queryset(queryset=queryset)\
            .prefetch_related('user')\
            .order_by('created_at')
        serializer = CommentSerializer(instance=comments, many=True)

        return Response({
            'comments': serializer.data,
        }, status=status.HTTP_200_OK)

    def create(self, request: Request):
        """
        POST /api/comments/
        """
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        # 注意这里必须要加 'data=' 来指定参数是传给 data 的
        # 因为默认的第一个参数是 instance
        serializer = CommentSerializerForCreate(data=data)

        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save()
        return Response(
            data=CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request: Request, *args, **kwargs):
        """
        PUT /api/comments/<pk>/
        """
        # 需有 **kwards 以接收调用 update 的 pk

        # get_object 是 DRF 包装的一个函数，是基于queryset的设定
        # 会在找不到的时候 raise 404 error
        # 所以这里无需做额外判断
        comment = self.get_object()
        serializer = CommentSerializerForUpdate(
            # 指定 instance 时，会调用 serializer 的 update 操作
            # 当 instance 不存在时，会调用 serializer 的 create 操作
            instance=comment,
            data=request.data,
        )

        # validate input
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # save 方法会触发 serializer 里的 update 方法，点进 save 的具体实现里可以看到
        # save 是根据 instance 参数有没有传来决定是触发 create 还是 update
        comment = serializer.save()
        return Response(
            data=CommentSerializer(comment).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request: Request, *args, **kwargs):
        """
        DELETE /api/comments/<pk>/
        """
        comment = self.get_object()
        comment.delete()
        # DRF 里默认 destroy 返回的是 status code = 204 no content
        # 这里 return 了 success=True 更直观的让前端去做判断，所以 return 200 更合适
        return Response({
            'success': True,
        }, status=status.HTTP_200_OK)
