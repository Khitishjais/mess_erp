"""Checks a POS bill BEFORE anything is saved. Raises ValueError with a plain message the POS can show."""
import uuid
from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_datetime

from ..models import Order, Payment
from .totals import paise

MAX_MONEY = Decimal('9999999999.99')        # fits NUMERIC(12,2)
ORDER_TYPES = {c for c, _ in Order.Type.choices}
STATUSES = {c for c, _ in Order.Status.choices}
STAGES = {c for c, _ in Order.Stage.choices}
PAY_MODES = {c for c, _ in Payment.Mode.choices}


def _num(value, label, *, minimum=None, maximum=None, positive=False):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{label} must be a number.')
    if not d.is_finite():
        raise ValueError(f'{label} must be a finite number.')
    if positive and d <= 0:
        raise ValueError(f'{label} must be more than 0.')
    if minimum is not None and d < minimum:
        raise ValueError(f'{label} cannot be less than {minimum}.')
    if (maximum is not None and d > maximum) or abs(d) > MAX_MONEY:
        raise ValueError(f'{label} is too large.')
    return d


def _optional(payload, key, label, **kw):
    v = payload.get(key)
    return _num(v, label, **kw) if v not in (None, '') else Decimal(0)


def validate_bill(payload):
    """Returns nothing; raises ValueError describing the first problem found."""
    if not isinstance(payload, dict):
        raise ValueError('A bill must be an object.')
    try:
        uuid.UUID(str(payload['client_uuid']))
    except (KeyError, ValueError, AttributeError):
        raise ValueError('client_uuid must be a valid UUID.')
    inv = payload.get('invoice_no')
    if not isinstance(inv, str) or not inv.strip() or len(inv) > 30:
        raise ValueError('invoice_no is required (max 30 characters).')
    if not isinstance(payload.get('created_at'), str) or parse_datetime(payload['created_at']) is None:
        raise ValueError('created_at must be an ISO date-time.')
    for key, allowed in (('order_type', ORDER_TYPES), ('status', STATUSES), ('stage', STAGES)):
        if key in payload and payload[key] not in allowed:
            raise ValueError(f'{key} must be one of: {", ".join(sorted(allowed))}.')

    for key in ('discount', 'delivery_charge', 'container_charge', 'service_charge', 'additional_charge', 'waived_off', 'tip'):
        _optional(payload, key, key, minimum=Decimal(0))
    _optional(payload, 'round_off', 'round_off', minimum=Decimal(-10), maximum=Decimal(10))

    items = payload.get('items', [])
    if not isinstance(items, list):
        raise ValueError('items must be a list.')
    subtotal = Decimal(0)
    for n, i in enumerate(items, 1):
        if not isinstance(i, dict) or not str(i.get('name') or '').strip():
            raise ValueError(f'Line {n}: name is required.')
        qty = _num(i.get('qty'), f'Line {n} quantity', positive=True)
        price = _num(i.get('price'), f'Line {n} price', minimum=Decimal(0))
        _optional(i, 'discount', f'Line {n} discount', minimum=Decimal(0))
        _optional(i, 'tax_rate', f'Line {n} tax rate', minimum=Decimal(0), maximum=Decimal(100))
        _optional(i, 'tax_amount', f'Line {n} tax amount', minimum=Decimal(0))
        if not i.get('is_cancelled'):
            subtotal += paise(qty * price)          # same per-line rounding as the totals, so a correct POS bill is never rejected

    taxes = payload.get('taxes', [])
    if not isinstance(taxes, list):
        raise ValueError('taxes must be a list.')
    for n, t in enumerate(taxes, 1):
        if not isinstance(t, dict) or not str(t.get('name') or '').strip():
            raise ValueError(f'Tax {n}: name is required.')
        _num(t.get('rate'), f'Tax {n} rate', minimum=Decimal(0), maximum=Decimal(100))
        _num(t.get('amount'), f'Tax {n} amount', minimum=Decimal(0))

    pays = payload.get('payments', [])
    if not isinstance(pays, list):
        raise ValueError('payments must be a list.')
    for n, p in enumerate(pays, 1):
        if not isinstance(p, dict) or p.get('mode') not in PAY_MODES:
            raise ValueError(f'Payment {n}: mode must be one of: {", ".join(sorted(PAY_MODES))}.')
        _num(p.get('amount'), f'Payment {n} amount', positive=True)

    kots = payload.get('kots', [])
    if not isinstance(kots, list):
        raise ValueError('kots must be a list.')
    for n, k in enumerate(kots, 1):
        if not isinstance(k, dict) or not isinstance(k.get('number'), int) or isinstance(k.get('number'), bool) or k['number'] < 1:
            raise ValueError(f'KOT {n}: number must be a whole number 1 or more.')

    line_discounts = sum((Decimal(str(i.get('discount') or 0)) for i in items if not i.get('is_cancelled')), Decimal(0))
    if Decimal(str(payload.get('discount') or 0)) + line_discounts > subtotal:
        raise ValueError('Discount is more than the bill amount.')
