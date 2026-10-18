from django.conf import settings
from django.db import models


class FavoriteReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_reports')
    report_code = models.CharField(max_length=60)

    class Meta:
        unique_together = ('user', 'report_code')
