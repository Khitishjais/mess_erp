"""Purchase orders: create, approve, reject, receive."""
from datetime import date

from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.common.mixins import OutletScopedMixin
from apps.common.permissions import IsPortalUser
from apps.common.request import filter_dates
from apps.common.scope import can_manage

from ..ledger import add_to_ledger
from ..models import PurchaseOrder
from ..serializers import PurchaseOrderSerializer


class PurchaseOrderViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('outlet').prefetch_related('lines__material')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['outlet', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_dates(self.request, qs, 'created_at__date').order_by('-created_at')

    @staticmethod
    def _require(po, status, verb):
        if po.status != status:
            raise ValidationError(f'Only a {status} purchase order can be {verb} (this one is {po.status}).')

    def _decide(self, request, status, verb):
        if not can_manage(request.user):
            raise PermissionDenied('Only owner/manager can approve or reject.')
        po = self.get_object()
        self._require(po, 'pending', verb)
        po.status, po.approved_by = status, request.user
        po.save()
        return Response(self.get_serializer(po).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, 'approved', 'approved')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, 'rejected', 'rejected')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def receive(self, request, pk=None):
        """Goods arrived: the quantities are added to today's stock as purchases (only once, only for an approved PO)."""
        po = self.get_object()
        self._require(po, 'approved', 'received')
        for line in po.lines.select_related('material'):
            add_to_ledger(po.outlet, line.material, date.today(), 'purchase', line.qty)
        po.status = 'received'
        po.save()
        return Response(self.get_serializer(po).data)
