from django.conf import settings
from django.db import models


class RawMaterial(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='materials')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True)
    purchase_unit = models.CharField(max_length=20)
    consumption_unit = models.CharField(max_length=20)
    conversion = models.DecimalField(max_digits=12, decimal_places=4, default=1)  # 1 purchase unit = N consumption units
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)   # Rs per purchase unit (estimate until real bills exist)
    shelf_life_days = models.PositiveIntegerField(default=30)                    # perishables are bought for fewer days
    yield_pct = models.DecimalField(max_digits=5, decimal_places=2, default=100)  # edible yield after cleaning/trimming
    pack_size = models.DecimalField(max_digits=8, decimal_places=3, default=1)   # purchase rounding step, in purchase units


class StockLedger(models.Model):
    """One row per outlet + material + day; the stock summary report sums these."""
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='stock_rows')
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    date = models.DateField()
    opening = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    purchase = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    excess = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    consumed = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    wastage = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    normal_loss = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    transfer = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    shortage = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    production = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    closing = models.DecimalField(max_digits=14, decimal_places=3, default=0)         # computed
    stock_closing = models.DecimalField(max_digits=14, decimal_places=3, default=0)   # physically counted

    class Meta:
        unique_together = ('outlet', 'material', 'date')


class ClosingStockLog(models.Model):
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE)
    date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('outlet', 'date')


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        RECEIVED = 'received', 'Received'

    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='purchase_orders')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=14, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class InvoiceImport(models.Model):
    """A supplier bill that was entered into stock from a photo or by hand. Kept so the same bill cannot be entered twice."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoice_imports')
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='invoice_imports')
    supplier = models.CharField(max_length=120, blank=True)
    invoice_no = models.CharField(max_length=60, blank=True)
    date = models.DateField()
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
