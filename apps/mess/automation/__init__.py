"""Scheduled automation for the mess (run by `manage.py daily_run`, or from the portal's "Run now").

 1. generate_daily_plan   - tomorrow's (and today's, if missing) cook / buy / staff plan, saved
 3. apply_consumption     - stock is reduced from real attendance x recipes (idempotent: safe to re-run)
 4. make_reminders        - de-duplicated notifications for things nobody has entered yet
 5. build_daily_report    - end-of-day summary: forecast vs served, cost per plate, wastage, issues

Nothing here sends messages or buys anything. Purchases stay drafts a manager approves."""
from .common import mess_outlets
from .consumption import apply_consumption
from .plans import generate_daily_plan
from .reminders import ACCURACY_ALERT_WAPE, MEAL_END_HOUR, make_reminders
from .reports import build_daily_report
from .runner import run_daily

__all__ = [
    'mess_outlets',
    'apply_consumption',
    'generate_daily_plan',
    'ACCURACY_ALERT_WAPE',
    'MEAL_END_HOUR',
    'make_reminders',
    'build_daily_report',
    'run_daily',
]
