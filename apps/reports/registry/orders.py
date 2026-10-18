"""Row-per-order reports."""
from .columns import DATE, INT, MONEY, col
from .filters import order_qs


def order_rows(filt=None, force_status=None, cols_extra=()):
    base = [col('invoice_no', 'Invoice No.'), col('created_at', 'Date', DATE), col('outlet', 'Restaurant'),
            col('order_type', 'Order Type'), col('sub_order_type', 'Sub Order Type'), col('status', 'Status'),
            col('biller', 'Biller'), col('customer_name', 'Customer'), col('customer_phone', 'Phone'),
            col('locality', 'Locality'), col('my_amount', 'My Amount', MONEY), col('discount', 'Discount', MONEY),
            col('discount_reason', 'Discount Reason'), col('net', 'Net Sales', MONEY), col('delivery_charge', 'Delivery Charge', MONEY),
            col('container_charge', 'Container Charge', MONEY), col('service_charge', 'Service Charge', MONEY),
            col('total_tax', 'Total Tax', MONEY), col('round_off', 'Round Off', MONEY), col('total', 'Total', MONEY),
            col('payment_modes', 'Payment'), col('pax', 'Pax', INT)]

    def build(request):
        qs = order_qs(request, force_status)
        if filt:
            qs = filt(qs)
        qs = qs.select_related('outlet', 'biller').prefetch_related('payments').order_by('-created_at')
        rows = [{
            'invoice_no': o.invoice_no, 'created_at': o.created_at, 'outlet': o.outlet.name, 'order_type': o.get_order_type_display(),
            'sub_order_type': o.sub_order_type, 'status': o.get_status_display(), 'biller': o.biller.name if o.biller else '',
            'customer_name': o.customer_name, 'customer_phone': o.customer_phone, 'locality': o.locality,
            'my_amount': o.my_amount, 'discount': o.discount, 'discount_reason': o.discount_reason, 'net': o.net_sales,
            'delivery_charge': o.delivery_charge, 'container_charge': o.container_charge, 'service_charge': o.service_charge,
            'total_tax': o.total_tax, 'round_off': o.round_off, 'total': o.total,
            'payment_modes': ', '.join(f'{p.mode}:{p.amount}' for p in o.payments.all()), 'pax': o.pax} for o in qs]
        return base, rows
    return build
