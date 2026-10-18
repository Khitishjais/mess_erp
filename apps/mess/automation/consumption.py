"""Automation 3: deduct ingredients from stock from real attendance (idempotent)."""
from decimal import Decimal

from django.db import transaction

from apps.inventory.ledger import add_to_ledger
from apps.inventory.models import RawMaterial
from apps.prefs import service as prefs

from .. import services as svc
from ..models import Attendance, AutoConsumption


@transaction.atomic
def apply_consumption(outlet, day, meal):
    """Deduct what this meal used (real headcount x recipes, in purchase units). Re-running only applies the difference."""
    if not prefs.get(outlet.owner, 'auto_deduct_stock', outlet):          # Settings: switched off for this outlet
        return 0
    att = Attendance.objects.filter(outlet=outlet, date=day, meal=meal).first()
    done = AutoConsumption.objects.filter(outlet=outlet, date=day, meal=meal).first()
    new = {}
    if att:
        req = svc.meal_requirement(outlet, day, meal, headcount=att.actual)
        new = {str(m['material_id']): Decimal(str(m['purchase_qty'])) for m in req['materials']}
    old = {k: Decimal(v) for k, v in (done.payload if done else {}).items()}
    changed = 0
    for mid in set(new) | set(old):
        delta = new.get(mid, Decimal(0)) - old.get(mid, Decimal(0))
        if delta == 0:
            continue
        add_to_ledger(outlet, RawMaterial.objects.get(pk=int(mid)), day, 'consumed', delta)
        changed += 1
    if att:
        AutoConsumption.objects.update_or_create(outlet=outlet, date=day, meal=meal,
                                                 defaults={'payload': {k: str(v) for k, v in new.items()}, 'headcount': att.actual})
    elif done:
        done.delete()
    return changed
