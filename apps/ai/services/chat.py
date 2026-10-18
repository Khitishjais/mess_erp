"""Question router: answers known questions from our own numbers (no LLM needed)."""
from collections import defaultdict
from datetime import date as Date
from datetime import timedelta

from django.db.models import Count, Sum

from apps.mess import services as mess
from apps.orders.models import Order, OrderItem


def answer(question, outlet, outlets):
    q = question.lower()
    today = Date.today()
    tomorrow = today + timedelta(days=1)
    has = lambda *ws: any(w in q for w in ws)

    if has('wastage', 'waste', 'barbaad', 'bach', 'phenk', 'fenk'):
        r = mess.wastage_insights(outlet)
        return {'intent': 'wastage', 'answer': f"Last {r['days']} days wastage cost: Rs {r['total_cost'] or 0}. " + (' '.join(r['tips'][:2]) or 'No wastage logged yet.'), 'data': r}
    if has('purchase', 'kharid', 'buy', 'order karna', 'mangwa'):
        p = mess.purchase_plan(outlet, today, 7)
        top = ', '.join(f"{r['material']} {r['buy']} {r['unit']}" for r in p['rows'] if r['buy'] > 0)
        return {'intent': 'purchase', 'answer': f"7-day purchase plan: Rs {p['total']}. Buy: {top or 'nothing, stock covers it'}.", 'data': p}
    if has('alert', 'expire', 'dead stock', 'low stock', 'kam stock', 'kharab'):
        a = mess.stock_alerts(outlet)
        return {'intent': 'alerts', 'answer': '; '.join(x['message'] for x in a[:5]) or 'No stock alerts.', 'data': a}
    if has('staff', 'cook', 'rasoiya', 'server', 'kitne log kaam'):
        s = mess.staffing(outlet, tomorrow if has('kal', 'tomorrow') else today)
        return {'intent': 'staffing', 'answer': '; '.join(f"{x['meal']}: {x['cooks']} cooks, {x['servers']} servers for {x['expected']} people" for x in s), 'data': s}
    day = tomorrow if has('kal', 'tomorrow') else today
    mats = {m['material'].lower(): m for meal in mess.day_plan(outlet, day)['meals'].values() for m in meal['materials']} if has('kitna', 'how much', 'lagega', 'need', 'chahiye', 'quantity') else {}
    if mats:
        wanted = [name for name in mats if name.split()[0] in q] or None
        if wanted:
            tot = defaultdict(float)
            for meal in mess.day_plan(outlet, day)['meals'].values():
                for m in meal['materials']:
                    if m['material'].lower() in wanted:
                        tot[(m['material'], m['unit'])] += float(m['qty'])
            txt = '; '.join(f"{n}: {round(v / 1000, 2) if u == 'gm' else round(v, 1)} {'kg' if u == 'gm' else u}" for (n, u), v in tot.items())
            return {'intent': 'ingredient', 'answer': f"{day}: {txt}", 'data': dict(tot.items()) and [{'material': k[0], 'qty': v, 'unit': k[1]} for k, v in tot.items()]}
    if has('forecast', 'kitne log', 'headcount', 'attendance', 'kitne student', 'people', 'plates'):
        f = [mess.forecast_headcount(outlet, day, m, snapshot=False) for m in mess.MEALS]
        return {'intent': 'forecast', 'answer': f"{day}: " + '; '.join(f"{x['meal']} ~{x['expected']} ({x['low']}-{x['high']})" for x in f), 'data': f}
    if has('sales', 'bikri', 'revenue', 'kamai', 'collection'):
        a = Order.objects.filter(outlet__in=outlets, created_at__date=today, status='success').aggregate(t=Sum('total'), n=Count('id'))
        return {'intent': 'sales', 'answer': f"Today: {a['n'] or 0} bills, Rs {a['t'] or 0}.", 'data': a}
    if has('top', 'best', 'sabse zyada', 'popular', 'most sold'):
        r = list(OrderItem.objects.filter(order__outlet__in=outlets, order__created_at__date__gte=today - timedelta(days=7), is_cancelled=False)
                 .values('name').annotate(q=Sum('qty')).order_by('-q')[:5])
        return {'intent': 'top_items', 'answer': 'Top items (7 days): ' + ', '.join(f"{x['name']} ({x['q']})" for x in r), 'data': r}
    return None
