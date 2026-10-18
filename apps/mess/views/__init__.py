"""Mess HTTP endpoints, grouped by purpose (crud / planning / automation)."""
from .automation import automation_cron, automation_run, automation_status, daily_plan, daily_report
from .crud import (
    AttendanceViewSet,
    MealPlanViewSet,
    RecipeViewSet,
    SettingViewSet,
    SpecialDayViewSet,
    WastageViewSet,
)
from .planning import (
    alerts,
    forecast,
    menu_eng,
    plan,
    purchase_draft,
    purchases,
    wastage_report,
    weekly_menu,
)

__all__ = [
    'automation_cron',
    'SettingViewSet',
    'SpecialDayViewSet',
    'RecipeViewSet',
    'MealPlanViewSet',
    'AttendanceViewSet',
    'WastageViewSet',
    'weekly_menu',
    'forecast',
    'plan',
    'purchases',
    'purchase_draft',
    'alerts',
    'wastage_report',
    'menu_eng',
    'automation_run',
    'automation_status',
    'daily_plan',
    'daily_report',
]
