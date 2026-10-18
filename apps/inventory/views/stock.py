"""Daily stock entry, stock summary, closing-stock tracker and pending purchases."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.mixins import OutletScopedMixin
from apps.common.permissions import IsPortalUser
from apps.common.request import filter_dates, get_id, get_int
from apps.common.scope import outlets_for

from ..ledger import compute_closing
from ..models import ClosingStockLog, RawMaterial, StockLedger
from ..serializers import StockLedgerSerializer

ZERO = Decimal(0)


class StockLedgerViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    """Daily stock entry per outlet+material. Saving also marks the day's closing stock as updated."""
    queryset = StockLedger.objects.select_related('material').order_by('-date', 'material__name')
    serializer_class = StockLedgerSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['outlet', 'material', 'date']

    def _save(self, serializer):
        row = serializer.save()
        compute_closing(row)
        row.save()
        ClosingStockLog.objects.update_or_create(outlet=row.outlet, date=row.date,
                                                 defaults={'updated_by': self.request.user})

    perform_create = _save
    perform_update = _save


@api_view(['GET'])
@permission_classes([IsPortalUser])
def stock_summary(request):
    p = request.query_params
    qs = StockLedger.objects.filter(outlet__in=outlets_for(request.user))
    if get_id(request, 'outlet'):
        qs = qs.filter(outlet_id=get_id(request, 'outlet'))
    if p.get('category'):
        qs = qs.filter(material__category=p['category'])
    qs = filter_dates(request, qs, 'date')
    use_cons = p.get('unit_type') == 'consumption'
    flows = ['purchase', 'excess', 'consumed', 'wastage', 'normal_loss', 'transfer', 'shortage', 'production']
    rows = []
    for m in RawMaterial.objects.filter(owner=request.user.tenant_owner).order_by('name'):
        mq = qs.filter(material=m).order_by('date')
        if p.get('category') and m.category != p['category']:
            continue
        first, last = mq.first(), mq.last()
        agg = mq.aggregate(**{f: Sum(f) for f in flows})
        f = m.conversion if use_cons else 1
        r = {'material': f'{m.name} [{m.consumption_unit if use_cons else m.purchase_unit}]', 'material_id': m.id}
        r['opening'] = (first.opening if first else ZERO) * f
        for k in flows:
            r[k] = (agg[k] or ZERO) * f
        r['total'] = r['opening'] + r['purchase'] + r['excess']
        r['closing'] = r['total'] - r['consumed'] - r['wastage'] - r['normal_loss'] - r['transfer'] - r['shortage'] + r['production']
        r['stock_closing'] = (last.stock_closing if last else ZERO) * f
        r['difference'] = r['stock_closing'] - r['closing']
        rows.append(r)
    page, size = get_int(request, 'page', 1, lo=1), get_int(request, 'page_size', 100, lo=1, hi=500)
    return Response({'count': len(rows), 'page': page, 'rows': rows[(page - 1) * size: page * size],
                     'categories': sorted(set(RawMaterial.objects.filter(owner=request.user.tenant_owner).exclude(category='').values_list('category', flat=True)))})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def closing_tracker(request):
    days = get_int(request, 'days', 7, lo=1, hi=31)
    today = date.today()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    outlets = list(outlets_for(request.user))
    done = set(ClosingStockLog.objects.filter(outlet__in=outlets, date__gte=dates[0]).values_list('outlet_id', 'date'))
    grid = [{'outlet_id': o.id, 'outlet': o.name, 'code': o.code,
             'days': [(o.id, d) in done for d in dates], 'updated': sum((o.id, d) in done for d in dates)} for o in outlets]
    return Response({'dates': [d.isoformat() for d in dates], 'outlets': grid,
                     'closed_today': sum(g['days'][-1] for g in grid), 'pending_today': sum(not g['days'][-1] for g in grid),
                     'updates_total': sum(g['updated'] for g in grid), 'slots': len(grid) * days})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def pending_purchases(request):
    """Materials where shortage was recorded (consumed/sold more than purchased) and no received PO covers it."""
    qs = StockLedger.objects.filter(outlet__in=outlets_for(request.user), shortage__gt=0).select_related('material', 'outlet')
    if get_id(request, 'outlet'):
        qs = qs.filter(outlet_id=get_id(request, 'outlet'))
    qs = filter_dates(request, qs, 'date')
    return Response([{'outlet': r.outlet.name, 'material': r.material.name, 'date': r.date, 'shortage': r.shortage}
                     for r in qs.order_by('-date')])
