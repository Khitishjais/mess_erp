"""Apply a REVIEWED bill: add the purchases to the stock ledger, optionally update catalogue rates, and remember the bill so it cannot be entered twice."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog

from ..ledger import add_to_ledger
from ..models import ClosingStockLog, InvoiceImport, RawMaterial
from . import units
from .parse import MAX_LINES, MAX_QTY, MAX_RATE, iso_date, num, text


class Duplicate(ValidationError):
    status_code = 409


def _line(owner, raw, i):
    if not isinstance(raw, dict):
        raise ValidationError(f'Line {i}: invalid.')
    qty = num(raw.get('qty'), MAX_QTY)
    rate = num(raw.get('rate') if raw.get('rate') not in (None, '') else 0, MAX_RATE)
    if not qty or qty <= 0:
        raise ValidationError(f'Line {i}: quantity must be more than 0.')
    if rate is None:
        raise ValidationError(f'Line {i}: rate is not a valid number.')
    return qty, rate, _material(owner, raw, i)


def _material(owner, raw, i):
    if raw.get('material'):
        m = RawMaterial.objects.filter(owner=owner, pk=raw['material']).first() if str(raw['material']).isdigit() else None
        if not m:
            raise ValidationError(f'Line {i}: that raw material does not exist.')
        return m
    new = raw.get('new_material')
    name = text(new.get('name'), 200) if isinstance(new, dict) else ''
    if not name:
        raise ValidationError(f'Line {i}: choose a raw material or give a name for a new one.')
    existing = RawMaterial.objects.filter(owner=owner, name__iexact=name).first()
    if existing:
        return existing
    unit = units.canon(new.get('unit')) or 'kg'
    cons, conv = units.base_units(unit)
    return RawMaterial.objects.create(owner=owner, name=name, purchase_unit=unit, consumption_unit=cons, conversion=conv)


def _bill_date(payload):
    day = date.fromisoformat(iso_date(payload.get('date')) or date.today().isoformat())
    if day > date.today() + timedelta(days=1) or day < date.today() - timedelta(days=366):
        raise ValidationError('The bill date must be within the last year and not in the future.')
    return day


def apply_invoice(user, outlet, payload):
    owner = user.tenant_owner
    day = _bill_date(payload)
    raw_lines = payload.get('lines')
    if not isinstance(raw_lines, list) or not 1 <= len(raw_lines) <= MAX_LINES:
        raise ValidationError(f'Send between 1 and {MAX_LINES} lines.')
    supplier, number = text(payload.get('supplier')), text(payload.get('invoice_no'), 60)
    if number and InvoiceImport.objects.filter(outlet=outlet, supplier__iexact=supplier, invoice_no__iexact=number).exists():
        raise Duplicate(f'Bill {number} from {supplier or "this supplier"} was already entered.')
    with transaction.atomic():
        parsed = [_line(owner, r, i + 1) for i, r in enumerate(raw_lines)]
        total, rates = Decimal(0), 0
        for qty, rate, m in parsed:
            add_to_ledger(outlet, m, day, 'purchase', qty)
            total += qty * rate
            if payload.get('update_rates') and rate > 0 and m.unit_cost != rate:
                m.unit_cost = rate
                m.save(update_fields=['unit_cost'])
                rates += 1
        ClosingStockLog.objects.update_or_create(outlet=outlet, date=day, defaults={'updated_by': user})
        rec = InvoiceImport.objects.create(owner=owner, outlet=outlet, supplier=supplier, invoice_no=number, date=day, total=round(total, 2),
                                           line_count=len(parsed), created_by=user)
        AuditLog.objects.create(owner=owner, outlet=outlet, actor=user, kind='invoice_import',
                                message=f'Bill {number or "(no number)"} from {supplier or "?"}: {len(parsed)} lines, Rs {round(total, 2)}'[:300])
    return {'id': rec.id, 'lines': len(parsed), 'total': float(round(total, 2)), 'rates_updated': rates}
