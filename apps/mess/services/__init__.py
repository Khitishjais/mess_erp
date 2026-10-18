"""Mess planning AI layer.

Every number starts as an explicit ESTIMATE (defaults below / MessSetting) and is replaced by what the mess
actually records (Attendance, WastageLog) as data builds up. Nothing here needs an external service."""
from .alerts import stock_alerts
from .config import (
    ALPHA,
    DAY_KEYS,
    DEFAULT_ATTENDANCE,
    HISTORY_WEEKS,
    MEALS,
    PRIOR_STRENGTH,
    attendance_pct,
    dishes_for,
    round_half_up,
    setting_for,
)
from .forecast import forecast_accuracy, forecast_headcount
from .menu import menu_engineering
from .purchasing import current_stock, purchase_plan
from .requirements import day_plan, material_cost, meal_requirement, recipe_plate_cost
from .staffing import staffing
from .wastage import wastage_insights

__all__ = [
    'stock_alerts',
    'ALPHA',
    'DAY_KEYS',
    'DEFAULT_ATTENDANCE',
    'HISTORY_WEEKS',
    'MEALS',
    'PRIOR_STRENGTH',
    'attendance_pct',
    'round_half_up',
    'dishes_for',
    'setting_for',
    'forecast_accuracy',
    'forecast_headcount',
    'menu_engineering',
    'current_stock',
    'purchase_plan',
    'day_plan',
    'material_cost',
    'meal_requirement',
    'recipe_plate_cost',
    'staffing',
    'wastage_insights',
]
