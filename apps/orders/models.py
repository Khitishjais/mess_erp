import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Type(models.TextChoices):
        DINE_IN = 'dine_in', 'Dine in'
        PICKUP = 'pickup', 'Pick up'
        DELIVERY = 'delivery', 'Delivery'

    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLIMENTARY = 'complimentary', 'Complimentary'
        SALES_RETURN = 'sales_return', 'Sales return'

    class Stage(models.TextChoices):
        PREPARING = 'preparing', 'In preparation'
        WAITING_PICKUP = 'waiting_pickup', 'Waiting for pickup'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for delivery'
        DONE = 'done', 'Done'

    # Client-generated id: makes POS offline sync idempotent.
    client_uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.PROTECT, related_name='orders')
    device = models.ForeignKey('outlets.Device', null=True, blank=True, on_delete=models.SET_NULL)
    invoice_no = models.CharField(max_length=30)
    order_type = models.CharField(max_length=12, choices=Type.choices, default=Type.DINE_IN)
    sub_order_type = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.RUNNING)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.PREPARING)
    is_online = models.BooleanField(default=False)
    table = models.ForeignKey('catalog.DiningTable', null=True, blank=True, on_delete=models.SET_NULL)
    biller = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    pax = models.PositiveIntegerField(default=1)
    customer_name = models.CharField(max_length=120, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    locality = models.CharField(max_length=120, blank=True)

    my_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)   # items total before discount
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=200, blank=True)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    container_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    round_off = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    waived_off = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)       # total sales

    created_at = models.DateTimeField()           # when the bill was created on the terminal
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('outlet', 'invoice_no')
        indexes = [
            models.Index(fields=['outlet', 'created_at']),
            models.Index(fields=['outlet', 'status']),
        ]

    @property
    def net_sales(self):
        return self.my_amount - self.discount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey('catalog.Item', null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200)        # snapshot at time of sale
    category_name = models.CharField(max_length=120, blank=True)
    qty = models.DecimalField(max_digits=8, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_cancelled = models.BooleanField(default=False)


class OrderTax(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='taxes')
    name = models.CharField(max_length=60)
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)


class Payment(models.Model):
    class Mode(models.TextChoices):
        CASH = 'cash', 'Cash'
        CARD = 'card', 'Card'
        UPI = 'upi', 'UPI'
        DUE = 'due', 'Due payment'
        WALLET = 'wallet', 'Wallet'
        ONLINE = 'online', 'Online'
        OTHER = 'other', 'Other'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    mode = models.CharField(max_length=10, choices=Mode.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_no = models.CharField(max_length=60, blank=True)


class Kot(models.Model):
    """Kitchen order ticket sent from POS."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='kots')
    number = models.PositiveIntegerField()
    lines = models.JSONField(default=list)  # [{name, qty, note}]
    status = models.CharField(max_length=12, default='new')  # new|preparing|ready|served
    created_at = models.DateTimeField(auto_now_add=True)


class Shift(models.Model):
    device = models.ForeignKey('outlets.Device', on_delete=models.CASCADE, related_name='shifts')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
