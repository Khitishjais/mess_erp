from datetime import date

from django.db.models import Count, Q, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.permissions import IsPortalUser
from apps.common.request import get_date, get_id_list, get_int
from apps.common.scope import outlets_for
from apps.orders.models import Order, Payment


def _orders(request):
    qs = Order.objects.filter(outlet__in=outlets_for(request.user), status__in=['success', 'complimentary'])
    day = get_date(request, 'date') or date.today()
    qs = qs.filter(created_at__date__gte=get_date(request, 'from') or day, created_at__date__lte=get_date(request, 'to') or day)
    ids = get_id_list(request, 'outlets')
    return qs.filter(outlet_id__in=ids) if ids else qs


def _pct(part, whole):
    return round(float(part) / float(whole) * 100, 2) if whole else 0


@api_view(['GET'])
@permission_classes([IsPortalUser])
def kpis(request):
    qs = _orders(request)
    a = qs.aggregate(gross=Sum('total'), net=Sum('my_amount'),
                     disc=Sum('discount'), online=Sum('total', filter=Q(is_online=True)),
                     offline=Sum('total', filter=Q(is_online=False)), bills=Count('id'), outlets=Count('outlet', distinct=True))
    gross = a['gross'] or 0
    net = (a['net'] or 0) - (a['disc'] or 0)
    cash = Payment.objects.filter(order__in=qs, mode='cash').aggregate(s=Sum('amount'))['s'] or 0
    return Response({
        'gross_sales': gross, 'net_sales': net, 'online_sales': a['online'] or 0, 'offline_sales': a['offline'] or 0,
        'online_pct': _pct(a['online'] or 0, gross), 'offline_pct': _pct(a['offline'] or 0, gross),
        'cash_collected': cash, 'cash_pct': _pct(cash, gross), 'bills': a['bills'],
        'outlet_count': outlets_for(request.user).count(),
    })


@api_view(['GET'])
@permission_classes([IsPortalUser])
def outlet_stats(request):
    metric = request.query_params.get('metric', 'gross')
    order = request.query_params.get('order', 'top')
    limit = get_int(request, 'limit', 10, lo=1, hi=100)
    rows = _orders(request).values('outlet_id', 'outlet__name').annotate(
        gross=Sum('total'), net=Sum('my_amount') - Sum('discount'), offline=Sum('total', filter=Q(is_online=False)),
        orders=Count('id'))
    key = {'gross': 'gross', 'net': 'net', 'offline': 'offline', 'orders': 'orders'}.get(metric, 'gross')
    rows = sorted(rows, key=lambda r: r[key] or 0, reverse=(order == 'top'))[:limit]
    return Response([{'outlet_id': r['outlet_id'], 'outlet': r['outlet__name'], 'value': r[key] or 0, **{
        k: r[k] or 0 for k in ('gross', 'net', 'offline', 'orders')}} for r in rows])


@api_view(['GET'])
@permission_classes([IsPortalUser])
def taxes(request):
    qs = _orders(request)
    mode = request.query_params.get('mode', 'all')
    if mode == 'online':
        qs = qs.filter(is_online=True)
    elif mode == 'offline':
        qs = qs.filter(is_online=False)
    n = get_int(request, 'n', 5, lo=1, hi=100)
    order = '-v' if request.query_params.get('order', 'top') == 'top' else 'v'
    rows = list(qs.values('outlet__name').annotate(v=Sum('total_tax')).order_by(order)[:n])
    total = sum((r['v'] or 0) for r in rows)
    return Response({'total': total, 'rows': [{'outlet': r['outlet__name'], 'value': r['v'] or 0, 'pct': _pct(r['v'] or 0, total)} for r in rows]})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def discounts(request):
    qs = _orders(request).filter(discount__gt=0)
    mode = request.query_params.get('mode', 'all')
    if mode == 'online':
        qs = qs.filter(is_online=True)
    elif mode == 'offline':
        qs = qs.filter(is_online=False)
    n = get_int(request, 'n', 5, lo=1, hi=100)
    order = '-v' if request.query_params.get('order', 'top') == 'top' else 'v'
    rows = list(qs.values('outlet__name').annotate(v=Sum('discount')).order_by(order)[:n])
    total = sum((r['v'] or 0) for r in rows)
    return Response({'total': total, 'rows': [{'outlet': r['outlet__name'], 'value': r['v'] or 0, 'pct': _pct(r['v'] or 0, total)} for r in rows]})