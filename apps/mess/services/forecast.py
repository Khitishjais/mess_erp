"""Headcount forecast: estimate blended with smoothed real attendance, plus forecast accuracy (WAPE)."""
import math
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from ..models import Attendance, ForecastSnapshot, SpecialDay
from .config import (
    ALPHA,
    HISTORY_WEEKS,
    PRIOR_STRENGTH,
    attendance_pct,
    dishes_for,
    round_half_up,
    setting_for,
)


def forecast_headcount(outlet, day, meal, snapshot=True):
    """Prior (members x attendance% x menu pull x special day) blended with smoothed actuals of past same weekdays."""
    s = setting_for(outlet)
    dishes = dishes_for(outlet, day, meal)
    pull = (sum(d.popularity for d in dishes) / len(dishes)) if dishes else Decimal(1)
    pull = max(Decimal('0.85'), min(Decimal('1.15'), pull))
    special = SpecialDay.objects.filter(outlet=outlet, date=day).first()
    sp = special.factor if special else Decimal(1)
    prior = float(s.members * attendance_pct(s, day, meal) / 100 * pull * sp)

    hist = list(Attendance.objects.filter(outlet=outlet, meal=meal, date__lt=day, date__week_day=(day.isoweekday() % 7) + 1)
                .order_by('-date')[:HISTORY_WEEKS].values_list('actual', flat=True))
    n = len(hist)
    if n:
        ewma = None
        for v in reversed(hist):          # oldest -> newest
            ewma = v if ewma is None else ALPHA * v + (1 - ALPHA) * ewma
        w = n / (n + PRIOR_STRENGTH)
        # history already reflects normal menu/weekday; apply only today's special-day factor on top of it
        expected = w * ewma * float(sp) + (1 - w) * prior
        mean = sum(hist) / n
        spread = (sum((v - mean) ** 2 for v in hist) / n) ** 0.5 / mean if n > 1 and mean else 0.15
        band = max(0.05, min(0.25, spread if n > 2 else 0.15))
        method = 'learned' if n >= PRIOR_STRENGTH else 'blended'
    else:
        expected, band, method, w = prior, 0.15, 'estimate', 0

    expected = max(0, round_half_up(expected))
    if snapshot and day >= Date.today():
        ForecastSnapshot.objects.get_or_create(outlet=outlet, date=day, meal=meal, defaults={'expected': expected, 'method': method})
    return {
        'date': day.isoformat(), 'meal': meal, 'expected': expected,
        'low': math.floor(expected * (1 - band)), 'high': math.ceil(expected * (1 + band)),
        'method': method, 'history_points': n, 'data_weight': round(w, 2),
        'factors': {'members': s.members, 'attendance_pct': float(attendance_pct(s, day, meal)), 'menu_pull': float(pull),
                    'special_day': float(sp), 'special_note': special.note if special else ''},
        'dishes': [d.name for d in dishes],
    }


def forecast_accuracy(outlet, days=30):
    """WAPE of pre-meal predictions vs what was actually served."""
    since = Date.today() - timedelta(days=days)
    snaps = {(s.date, s.meal): s.expected for s in ForecastSnapshot.objects.filter(outlet=outlet, date__gte=since)}
    pairs = [(snaps[(a.date, a.meal)], a.actual) for a in Attendance.objects.filter(outlet=outlet, date__gte=since) if (a.date, a.meal) in snaps]
    if not pairs:
        return {'points': 0, 'wape': None, 'note': 'No actual attendance logged yet — forecast is running on estimates.'}
    err = sum(abs(p - a) for p, a in pairs)
    act = sum(a for _, a in pairs) or 1
    return {'points': len(pairs), 'wape': round(err / act * 100, 1), 'note': 'Lower is better; under 10% is good for a mess.'}
