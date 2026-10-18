"""Cooks and servers needed per meal."""
import math

from .config import MEALS, setting_for
from .forecast import forecast_headcount


def staffing(outlet, day):
    s = setting_for(outlet)
    out = []
    for meal in MEALS:
        fc = forecast_headcount(outlet, day, meal, snapshot=False)
        out.append({'meal': meal, 'expected': fc['expected'], 'cooks': max(1, math.ceil(fc['expected'] / s.staff_plates_per_cook)),
                    'servers': max(1, math.ceil(fc['expected'] / s.staff_plates_per_server))})
    return out
