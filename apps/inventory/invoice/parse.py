"""Clean whatever the reader (AI model or a person) produced into a strict, safe shape. Nothing the reader says is trusted as-is."""
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

MAX_LINES = 200
MAX_QTY, MAX_RATE = Decimal('1000000'), Decimal('10000000')


def extract_json(text):
    """The first {...} object in a model reply (handles ```json fences and chatter around it)."""
    s = (text or '').strip()
    a, b = s.find('{'), s.rfind('}')
    if a < 0 or b <= a:
        raise ValueError('The reply had no invoice data.')
    return json.loads(s[a: b + 1])


def num(v, hi=MAX_RATE):
    """A non-negative Decimal with 3 places, or None for junk (text, NaN, negative, huge)."""
    try:
        d = Decimal(re.sub(r'[,\s₹]|Rs\.?', '', str(v)))
    except (InvalidOperation, TypeError):
        return None
    if not d.is_finite() or d < 0 or d > hi:
        return None
    return d.quantize(Decimal('0.001'))


def text(v, n=120):
    return re.sub(r'\s+', ' ', str(v or '')).strip()[:n]


def iso_date(v):
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        return ''


def clean(raw):
    """-> {supplier, invoice_no, date, total, lines:[{name, qty, unit, rate, amount}]}. Lines without a name are dropped."""
    if not isinstance(raw, dict):
        raise ValueError('Invoice data must be an object.')
    lines = []
    for r in (raw.get('lines') if isinstance(raw.get('lines'), list) else [])[:MAX_LINES]:
        if not isinstance(r, dict) or not text(r.get('name')):
            continue
        lines.append({'name': text(r['name']), 'qty': num(r.get('qty'), MAX_QTY), 'unit': text(r.get('unit'), 20),
                      'rate': num(r.get('rate')), 'amount': num(r.get('amount'))})
    return {'supplier': text(raw.get('supplier')), 'invoice_no': text(raw.get('invoice_no'), 60), 'date': iso_date(raw.get('date')),
            'total': num(raw.get('total')), 'lines': lines}
