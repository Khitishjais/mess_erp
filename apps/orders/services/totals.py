"""Bill totals. Pure functions (no database) that mirror the POS formula in pos/src/billing.js, so both always agree."""
from decimal import ROUND_HALF_UP, Decimal

D = lambda v: Decimal(str(v or 0))   # noqa: E731  (None / '' / number -> Decimal)
Q = Decimal('0.01')


def paise(value):
    """Round to 2 decimals, halves UP (the POS rounds the same way, so both always agree to the paisa)."""
    return Decimal(value).quantize(Q, rounding=ROUND_HALF_UP)


CHARGE_FIELDS = ('delivery_charge', 'container_charge', 'service_charge', 'additional_charge')


def compute_totals(payload):
    """my_amount, discount, total_tax, round_off and total, recomputed from the lines the POS sent."""
    live = [i for i in payload.get('items', []) if not i.get('is_cancelled')]
    my_amount = sum((paise(D(i['qty']) * D(i['price'])) for i in live), Decimal(0))      # each line to the paisa, then added
    discount = D(payload.get('discount')) + sum((D(i.get('discount')) for i in live), Decimal(0))
    total_tax = paise(sum((D(t['amount']) for t in payload.get('taxes', [])), Decimal(0)))
    charges = sum(D(payload.get(k)) for k in CHARGE_FIELDS)
    round_off = D(payload.get('round_off'))
    total = paise(my_amount - discount + total_tax + charges + round_off - D(payload.get('waived_off')))
    return {'my_amount': my_amount, 'discount': discount, 'total_tax': total_tax, 'round_off': round_off, 'total': total}
