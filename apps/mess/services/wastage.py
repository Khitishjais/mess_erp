"""Wastage analytics and tips from the wastage log."""
from datetime import date as Date
from datetime import timedelta

from django.db.models import Sum

from ..models import WastageLog
from .forecast import forecast_accuracy


def wastage_insights(outlet, days=30):
    since = Date.today() - timedelta(days=days)
    qs = WastageLog.objects.filter(outlet=outlet, date__gte=since)
    by_reason = list(qs.values('reason').annotate(cost=Sum('cost'), qty=Sum('qty')).order_by('-cost'))
    by_dish = list(qs.exclude(recipe=None).values('recipe__name').annotate(portions=Sum('qty'), cost=Sum('cost')).order_by('-cost'))
    by_meal = list(qs.values('meal').annotate(cost=Sum('cost')).order_by('-cost'))
    total = qs.aggregate(s=Sum('cost'))['s'] or 0
    tips = []
    for d in by_dish[:5]:
        tips.append(f"'{d['recipe__name']}': {d['portions']} portions wasted in {days} days — cook ~{min(25, round(float(d['portions']) / 4))}% less or swap it.")
    for r in by_reason:
        if r['reason'] == 'spoiled' and r['cost']:
            tips.append('Spoilage found: buy perishables daily (purchase plan already limits them to their shelf life).')
    acc = forecast_accuracy(outlet, days)
    return {'days': days, 'total_cost': total, 'by_reason': by_reason, 'by_dish': by_dish, 'by_meal': by_meal, 'tips': tips, 'accuracy': acc}
