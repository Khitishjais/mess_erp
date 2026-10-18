"""Kitchen ready-time estimate (heuristic until timings are recorded)."""
from apps.orders.models import Kot

BASE_MIN = {'starters': 10, 'main': 15, 'beverage': 4, 'dessert': 5, 'bread': 6}


def kitchen_eta(outlet, categories):
    open_kots = Kot.objects.filter(order__outlet=outlet, status__in=['new', 'preparing']).count()
    base = max([next((v for k, v in BASE_MIN.items() if k in c.lower()), 12) for c in categories] or [12])
    load = round(open_kots * 1.5)
    return {'minutes': base + load, 'base': base, 'queue_kots': open_kots, 'method': 'heuristic',
            'note': 'Rule of thumb (dish type + queue). Becomes data-driven once KOT start/ready times are recorded.'}
