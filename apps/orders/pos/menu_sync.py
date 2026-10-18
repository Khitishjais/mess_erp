"""Menu/tables/taxes download (bootstrap) and delta pull (changes)."""
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.catalog.models import DiningTable, Item, ItemOutletStatus, Tax
from apps.prefs import service as prefs

from ..models import Order
from .auth import HasDevice


def _menu_payload(dev, since=None):
    owner = dev.outlet.owner
    items = Item.objects.filter(owner=owner).select_related('category', 'tax')
    if since:
        items = items.filter(updated_at__gt=since)
    off = set(ItemOutletStatus.objects.filter(outlet=dev.outlet, is_available=False).values_list('item_id', flat=True))
    return [{'id': i.id, 'name': i.name, 'category': i.category_id, 'category_name': i.category.name,
             'price': str(i.price), 'tax_rate': str(i.tax.rate if i.tax else 0), 'tax_name': i.tax.name if i.tax else '',
             'is_veg': i.is_veg, 'active': i.is_active and i.id not in off, 'updated_at': i.updated_at.isoformat()}
            for i in items]


def _last_seq(dev):
    """Highest numeric suffix used with this terminal's prefix, so a re-installed POS never reuses a number."""
    best = 0
    for inv in Order.objects.filter(outlet=dev.outlet, invoice_no__startswith=dev.invoice_prefix + '-').values_list('invoice_no', flat=True):
        tail = inv.rsplit('-', 1)[-1]
        if tail.isdigit():
            best = max(best, int(tail))
    return best


@api_view(['GET'])
@permission_classes([HasDevice])
def bootstrap(request):
    dev = request.device
    cats = dev.outlet.owner.categories.all()
    return Response({
        'server_time': timezone.now().isoformat(),
        'outlet': {'id': dev.outlet_id, 'name': dev.outlet.name, 'gstin': dev.outlet.gstin, 'address': dev.outlet.address, 'settings': prefs.pos_payload(dev.outlet)},
        'invoice_prefix': dev.invoice_prefix,
        'last_invoice_seq': _last_seq(dev),
        'categories': [{'id': c.id, 'name': c.name, 'sort_order': c.sort_order} for c in cats],
        'items': _menu_payload(dev),
        'tables': [{'id': t.id, 'name': t.name, 'section': t.section, 'seats': t.seats} for t in DiningTable.objects.filter(outlet=dev.outlet)],
        'taxes': [{'id': t.id, 'name': t.name, 'rate': str(t.rate)} for t in Tax.objects.filter(owner=dev.outlet.owner)],
    })


@api_view(['GET'])
@permission_classes([HasDevice])
def changes(request):
    """Delta pull: menu/prices changed since cursor. Server wins for menu data."""
    since = parse_datetime(request.query_params.get('since', '') or '')
    dev = request.device
    outlet = {'id': dev.outlet_id, 'name': dev.outlet.name, 'gstin': dev.outlet.gstin, 'address': dev.outlet.address, 'settings': prefs.pos_payload(dev.outlet)}
    return Response({'server_time': timezone.now().isoformat(), 'items': _menu_payload(dev, since), 'outlet': outlet})
