from notifications.models import Notification
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from inbox.api.serializers import NotificationSerializer


class NotificationViewSet(viewsets.GenericViewSet,
                          viewsets.mixins.ListModelMixin):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    # viewsets.mixins.ListModelMixin 中会self.filter_queryset()
    # list 时会以此筛选
    # GET /api/notifications/?unread=True
    # GET /api/notifications/?unread=False
    filterset_fields = ('unread',)

    def get_queryset(self):
        # return self.request.user.notification.all()
        return Notification.objects.filter(recipient=self.request.user).all()

    @action(methods=['GET'], detail=False, url_path='unread-count')
    def unread_count(self, request: Request):
        """
        GET /api/notifications/unread-count/
        """
        count = self.get_queryset().filter(unread=True).count()
        return Response({
            'unread_count': count
        }, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='mark-all-as-read')
    def mark_all_as_read(self, request: Request):
        """
        POST /api/notifications/mark-all-as-read/
        """
        updated_count = self.get_queryset().filter(unread=True).update(unread=False)  # mark as read
        return Response({
            'marked_count': updated_count
        }, status=status.HTTP_200_OK)
