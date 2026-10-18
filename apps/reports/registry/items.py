"""Item based reports (item, category, hour, tag, row-per-line)."""
from django.db.models import F, Sum
from django.db.models.functions import ExtractHour

from .columns import DATE, INT, MONEY, ZERO, col
from .filters import item_qs

ITEM_AGG = {'q_sum': Sum('qty'), 'amt_sum': Sum(F('qty') * F('price')), 'disc_sum': Sum('discount'), 'tax_sum': Sum('tax_amount')}


def item_group(groups, label_map=None):
    def build(request):
        qs = item_qs(request)
        paths = list(groups.values())
        rows = []
        for r in qs.values(*paths).annotate(**ITEM_AGG).order_by(*paths):
            d = {k: r[p] for k, p in groups.items()}
            d.update(qty=r['q_sum'] or ZERO, amount=r['amt_sum'] or ZERO, discount=r['disc_sum'] or ZERO, tax=r['tax_sum'] or ZERO)
            d['net'] = d['amount'] - d['discount']
            rows.append(d)
        cols = [col(k, (label_map or {}).get(k, k.replace('_', ' ').title())) for k in groups] + [
            col('qty', 'Qty', INT), col('amount', 'Amount', MONEY), col('discount', 'Discount', MONEY),
            col('net', 'Net', MONEY), col('tax', 'Tax', MONEY)]
        return cols, rows
    return build


def hourly_items(request):
    qs = item_qs(request).annotate(hr=ExtractHour('order__created_at'))
    rows = []
    for r in qs.values('hr', 'name').annotate(**ITEM_AGG).order_by('hr', 'name'):
        rows.append({'hour': f"{r['hr']:02d}:00-{r['hr']:02d}:59", 'item': r['name'], 'qty': r['q_sum'], 'amount': r['amt_sum'] or ZERO})
    return [col('hour', 'Hour'), col('item', 'Item'), col('qty', 'Qty', INT), col('amount', 'Amount', MONEY)], rows


def item_rows(force_status=None, cancelled_only=False):
    def build(request):
        qs = item_qs(request, force_status, include_cancelled_lines=cancelled_only)
        if cancelled_only:
            qs = qs.filter(is_cancelled=True) | item_qs(request, 'cancelled', True)
        rows = [{'invoice_no': i.order.invoice_no, 'created_at': i.order.created_at, 'outlet': i.order.outlet.name,
                 'category': i.category_name, 'item': i.name, 'qty': i.qty, 'price': i.price, 'amount': i.qty * i.price,
                 'discount': i.discount, 'tax': i.tax_amount, 'customer': i.order.customer_name, 'status': i.order.get_status_display()}
                for i in qs.select_related('order__outlet').order_by('-order__created_at')]
        return [col('invoice_no', 'Invoice No.'), col('created_at', 'Date', DATE), col('outlet', 'Restaurant'),
                col('category', 'Category'), col('item', 'Item'), col('qty', 'Qty', INT), col('price', 'Price', MONEY),
                col('amount', 'Amount', MONEY), col('discount', 'Discount', MONEY), col('tax', 'Tax', MONEY),
                col('customer', 'Customer'), col('status', 'Status')], rows
    return build


def tag_wise(request):
    qs = item_qs(request).exclude(item__tags=None)
    rows = [{'tag': r['item__tags__name'], 'qty': r['q_sum'], 'amount': r['amt_sum'] or ZERO}
            for r in qs.values('item__tags__name').annotate(**ITEM_AGG).order_by('item__tags__name')]
    return [col('tag', 'Tag'), col('qty', 'Qty', INT), col('amount', 'Amount', MONEY)], rows
