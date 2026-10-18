import secrets

from django.conf import settings
from django.db import models


class Outlet(models.Model):
    class Kind(models.TextChoices):
        RESTAURANT = 'restaurant', 'Restaurant'
        CENTRAL_KITCHEN = 'central_kitchen', 'Central kitchen'
        MESS = 'mess', 'Mess / canteen'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='outlets')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=120, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.RESTAURANT)
    is_active = models.BooleanField(default=True)
    gstin = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'code')
        ordering = ['name']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Zone(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=120)
    outlets = models.ManyToManyField(Outlet, related_name='zones', blank=True)

    class Meta:
        unique_together = ('owner', 'name')


class Device(models.Model):
    """A billing terminal mapped to an outlet using a one-time activation code."""
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=80, blank=True)
    invoice_prefix = models.CharField(max_length=10)  # e.g. T1 -> T1-0001 offline-safe numbering
    activation_code = models.CharField(max_length=12, unique=True, null=True, blank=True)
    token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('outlet', 'invoice_prefix')

    @staticmethod
    def new_code():
        return secrets.token_hex(3).upper()
