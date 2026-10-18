"""Run the mess automation once: plan for tomorrow, stock deduction, daily report, reminders.
Schedule it twice a day (e.g. 06:00 and 21:30). See scripts/schedule_daily_run.ps1."""
from datetime import datetime

from django.core.management.base import BaseCommand

from apps.mess.automation import run_daily


class Command(BaseCommand):
    help = 'Generate plans, apply stock consumption, build the daily report and create reminders.'

    def add_arguments(self, p):
        p.add_argument('--outlet', type=int, default=None)
        p.add_argument('--now', default=None, help='Pretend it is this time (YYYY-MM-DD HH:MM), for testing')

    def handle(self, *a, outlet=None, now=None, **kw):
        when = datetime.strptime(now, '%Y-%m-%d %H:%M') if now else None
        for r in run_daily(now=when, outlet_id=outlet):
            self.stdout.write(('OK   ' if r['ok'] else 'FAIL ') + str(r))
