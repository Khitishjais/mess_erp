"""Sales reports grouped by outlet/day/biller/...: sums plus payment split."""
from collections import defaultdict

from django.db.models import Count, Max, Min, Sum

from apps.orders.models import Payment

from .columns import DATE, INT, MODES, MONEY, ZERO, col
from .filters import order_qs

SALES_COLS = [
    col('bills', 'Total no. of bills', INT), col('my_amount', 'My Amount', MONEY), col('discount', 'Total Discount', MONEY),
    col('net', 'Net Sales (M.A - T.D)', MONEY), col('delivery_charge', 'Delivery Charge', MONEY),
    col('container_charge', 'Container Charge', MONEY), col('service_charge', 'Service Charge', MONEY),
    col('additional_charge', 'Additional Charge', MONEY), col('total_tax', 'Total Tax', MONEY),
    col('round_off', 'Round Off', MONEY), col('waived_off', 'Waived off', MONEY), col('total', 'Total Sales', MONEY),
    col('tip', 'Tip', MONEY),
] + [col(m, m.capitalize() if m != 'upi' else 'UPI', MONEY) for m in MODES] + [col('pax', 'Pax', INT)]


SUMS = ['my_amount', 'discount', 'delivery_charge', 'container_charge', 'service_charge', 'additional_charge',
        'total_tax', 'round_off', 'waived_off', 'total', 'tip', 'pax']


def grouped_sales(qs, groups):
    """groups: {'key': 'orm__path'} -> one row per group with sales + payment split."""
    paths = list(groups.values())
    rows = qs.values(*paths).annotate(
        bills=Count('id'), first_inv=Min('invoice_no'), last_inv=Max('invoice_no'), last_sync=Max('synced_at'),
        **{k: Sum(k) for k in SUMS})
    pay = defaultdict(lambda: defaultdict(lambda: ZERO))
    for r in Payment.objects.filter(order__in=qs).values(*[f'order__{p}' for p in paths], 'mode').annotate(s=Sum('amount')):
        pay[tuple(r[f'order__{p}'] for p in paths)][r['mode']] += r['s']
    out = []
    for r in rows:
        key = tuple(r[p] for p in paths)
        d = {k: r[p] for k, p in groups.items()}
        d.update({s: r[s] or ZERO for s in SUMS}); d['bills'] = r['bills']
        d['net'] = d['my_amount'] - d['discount']
        d['invoice_nos'] = f"{r['first_inv']}-{r['last_inv']}" if r['bills'] > 1 else r['first_inv']
        d['last_sync'] = r['last_sync']
        for m in MODES:
            d[m] = pay[key][m]
        out.append(d)
    return out


def sales_report(groups, extra_cols=(), outlet_cols=True, filt=None, force_status=None):
    def build(request):
        qs = order_qs(request, force_status)
        if filt:
            qs = qs.filter(**filt) if isinstance(filt, dict) else filt(qs)
        rows = grouped_sales(qs, groups)
        rows.sort(key=lambda r: tuple(str(r[k] or '') for k in groups))
        cols = [col(k, label) for k, label in zip(groups, LABELS_FOR(groups))] + [col('invoice_nos', 'Invoice Nos.')] + SALES_COLS + [col('last_sync', 'Data Synced', DATE)]
        return cols, rows
    return build


def LABELS_FOR(groups):
    return [k.replace('_', ' ').title() for k in groups]


def outlet_performance(request):
    cols, rows = sales_report({'restaurant': 'outlet__name'})(request)
    avg = (sum(r['total'] for r in rows) / len(rows)) if rows else ZERO
    for r in rows:
        r['vs_avg'] = r['total'] - avg
        r['position'] = 'Above average' if r['total'] >= avg else 'Below average'
    rows.sort(key=lambda r: r['total'], reverse=True)
    keep = ['restaurant', 'bills', 'net', 'total_tax', 'total']
    return [c for c in cols if c['key'] in keep] + [col('vs_avg', 'Vs group average', MONEY), col('position', 'Position')], rows
