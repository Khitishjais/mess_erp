"""Anomaly detection: unusual discounts, cancels, wastage spikes and over-cooking."""
from collections import defaultdict
from datetime import date as Date
from datetime import timedelta
from statistics import mean, pstdev

from apps.orders.models import Order
from apps.prefs import service as prefs


def anomalies(outlets, days=14):
    since = Date.today() - timedelta(days=days)
    out = []
    orders = Order.objects.filter(outlet__in=outlets, created_at__date__gte=since).exclude(status='running')
    by_biller = defaultdict(lambda: {'bills': 0, 'amount': 0.0, 'disc': 0.0, 'cancel': 0})
    for o in orders.select_related('biller'):
        b = by_biller[o.biller.name if o.biller else 'Unknown']
        b['bills'] += 1
        if o.status == 'cancelled':
            b['cancel'] += 1
        else:
            b['amount'] += float(o.my_amount); b['disc'] += float(o.discount)
    rates = {k: (v['disc'] / v['amount'] * 100 if v['amount'] else 0) for k, v in by_biller.items()}
    if len(rates) >= 3:
        mu, sd = mean(rates.values()), pstdev(rates.values())
        for k, r in rates.items():
            if sd and (r - mu) / sd > 1.5 and r > 5:
                out.append({'type': 'high_discount', 'severity': 'high', 'subject': k, 'message': f'{k} gave {r:.1f}% discount vs team average {mu:.1f}%'})
    for k, v in by_biller.items():
        if v['bills'] >= 10 and v['cancel'] / v['bills'] > 0.1:
            out.append({'type': 'many_cancels', 'severity': 'medium', 'subject': k, 'message': f'{k} cancelled {v["cancel"]} of {v["bills"]} bills'})
    for o in orders.filter(status='success').select_related('biller'):
        if o.my_amount and o.discount / o.my_amount > 0.25:
            out.append({'type': 'big_discount_bill', 'severity': 'medium', 'subject': o.invoice_no,
                        'message': f'Bill {o.invoice_no}: {float(o.discount / o.my_amount * 100):.0f}% discount ({o.discount_reason or "no reason"})'})
    from apps.mess.models import Attendance, WastageLog
    daily = defaultdict(float)
    for w in WastageLog.objects.filter(outlet__in=outlets, date__gte=since):
        daily[w.date] += float(w.cost)
    if len(daily) >= 5:
        mu, sd = mean(daily.values()), pstdev(daily.values())
        for d, c in daily.items():
            if sd and (c - mu) / sd > 2:
                out.append({'type': 'wastage_spike', 'severity': 'high', 'subject': str(d), 'message': f'Wastage Rs {c:.0f} on {d} vs usual Rs {mu:.0f}'})
    limits = {}                                   # over-cooking threshold from Settings, once per business
    for a in Attendance.objects.filter(outlet__in=outlets, date__gte=since, prepared_portions__isnull=False).select_related('outlet'):
        limit = limits.setdefault(a.outlet.owner_id, prefs.get(a.outlet.owner, 'overcook_pct') / 100)
        if a.actual and a.prepared_portions > a.actual * limit:
            out.append({'type': 'overcooked', 'severity': 'low', 'subject': f'{a.date} {a.meal}',
                        'message': f'{a.date} {a.meal}: cooked {a.prepared_portions} for {a.actual} people (+{a.prepared_portions - a.actual})'})
    return out[:60]
