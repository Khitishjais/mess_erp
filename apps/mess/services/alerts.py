"""Dead stock, over-stock, expiry, low and negative stock alerts."""
from datetime import date as Date
from decimal import Decimal

from apps.inventory.models import RawMaterial, StockLedger
from apps.prefs import service as prefs

from .purchasing import current_stock, purchase_plan


def stock_alerts(outlet, horizon=None):
    horizon = horizon or prefs.get(outlet.owner, 'alert_horizon_days')          # Settings
    plan = purchase_plan(outlet, Date.today(), horizon)
    used = {r['material_id']: r for r in plan['rows']}
    alerts = []
    last_buy = {}
    for row in StockLedger.objects.filter(outlet=outlet, purchase__gt=0).order_by('-date'):
        last_buy.setdefault(row.material_id, row.date)
    stock = current_stock(outlet)
    if not stock:
        return [{'type': 'no_stock_data', 'material': '', 'message': 'No stock has been entered yet, so stock alerts and net purchase quantities cannot be exact. Add opening stock in Inventory > Stock Entry.'}]
    for mid, qty in stock.items():
        if qty < 0:
            m = RawMaterial.objects.get(pk=mid)
            alerts.append({'type': 'negative_stock', 'material': m.name,
                           'message': f'Stock shows {qty} {m.purchase_unit}: more was used than recorded as bought. Enter the purchase or a counted stock.'})
            continue
        if qty <= 0:
            continue
        m = RawMaterial.objects.get(pk=mid)
        r = used.get(mid)
        if not r:
            alerts.append({'type': 'dead_stock', 'material': m.name, 'message': f'{qty} {m.purchase_unit} in stock but not used in the next {horizon} days menu'})
        elif r['need'] and qty > r['need'] * 2:
            alerts.append({'type': 'overstock', 'material': m.name, 'message': f'Stock {qty} {m.purchase_unit} is more than 2x the {horizon}-day need ({r["need"]})'})
        bought = last_buy.get(mid)
        if bought and (Date.today() - bought).days >= m.shelf_life_days - 1:
            alerts.append({'type': 'expiry', 'material': m.name, 'message': f'Bought {bought}; shelf life {m.shelf_life_days} days — use or discard today'})
    for r in plan['rows'][:15]:                 # most expensive first, keep the list short
        if r['buy'] > 0 and r['in_stock'] < r['need'] * Decimal('0.3'):
            alerts.append({'type': 'low_stock', 'material': r['material'], 'message': f'Only {r["in_stock"]} {r["unit"]} left, need {r["need"]} for the coming days'})
    return alerts
