"""Automation endpoints: run now, status, saved daily plan and report."""
from datetime import date as Date

import hmac
import os

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import IsPortalManagerOrReadOnly, IsPortalUser
from apps.common.request import resolve_day, resolve_outlet

from .. import automation
from ..models import AutomationRun, DailyPlan, DailyReport


@api_view(['POST'])
@permission_classes([IsPortalManagerOrReadOnly])
def automation_run(request):
    """'Run now': same job the scheduler runs (plans, stock deduction, report, reminders)."""
    o = resolve_outlet(request)
    return Response(automation.run_daily(outlet_id=o.id, trigger='manual'))


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def automation_cron(request):
    """For hosts with no scheduler: an outside timer (cron-job.org, GitHub Actions ...) calls this once or twice a day with
    the header  Authorization: Bearer <CRON_SECRET>.  Off (404) unless CRON_SECRET is set; wrong secret = 403. Runs the same job as `manage.py daily_run`."""
    secret = os.environ.get('CRON_SECRET', '')
    if len(secret) < 16:
        return Response({'detail': 'Not found.'}, status=404)
    sent = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    if not hmac.compare_digest(sent.encode(), secret.encode()):
        return Response({'detail': 'Forbidden.'}, status=403)
    return Response({'ran': automation.run_daily(trigger='cron')})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def automation_status(request):
    o = resolve_outlet(request)
    runs = [{'at': r.started_at, 'trigger': r.trigger, 'ok': r.ok, 'summary': r.summary} for r in AutomationRun.objects.filter(outlet=o)[:8]]
    plan = DailyPlan.objects.filter(outlet=o, date__gte=Date.today()).order_by('date').first()
    rep = DailyReport.objects.filter(outlet=o).first()
    return Response({'runs': runs, 'last_run': runs[0] if runs else None,
                     'next_plan': {'date': plan.date, 'generated_at': plan.generated_at} if plan else None,
                     'latest_report': {'date': rep.date, 'generated_at': rep.generated_at} if rep else None})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def daily_plan(request):
    o, d = resolve_outlet(request), resolve_day(request)
    p = DailyPlan.objects.filter(outlet=o, date=d).first()
    return Response({'date': d, 'generated_at': p.generated_at, **p.payload} if p else {'date': d, 'missing': True})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def daily_report(request):
    o = resolve_outlet(request)
    qs = DailyReport.objects.filter(outlet=o)
    if request.query_params.get('date'):
        qs = qs.filter(date=resolve_day(request))
    r = qs.first()
    return Response({'date': r.date, 'generated_at': r.generated_at, **r.payload} if r else {'missing': True})
