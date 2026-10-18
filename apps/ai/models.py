from django.db import models


class Feedback(models.Model):
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='feedback')
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    meal = models.CharField(max_length=10, blank=True)
    date = models.DateField(auto_now_add=True)
    sentiment = models.CharField(max_length=10, blank=True)   # filled by the AI layer
    topics = models.JSONField(default=list, blank=True)