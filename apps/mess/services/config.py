"""Constants and small lookups shared by every mess planning module (meals, estimates, settings, menu per slot)."""
from decimal import ROUND_HALF_UP, Decimal

from ..models import MealPlan, MessSetting

MEALS = ['breakfast', 'lunch', 'dinner']


DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


# Estimated share of members who eat each meal (percent). Assumption until attendance is logged:
# breakfast is skipped most, weekend dinners drop because people eat out.
DEFAULT_ATTENDANCE = {
    'mon': {'breakfast': 70, 'lunch': 85, 'dinner': 90}, 'tue': {'breakfast': 70, 'lunch': 85, 'dinner': 90},
    'wed': {'breakfast': 70, 'lunch': 85, 'dinner': 90}, 'thu': {'breakfast': 70, 'lunch': 85, 'dinner': 90},
    'fri': {'breakfast': 68, 'lunch': 83, 'dinner': 85}, 'sat': {'breakfast': 60, 'lunch': 80, 'dinner': 75},
    'sun': {'breakfast': 55, 'lunch': 85, 'dinner': 70},
}


HISTORY_WEEKS = 8        # how many past same-weekday meals the forecast looks at


ALPHA = 0.4              # smoothing: weight on the most recent observation


PRIOR_STRENGTH = 3       # after ~3 real observations, data outweighs the estimate


def setting_for(outlet):
    s, _ = MessSetting.objects.get_or_create(outlet=outlet)
    return s


def attendance_pct(setting, day, meal):
    key = DAY_KEYS[day.weekday()]
    return Decimal(str(((setting.attendance or {}).get(key) or {}).get(meal, DEFAULT_ATTENDANCE[key][meal])))


def dishes_for(outlet, day, meal):
    out = []
    for p in MealPlan.objects.filter(outlet=outlet, weekday=day.weekday(), meal=meal).select_related('recipe').prefetch_related('recipe__lines__material'):
        # share of diners taking this dish in this slot (slot override wins over the dish default)
        p.recipe._take = p.take_rate if p.take_rate is not None else p.recipe.take_rate
        out.append(p.recipe)
    return out


def round_half_up(x):
    """76.5 -> 77 (Python's round() gives 76: banker's rounding, which surprises people counting plates)."""
    return int(Decimal(str(x)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
