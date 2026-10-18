from django.db.models import Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.mixins import OutletScopedMixin
from apps.common.permissions import IsPortalUser
from apps.common.request import filter_dates, get_id
from apps.common.scope import outlets_for

from .models import Kot, Order
from .serializers import KotSerializer, OrderSerializer


class OrderViewSet(OutletScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.select_related('outlet', 'biller').prefetch_related('items', 'payments', 'taxes')
    serializer_class = OrderSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['outlet', 'status', 'order_type', 'is_online']

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_dates(self.request, qs, 'created_at__date').order_by('-created_at')


@api_view(['GET'])
@permission_classes([IsPortalUser])
def live_orders(request):
    """Live Orders: running totals by type and pending stages, optionally per outlet."""
    qs = Order.objects.filter(outlet__in=outlets_for(request.user), status='running')
    if get_id(request, 'outlet'):
        qs = qs.filter(outlet_id=get_id(request, 'outlet'))

    def agg(q):
        r = q.aggregate(orders=Count('id'), amount=Sum('total'))
        return {'orders': r['orders'] or 0, 'amount': str(r['amount'] or 0)}

    view = request.query_params.get('view', 'orders')
    data = {
        'total': agg(qs),
        'by_type': {t: agg(qs.filter(order_type=t)) for t in ('dine_in', 'pickup', 'delivery')},
        'pending': {
            'total': agg(qs.exclude(stage='done')),
            'preparing': agg(qs.filter(stage='preparing')),
            'waiting_pickup': agg(qs.filter(stage='waiting_pickup')),
            'out_for_delivery': agg(qs.filter(stage='out_for_delivery')),
        },
    }
    if view == 'tables':
        data['tables'] = [{'table': o.table.name if o.table else None, 'order_id': o.id, 'invoice_no': o.invoice_no,
                           'amount': str(o.total), 'since': o.created_at} for o in qs.exclude(table=None).select_related('table')]
    return Response(data)


class KotViewSet(OutletScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Kitchen display feed (portal side)."""
    queryset = Kot.objects.select_related('order').order_by('-created_at')
    outlet_field = 'order__outlet'
    serializer_class = KotSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['status', 'order__outlet']