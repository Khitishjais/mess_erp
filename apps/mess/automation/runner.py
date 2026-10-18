"""Runs every job for every mess outlet and logs the run."""
from datetime import datetime, timedelta

from .. import services as svc
from ..models import Attendance, AutomationRun, DailyPlan
from .common import _clean, mess_outlets
from .consumption import apply_consumption
from .plans import generate_daily_plan
from .reminders import make_reminders
from .reports import build_daily_report


def run_daily(now=None, outlet_id=None, trigger='schedule'):
    now = now or datetime.now()
    today = now.date()
    results = []
    for outlet in mess_outlets(outlet_id):
        summary = {'outlet': outlet.name}
        run = AutomationRun(job='daily', outlet=outlet, trigger=trigger)
        try:
            days = (today - timedelta(days=1), today)
            summary['stock_changes'] = sum(apply_consumption(outlet, d, m) for d in days for m in svc.MEALS)
            for d in days:
                if Attendance.objects.filter(outlet=outlet, date=d).exists():
                    build_daily_report(outlet, d)
                    summary.setdefault('reports', []).append(str(d))
            for d in (today + timedelta(days=1), today):
                if d > today or not DailyPlan.objects.filter(outlet=outlet, date=d).exists():
                    generate_daily_plan(outlet, d)
                    summary.setdefault('plans', []).append(str(d))
            summary['reminders'] = make_reminders(outlet, now)
        except Exception as e:      # one outlet failing must not stop the others
            run.ok = False
            summary['error'] = f'{type(e).__name__}: {e}'
        run.summary = _clean(summary)
        run.save()
        results.append({**run.summary, 'ok': run.ok})
    return results
