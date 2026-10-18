from django.conf import settings
from django.db import models


class Notification(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(max_length=120, blank=True, db_index=True)   # de-duplicates automatic reminders


class AuditLog(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audit_logs')
    outlet = models.ForeignKey('outlets.Outlet', null=True, blank=True, on_delete=models.SET_NULL)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    kind = models.CharField(max_length=40)   # store_status | item_status | menu_trigger | ...
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
