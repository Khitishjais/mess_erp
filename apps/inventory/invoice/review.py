"""Turn the cleaned bill lines into a review table: suggested raw material, quantities converted to OUR purchase unit, and warnings."""
from decimal import Decimal

from apps.prefs import service as prefs

from ..models import RawMaterial
from . import units
from .match import SURE, best_match


def _money(x):
    return None if x is None else round(float(x), 2)


def review_line(line, materials, rate_jump=Decimal('0.30')):
    name, qty, unit, rate, amount = line['name'], line['qty'], line['unit'], line['rate'], line['amount']
    m, sc = best_match(name, materials)
    flags = []
    out = {'name': name, 'bill_qty': float(qty) if qty is not None else None, 'bill_unit': unit, 'bill_rate': _money(rate), 'amount': _money(amount),
           'material': m.id if m else None, 'material_name': m.name if m else '', 'match': sc, 'unit': m.purchase_unit if m else unit, 'qty': None, 'rate': None, 'flags': flags}
    if not m:
        flags.append('no_match')
    elif sc < SURE:
        flags.append('check_match')
    if qty is None or qty <= 0:
        flags.append('no_qty')
        return out
    if rate is None and amount is not None:
        rate = (amount / qty).quantize(Decimal('0.01'))
    if m:
        f = units.factor(unit or m.purchase_unit, m.purchase_unit)
        if f is None:
            flags.append('unit_mismatch')
            return out
        out['qty'] = round(float(qty) * f, 3)
        out['rate'] = _money(rate / Decimal(str(f))) if rate is not None else None
        if m.unit_cost and out['rate'] and abs(Decimal(str(out['rate'])) - m.unit_cost) / m.unit_cost > rate_jump:
            flags.append('rate_jump')
            out['catalogue_rate'] = _money(m.unit_cost)
    else:
        out['qty'], out['rate'] = float(qty), _money(rate)
    if amount is not None and rate is not None and abs(qty * rate - amount) > max(Decimal(1), amount * Decimal('0.02')):
        flags.append('amount_mismatch')
    return out


def build_review(owner, cleaned):
    materials = list(RawMaterial.objects.filter(owner=owner))
    jump = Decimal(prefs.get(owner, 'rate_jump_pct')) / 100          # Settings: warn when a bill price differs by more than this
    lines = [review_line(ln, materials, jump) for ln in cleaned['lines']]
    shown = [x['amount'] for x in lines if x['amount'] is not None]
    warnings = []
    if cleaned['total'] is not None and shown and abs(float(cleaned['total']) - sum(shown)) > max(1, float(cleaned['total']) * 0.01):
        warnings.append(f"The lines add up to {round(sum(shown), 2)} but the bill total says {float(cleaned['total'])}. Check for a missed or misread line.")
    if not lines:
        warnings.append('No items could be read from this bill. Add the lines by hand.')
    return {'supplier': cleaned['supplier'], 'invoice_no': cleaned['invoice_no'], 'date': cleaned['date'], 'total': _money(cleaned['total']),
            'lines': lines, 'warnings': warnings, 'materials': [{'id': m.id, 'name': m.name, 'unit': m.purchase_unit} for m in materials]}
