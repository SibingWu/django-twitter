from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from accounts.api.serializers import (
    UserSerializer,
    LoginSerializer,
    SignupSerializer,
    UserSerializerWithProfile, UserProfileSerializerForUpdate,
)
from django.contrib.auth import (
    authenticate as django_authenticate,
    login as django_login,
    logout as django_logout,
)

from accounts.models import UserProfile
from utils.permissions import IsObjectOwner


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializerWithProfile
    permission_classes = (permissions.IsAdminUser,)

class AccountViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    serializer_class = SignupSerializer

    @action(methods=['GET'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='GET', block=True))
    def login_status(self, request):
        """
        查看用户当前的登录状态和具体信息
        """
        data = {
            'has_logged_in': request.user.is_authenticated,
            'ip': request.META['REMOTE_ADDR'],
        }
        if request.user.is_authenticated:
            data['user'] = UserSerializer(request.user).data
        return Response(data)

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def login(self, request):
        """
        使用 username, password 进行注册
        默认的 username 是 admin, password 也是 admin
        """
        # get username and password from request
        serializer = LoginSerializer(data=request.data)

        # validate input
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # validation ok, login
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # check if user exists
        if not User.objects.filter(username=username).exists():
            return Response({
                'success': False,
                'message': 'User does not exists.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # check if given credentials are valid
        user = django_authenticate(username=username, password=password)
        if not user or user.is_anonymous:
            return Response({
                'success': False,
                'message': 'Username and password does not match.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # log in
        django_login(request, user)
        return Response({
            'success': True,
            'user': UserSerializer(instance=user).data,
        })


    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def logout(self, request):
        """
        登出当前用户
        """
        django_logout(request)
        return Response({'success': True})

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def signup(self, request):
        """
        使用 username, email, password 进行注册

        测试数据：
        username: lisawu
        email: lisa@twitter.com
        password: lisawu

        创建测试数据时，密码与用户名一致
        """
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        # create UserProfile object
        user.profile

        django_login(request, user)
        return Response({
            'success': True,
            'user': UserSerializer(instance=user).data,
        }, status=status.HTTP_201_CREATED)


class UserProfileViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.UpdateModelMixin,
):
    # 继承的 viewsets.mixins.UpdateModelMixin 中有个 update 方法
    # PUT /api/profiles/<profile_id>/
    queryset = UserProfile
    permission_classes = (IsAuthenticated, IsObjectOwner,)
    serializer_class = UserProfileSerializerForUpdate
