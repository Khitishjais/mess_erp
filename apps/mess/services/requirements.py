"""Raw material needed per meal/day from the forecast (or a real headcount), recipes and edible yield."""
import math
from collections import defaultdict
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.inventory.models import RawMaterial

from ..models import MealPlan, WastageLog
from .config import MEALS, dishes_for, setting_for
from .forecast import forecast_headcount


def _leftover_factor(outlet, recipe):
    """Learn over-cooking: if a dish keeps coming back, trim its portions (max 25%)."""
    wasted = WastageLog.objects.filter(outlet=outlet, recipe=recipe, reason='leftover', date__gte=Date.today() - timedelta(days=28)) \
        .aggregate(s=Sum('qty'))['s'] or 0
    served = MealPlan.objects.filter(outlet=outlet, recipe=recipe).count() * 4   # times served in 4 weeks (approx.)
    if not wasted or not served:
        return Decimal(1)
    s = setting_for(outlet)
    avg_portions = Decimal(s.members) * Decimal('0.8') * getattr(recipe, '_take', recipe.take_rate) * served
    rate = Decimal(wasted) / avg_portions if avg_portions else 0
    return max(Decimal('0.75'), 1 - rate)


def meal_requirement(outlet, day, meal, headcount=None):
    """Raw material for a meal. headcount=None -> use the forecast; headcount=N -> use that real number (consumption)."""
    s = setting_for(outlet)
    if headcount is None:
        fc = forecast_headcount(outlet, day, meal)
    else:
        fc = {'date': day.isoformat(), 'meal': meal, 'expected': headcount, 'low': headcount, 'high': headcount,
              'method': 'actual', 'history_points': 0, 'data_weight': 1, 'factors': {},
              'dishes': [d.name for d in dishes_for(outlet, day, meal)]}
    buffer = 1 + s.buffer_pct / 100
    dishes, materials = [], defaultdict(lambda: {'qty': Decimal(0)})
    for r in dishes_for(outlet, day, meal):
        trim = _leftover_factor(outlet, r)
        portions = math.ceil(Decimal(fc['expected']) * buffer * r._take * trim)
        lines = []
        for ln in r.lines.all():
            m = ln.material
            raw = Decimal(portions) * ln.qty / (m.yield_pct / 100)          # buy more than you serve to cover trimming
            lines.append({'material': m.name, 'qty': round(raw, 1), 'unit': m.consumption_unit})
            agg = materials[m.id]
            agg.update(material=m.name, material_id=m.id, unit=m.consumption_unit)
            agg['qty'] += raw
        dishes.append({'dish': r.name, 'portions': portions, 'leftover_trim': float(trim), 'is_estimate': r.is_estimate, 'lines': lines})
    mats = []
    for v in materials.values():
        m = RawMaterial.objects.get(pk=v['material_id'])
        cost = v['qty'] / m.conversion * m.unit_cost
        mats.append({**v, 'qty': round(v['qty'], 1), 'purchase_qty': round(v['qty'] / m.conversion, 3),
                     'purchase_unit': m.purchase_unit, 'cost': round(cost, 2)})
    mats.sort(key=lambda x: x['material'])
    total_cost = sum(x['cost'] for x in mats)
    return {'forecast': fc, 'dishes': dishes, 'materials': mats, 'cost': round(total_cost, 2),
            'cost_per_plate': round(total_cost / fc['expected'], 2) if fc['expected'] else 0}


def day_plan(outlet, day):
    meals = {m: meal_requirement(outlet, day, m) for m in MEALS}
    return {'date': day.isoformat(), 'weekday': day.strftime('%A'), 'meals': meals,
            'cost': round(sum(x['cost'] for x in meals.values()), 2)}


def material_cost(material, qty_consumption):
    return (Decimal(qty_consumption) / material.conversion * material.unit_cost).quantize(Decimal('0.01'))


def recipe_plate_cost(recipe):
    """Exact (unrounded) cost of one portion of a dish: every ingredient / edible yield / conversion x unit cost."""
    return sum((line.qty / (line.material.yield_pct / 100) / line.material.conversion * line.material.unit_cost
                for line in recipe.lines.select_related('material')), Decimal(0))
