"""Menu engineering: rate each dish by popularity, cost per plate and waste."""
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum

from ..models import MealPlan, Recipe, WastageLog
from .config import setting_for


def menu_engineering(outlet):
    """Classify each dish by cost per plate and waste rate. Popularity comes from take-rate (estimate) until data exists."""
    rows = []
    s = setting_for(outlet)
    since = Date.today() - timedelta(days=28)
    for r in Recipe.objects.filter(owner=outlet.owner).prefetch_related('lines__material'):
        served_times = MealPlan.objects.filter(outlet=outlet, recipe=r).count() * 4
        if not served_times:
            continue
        cost = sum(ln.qty / (ln.material.yield_pct / 100) / ln.material.conversion * ln.material.unit_cost for ln in r.lines.all())
        wasted = WastageLog.objects.filter(outlet=outlet, recipe=r, date__gte=since).aggregate(s=Sum('qty'))['s'] or 0
        portions = Decimal(s.members) * Decimal('0.8') * r.take_rate * served_times
        waste_pct = float(Decimal(wasted) / portions * 100) if portions else 0
        liked = float(r.popularity)      # take_rate is how many people CAN eat it (e.g. veg only), not how good it is
        cls = ('Review' if waste_pct >= 10 else 'Star' if liked >= 1.0 and waste_pct < 5 else 'Steady' if liked >= 0.95 else 'Puzzle')
        rows.append({'dish': r.name, 'cost_per_plate': round(cost, 2), 'take_rate': float(r.take_rate), 'popularity': float(r.popularity),
                     'waste_pct': round(waste_pct, 1), 'class': cls, 'is_estimate': r.is_estimate,
                     'advice': {'Star': 'Popular and little waste — keep as is.', 'Steady': 'Fine; keep monitoring.', 'Review': 'High waste — reduce portion or replace.',
                                'Puzzle': 'Low pull — try a better recipe or move it to a different day.'}[cls]})
    rows.sort(key=lambda x: (-x['waste_pct'], -x['cost_per_plate']))
    return rows
