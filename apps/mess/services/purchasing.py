"""Current stock and the purchase plan (need minus stock, shelf-life aware, rounded to pack size)."""
import math
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from apps.inventory.models import RawMaterial, StockLedger

from .config import MEALS
from .requirements import meal_requirement


def current_stock(outlet):
    """Latest counted closing stock per material (purchase units)."""
    out = {}
    for row in StockLedger.objects.filter(outlet=outlet).order_by('material_id', '-date').select_related('material'):
        if row.material_id not in out:
            out[row.material_id] = row.stock_closing if row.stock_closing else row.closing
    return out


def purchase_plan(outlet, start, days=7):
    """Need over the horizon minus stock. Perishables are bought only for their shelf life, rounded up to pack size."""
    per_day = defaultdict(lambda: defaultdict(Decimal))
    for i in range(days):
        d = start + timedelta(days=i)
        for meal in MEALS:
            for m in meal_requirement(outlet, d, meal)['materials']:
                per_day[m['material_id']][i] += Decimal(str(m['qty']))
    stock = current_stock(outlet)
    rows = []
    for mid, by_day in per_day.items():
        m = RawMaterial.objects.get(pk=mid)
        cover = min(days, max(1, m.shelf_life_days))           # don't stock more than will stay fresh
        need_units = sum(v for i, v in by_day.items() if i < cover) / m.conversion
        have = stock.get(mid, Decimal(0))
        buy = max(Decimal(0), need_units - have)
        if buy > 0 and m.pack_size > 0:
            buy = Decimal(math.ceil(buy / m.pack_size)) * m.pack_size
        rows.append({'material_id': mid, 'material': m.name, 'unit': m.purchase_unit, 'days_covered': cover,
                     'need': round(need_units, 3), 'in_stock': round(have, 3), 'buy': round(buy, 3),
                     'rate': m.unit_cost, 'cost': round(buy * m.unit_cost, 2), 'perishable': m.shelf_life_days <= 3})
    rows.sort(key=lambda r: (-r['cost'], r['material']))
    return {'start': start.isoformat(), 'days': days, 'rows': rows, 'total': round(sum(r['cost'] for r in rows), 2)}
