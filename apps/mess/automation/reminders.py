"""Automation 4: de-duplicated reminders for things nobody has entered yet."""
from datetime import timedelta

from apps.audit.models import Notification
from apps.inventory.models import ClosingStockLog
from apps.prefs import service as prefs

from .. import services as svc
from ..models import Attendance, MealPlan, WastageLog

MEAL_END_HOUR = {'breakfast': 10, 'lunch': 15, 'dinner': 22}      # after this hour a missing attendance entry is flagged


ACCURACY_ALERT_WAPE = 20                                          # % error above which we tell the manager


def _notify(outlet, key, title, body=''):
    full = f'{key}:{outlet.id}'
    if Notification.objects.filter(owner=outlet.owner, key=full).exists():
        return 0                       # already told them; never nag twice
    Notification.objects.create(owner=outlet.owner, key=full, title=f'[{outlet.name}] {title}', body=body)
    return 1


def make_reminders(outlet, now):
    if not prefs.get(outlet.owner, 'reminders_enabled', outlet):             # Settings: switched off for this outlet
        return 0
    made = 0
    today = now.date()
    for day in (today - timedelta(days=1), today):
        for meal in svc.MEALS:
            planned = MealPlan.objects.filter(outlet=outlet, weekday=day.weekday(), meal=meal).exists()
            ended = day < today or now.hour >= MEAL_END_HOUR[meal]
            if planned and ended and not Attendance.objects.filter(outlet=outlet, date=day, meal=meal).exists():
                made += _notify(outlet, f'attendance:{day}:{meal}', f'Enter {meal} attendance for {day}',
                                'Attendance drives the forecast and automatic stock deduction.')
    y = today - timedelta(days=1)
    had_meal = Attendance.objects.filter(outlet=outlet, date=y).exists()
    if had_meal and not ClosingStockLog.objects.filter(outlet=outlet, date=y).exists():
        made += _notify(outlet, f'closing:{y}', f'Closing stock not counted for {y}',
                        'Do a physical count in Inventory > Stock Entry so stock stays accurate.')
    if had_meal and not WastageLog.objects.filter(outlet=outlet, date=y).exists():
        made += _notify(outlet, f'wastage:{y}', f'No wastage logged for {y}',
                        'Log what was thrown away (even a small amount) so the AI can trim cooking quantities.')
    alerts = [a for a in svc.stock_alerts(outlet) if a['type'] in ('expiry', 'low_stock', 'negative_stock')]
    if alerts:
        made += _notify(outlet, f'stock:{today}', f'{len(alerts)} stock alert(s) today', '\n'.join(a['message'] for a in alerts[:8]))
    acc = svc.forecast_accuracy(outlet, 28)
    if acc['points'] >= 6 and acc['wape'] is not None and acc['wape'] > ACCURACY_ALERT_WAPE:
        made += _notify(outlet, f'accuracy:{today.isocalendar()[0]}-{today.isocalendar()[1]}', f"Forecast is {acc['wape']}% off",
                        'Check Mess > Settings: member count, attendance % and special days may need updating.')
    return made
