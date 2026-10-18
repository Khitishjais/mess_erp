"""The agent's tools. Every tool is READ-ONLY and runs for one outlet set the caller may see; the agent can look things up,
never change anything (no deletes, no orders, no stock edits). Each returns small JSON-able data."""
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Count, Sum

from apps.mess import services as mess
from apps.orders.models import Order, OrderItem

from .retriever import search


@dataclass
class Ctx:
    owner: object
    outlet: object
    outlets: object


def _day(value, default=None):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return default or date.today()


def _days(value, default=7, hi=90):
    try:
        return min(max(int(value), 1), hi)
    except (ValueError, TypeError):
        return default


def forecast(ctx, date=None):
    d = _day(date, date_today() + timedelta(days=1))
    return {'date': d.isoformat(), 'meals': [mess.forecast_headcount(ctx.outlet, d, m, snapshot=False) for m in mess.MEALS]}


def day_plan(ctx, date=None):
    return mess.day_plan(ctx.outlet, _day(date, date_today() + timedelta(days=1)))


def purchase_plan(ctx, days=7):
    return mess.purchase_plan(ctx.outlet, date_today(), _days(days))


def stock_alerts(ctx):
    return {'alerts': mess.stock_alerts(ctx.outlet)}


def wastage(ctx, days=30):
    return mess.wastage_insights(ctx.outlet, _days(days, 30))


def staffing(ctx, date=None):
    return {'rows': mess.staffing(ctx.outlet, _day(date, date_today() + timedelta(days=1)))}


def sales(ctx, days=1):
    n = _days(days, 1, 366)
    a = Order.objects.filter(outlet__in=ctx.outlets, created_at__date__gte=date_today() - timedelta(days=n - 1), status='success') \
        .aggregate(total=Sum('total'), bills=Count('id'))
    return {'days': n, 'bills': a['bills'] or 0, 'total': a['total'] or 0}


def top_items(ctx, days=7):
    rows = OrderItem.objects.filter(order__outlet__in=ctx.outlets, order__created_at__date__gte=date_today() - timedelta(days=_days(days)),
                                    is_cancelled=False).values('name').annotate(qty=Sum('qty')).order_by('-qty')[:8]
    return {'items': list(rows)}


def stock_levels(ctx, material=''):
    from apps.inventory.models import RawMaterial
    have = mess.current_stock(ctx.outlet)
    qs = RawMaterial.objects.filter(owner=ctx.owner)
    if material:
        qs = qs.filter(name__icontains=str(material)[:60])
    return {'stock': [{'material': m.name, 'unit': m.purchase_unit, 'in_stock': float(have.get(m.id, 0))} for m in qs[:40]]}


def knowledge(ctx, query=''):
    return {'results': [h.public() for h in search(ctx.owner, ctx.outlets, str(query)[:300])]}


def date_today():
    return date.today()


_D = {'type': 'string', 'description': 'YYYY-MM-DD, default tomorrow'}
TOOLS = {
    'forecast': (forecast, 'Expected number of people for breakfast/lunch/dinner on a date.', {'date': _D}),
    'day_plan': (day_plan, 'What to cook and how much raw material is needed on a date (with cost).', {'date': _D}),
    'purchase_plan': (purchase_plan, 'What to buy over the next N days, net of stock.', {'days': {'type': 'integer'}}),
    'stock_alerts': (stock_alerts, 'Low stock, expiry and dead-stock warnings.', {}),
    'wastage': (wastage, 'Food wastage cost, causes and tips for the last N days.', {'days': {'type': 'integer'}}),
    'staffing': (staffing, 'How many cooks and servers are needed on a date.', {'date': _D}),
    'sales': (sales, 'Bills count and sales total for the last N days (restaurant billing).', {'days': {'type': 'integer'}}),
    'top_items': (top_items, 'Best selling items of the last N days.', {'days': {'type': 'integer'}}),
    'stock_levels': (stock_levels, 'Current counted stock of one material or all.', {'material': {'type': 'string'}}),
    'knowledge': (knowledge, 'Search the guides and this business\'s menu, recipes, materials and feedback.', {'query': {'type': 'string'}}),
}


def schemas():
    return [{'name': n, 'description': d, 'input_schema': {'type': 'object', 'properties': p}} for n, (_, d, p) in TOOLS.items()]


def call(name, ctx, args):
    """Run a tool by name with model-supplied arguments. Unknown tools / bad args never raise; they return an error dict."""
    if name not in TOOLS:
        return {'error': f'unknown tool {name}'}
    fn, _, props = TOOLS[name]
    clean = {k: v for k, v in (args or {}).items() if k in props}
    try:
        return fn(ctx, **clean)
    except Exception as e:          # a tool failing must not crash the conversation
        return {'error': f'{name} failed: {type(e).__name__}'}
