"""Order and order-item querysets filtered by the request (dates, outlets, status)."""
from apps.common.request import filter_dates, get_id_list
from apps.common.scope import outlets_for
from apps.orders.models import Order, OrderItem


def order_qs(request, force_status=None):
    qs = Order.objects.filter(outlet__in=outlets_for(request.user)).exclude(status='running')
    qs = filter_dates(request, qs, 'created_at__date')
    ids = get_id_list(request, 'outlets')
    if ids:
        qs = qs.filter(outlet_id__in=ids)
    status = force_status or request.query_params.get('status', 'success')
    if status != 'all':
        qs = qs.filter(status=status)
    return qs


def item_qs(request, force_status=None, include_cancelled_lines=False):
    oq = order_qs(request, force_status)
    qs = OrderItem.objects.filter(order__in=oq)
    return qs if include_cancelled_lines else qs.filter(is_cancelled=False)
