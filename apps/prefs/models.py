from django.conf import settings
from django.db import models


class Setting(models.Model):
    """One configured value. outlet=NULL is the business-wide default; a row with an outlet overrides it for that outlet only."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prefs')
    outlet = models.ForeignKey('outlets.Outlet', null=True, blank=True, on_delete=models.CASCADE, related_name='prefs')
    key = models.CharField(max_length=60)
    value = models.JSONField()
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'outlet', 'key'], name='one_value_per_scope', nulls_distinct=False)]
