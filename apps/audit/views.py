from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.mixins import OwnerScopedMixin
from apps.common.permissions import IsPortalUser
from apps.common.request import filter_dates

from .models import AuditLog, Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'is_read', 'created_at']


class AuditLogSerializer(serializers.ModelSerializer):
    outlet_name = serializers.CharField(source='outlet.name', read_only=True, default='')
    actor_name = serializers.CharField(source='actor.name', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = ['id', 'kind', 'message', 'outlet', 'outlet_name', 'actor_name', 'created_at']


class NotificationViewSet(OwnerScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [IsPortalUser]

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'ok': True})


class AuditLogViewSet(OwnerScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('outlet', 'actor').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['kind', 'outlet']

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_dates(self.request, qs, 'created_at__date')