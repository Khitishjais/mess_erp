"""Automation 1: save tomorrow's cook / buy / staff plan."""
from .. import services as svc
from ..models import DailyPlan
from .common import _clean


def generate_daily_plan(outlet, day):
    plan = svc.day_plan(outlet, day)
    payload = _clean({'plan': plan, 'purchase': svc.purchase_plan(outlet, day, 7), 'alerts': svc.stock_alerts(outlet),
                      'staffing': svc.staffing(outlet, day)})
    obj, _ = DailyPlan.objects.update_or_create(outlet=outlet, date=day, defaults={'payload': payload})
    return obj
