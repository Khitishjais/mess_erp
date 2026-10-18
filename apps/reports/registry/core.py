"""Report registry (code -> report) and the totals/min/max/avg rows."""
from decimal import Decimal

from .columns import INT, MONEY

REPORTS = {}


def reg(code, title, desc, builder):
    REPORTS[code] = {'code': code, 'title': title, 'description': desc, 'build': builder}


def totals(cols, rows):
    nums = [c['key'] for c in cols if c['type'] in (MONEY, INT)]
    out = {}
    for label, fn in (('Total', sum), ('Min.', min), ('Max.', max), ('Avg.', lambda v: sum(v) / len(v))):
        out[label] = {k: fn([Decimal(str(r[k] or 0)) for r in rows]) for k in nums} if rows else {}
    return out
