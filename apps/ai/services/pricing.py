"""Offer / dynamic-pricing hints from slow hours."""
from datetime import date as Date
from datetime import timedelta
from statistics import median

from django.db.models import Count
from django.db.models.functions import ExtractHour

from apps.orders.models import Order


def pricing_hints(outlets, days=14):
    since = Date.today() - timedelta(days=days)
    out = []
    for o in outlets:
        rows = (Order.objects.filter(outlet=o, created_at__date__gte=since, status='success')
                .annotate(h=ExtractHour('created_at')).values('h').annotate(n=Count('id')))
        counts = {r['h']: r['n'] for r in rows}
        if len(counts) < 3:
            continue
        med = median(counts.values())
        for h, n in sorted(counts.items()):
            if n < med * 0.5:
                pct = 20 if n < med * 0.25 else 10
                out.append({'outlet': o.name, 'hour': f'{h:02d}:00-{h:02d}:59', 'orders': n, 'typical': med,
                            'suggestion': f'Slow hour: only {n} bills vs typical {med:.0f}. Try a {pct}% happy-hour offer on beverages/snacks.'})
    return out
