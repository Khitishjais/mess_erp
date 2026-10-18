"""Save a bill sent by a POS terminal. Idempotent by client_uuid, so a retried sync never creates a duplicate."""
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from apps.accounts.models import User
from apps.catalog.models import DiningTable, Item

from ..models import Kot, Order, OrderItem, OrderTax, Payment
from .totals import CHARGE_FIELDS, D, compute_totals
from .validation import validate_bill


def _tenant_user(outlet, user_id):
    """The user with this id, only if they belong to the outlet's tenant (the owner or one of their staff)."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return User.objects.filter(pk=uid, is_active=True).filter(Q(pk=outlet.owner_id) | Q(owner_id=outlet.owner_id)).first()


def _order_fields(device, payload, user):
    """Everything on the Order row itself (totals come from the server, not from the POS)."""
    outlet = device.outlet
    table = DiningTable.objects.filter(pk=payload.get('table'), outlet=outlet).first() if payload.get('table') else None
    biller = _tenant_user(outlet, payload.get('biller')) or user      # never a user from another tenant
    fields = dict(
        invoice_no=payload['invoice_no'], device=device, order_type=payload.get('order_type', 'dine_in'),
        sub_order_type=payload.get('sub_order_type', ''), status=payload.get('status', 'running'), stage=payload.get('stage', 'preparing'),
        is_online=bool(payload.get('is_online')), table=table, biller=biller, pax=payload.get('pax') or 1,
        customer_name=payload.get('customer_name', ''), customer_phone=payload.get('customer_phone', ''),
        locality=payload.get('locality', ''), discount_reason=payload.get('discount_reason', ''),
        waived_off=D(payload.get('waived_off')), tip=D(payload.get('tip')), created_at=parse_datetime(payload['created_at']),
    )
    fields.update({k: D(payload.get(k)) for k in CHARGE_FIELDS})
    fields.update(compute_totals(payload))
    return fields


def _replace_children(order, payload, outlet):
    """Lines, taxes, payments and KOTs are replaced wholesale: the POS always sends the complete bill."""
    items, taxes = payload.get('items', []), payload.get('taxes', [])
    order.items.all().delete()
    order.taxes.all().delete()
    order.payments.all().delete()
    catalog = {i.id: i for i in Item.objects.filter(owner=outlet.owner, id__in=[x.get('item') for x in items if x.get('item')])}
    OrderItem.objects.bulk_create([OrderItem(
        order=order, item=catalog.get(i.get('item')), name=i['name'], category_name=i.get('category_name', ''),
        qty=D(i['qty']), price=D(i['price']), discount=D(i.get('discount')), tax_rate=D(i.get('tax_rate')),
        tax_amount=D(i.get('tax_amount')), is_cancelled=bool(i.get('is_cancelled'))) for i in items])
    OrderTax.objects.bulk_create([OrderTax(order=order, name=t['name'], rate=D(t['rate']), amount=D(t['amount'])) for t in taxes])
    Payment.objects.bulk_create([Payment(order=order, mode=p['mode'], amount=D(p['amount']), reference_no=p.get('reference_no', ''))
                                 for p in payload.get('payments', [])])
    for k in payload.get('kots', []):
        Kot.objects.update_or_create(order=order, number=k['number'], defaults={'lines': k.get('lines', []), 'status': k.get('status', 'new')})


@transaction.atomic
def upsert_order(device, payload, user):
    validate_bill(payload)
    outlet = device.outlet
    order = Order.objects.filter(client_uuid=payload['client_uuid']).first()
    if order and order.outlet_id != outlet.id:
        raise ValueError('Order belongs to another outlet.')
    fields = _order_fields(device, payload, user)
    if order:
        for k, v in fields.items():
            setattr(order, k, v)
        order.save()
    else:
        order = Order.objects.create(client_uuid=payload['client_uuid'], outlet=outlet, **fields)
    _replace_children(order, payload, outlet)
    return order
