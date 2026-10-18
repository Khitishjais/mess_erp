"""Automation 5: end-of-day report (forecast vs served, cost, wastage, issues)."""
from decimal import Decimal

from django.db.models import Sum

from .. import services as svc
from ..models import Attendance, DailyReport, ForecastSnapshot, MealPlan, WastageLog
from .common import _clean


def build_daily_report(outlet, day):
    meals, issues = [], []
    total_cost = Decimal(0)
    served = 0
    snaps = {s.meal: s.expected for s in ForecastSnapshot.objects.filter(outlet=outlet, date=day)}
    atts = {a.meal: a for a in Attendance.objects.filter(outlet=outlet, date=day)}
    for meal in svc.MEALS:
        if not MealPlan.objects.filter(outlet=outlet, weekday=day.weekday(), meal=meal).exists():
            continue
        a = atts.get(meal)
        row = {'meal': meal, 'forecast': snaps.get(meal), 'actual': a.actual if a else None,
               'cooked': a.prepared_portions if a else None, 'leftover': a.leftover_portions if a else None,
               'cost': 0, 'cost_per_plate': None, 'error_pct': None}
        if a:
            req = svc.meal_requirement(outlet, day, meal, headcount=a.actual)
            row['cost'], row['cost_per_plate'] = req['cost'], req['cost_per_plate']
            served += a.actual
            total_cost += Decimal(str(req['cost']))
            if row['forecast'] and a.actual:
                row['error_pct'] = round((row['forecast'] - a.actual) / a.actual * 100, 1)
                if abs(row['error_pct']) > 20:
                    issues.append(f"{meal.title()}: forecast {row['forecast']} vs {a.actual} actually served ({row['error_pct']:+.0f}%).")
            if a.prepared_portions and a.leftover_portions and a.leftover_portions / a.prepared_portions > 0.15:
                issues.append(f"{meal.title()}: {a.leftover_portions} of {a.prepared_portions} portions left over "
                              f"({a.leftover_portions / a.prepared_portions * 100:.0f}%).")
        else:
            issues.append(f"{meal.title()}: attendance not entered, so cost and learning skip this meal.")
        meals.append(row)
    w = WastageLog.objects.filter(outlet=outlet, date=day)
    w_total = w.aggregate(s=Sum('cost'))['s'] or Decimal(0)
    by_reason = [{'reason': r['reason'], 'cost': r['cost']} for r in w.values('reason').annotate(cost=Sum('cost')).order_by('-cost')]
    if total_cost and w_total / total_cost > Decimal('0.10'):
        issues.append(f"Wastage Rs {w_total:.0f} is {w_total / total_cost * 100:.0f}% of food cost today.")
    per_plate = f" (Rs {total_cost / served:.1f}/plate)" if served else ''
    payload = _clean({
        'date': day, 'meals': meals, 'served': served, 'food_cost': total_cost,
        'cost_per_plate': round(total_cost / served, 2) if served else None,
        'wastage_cost': w_total, 'wastage_by_reason': by_reason, 'issues': issues,
        'summary': f"{served} plates served, food cost Rs {total_cost:.0f}{per_plate}, wastage Rs {w_total:.0f}. "
                   + (f"{len(issues)} thing(s) to look at." if issues else 'No issues.'),
        'accuracy_30d': svc.forecast_accuracy(outlet, 30),
    })
    obj, _ = DailyReport.objects.update_or_create(outlet=outlet, date=day, defaults={'payload': payload})
    return obj
