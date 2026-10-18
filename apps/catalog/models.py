from django.conf import settings
from django.db import models


class Tax(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='taxes')
    name = models.CharField(max_length=60)
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # percent


class Category(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=120)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']


class Tag(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=60)


class Item(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='items')
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.ForeignKey(Tax, null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    is_veg = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)  # drives POS delta sync

    class Meta:
        ordering = ['name']


class ItemOutletStatus(models.Model):
    """Per-outlet availability (out-of-stock tracking)."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='outlet_status')
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item', 'outlet')


class Addon(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)


class DiningTable(models.Model):
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='tables')
    name = models.CharField(max_length=40)
    section = models.CharField(max_length=60, blank=True)
    seats = models.PositiveIntegerField(default=2)

    class Meta:
        unique_together = ('outlet', 'name')
