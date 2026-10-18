"""Helpers shared by the automation jobs."""
import json

from django.core.serializers.json import DjangoJSONEncoder


def _clean(obj):
    """Make a payload JSON-safe (Decimal/date -> plain JSON)."""
    return json.loads(json.dumps(obj, cls=DjangoJSONEncoder))


def mess_outlets(only=None):
    from apps.outlets.models import Outlet
    qs = Outlet.objects.filter(is_active=True, meal_plan__isnull=False).distinct()
    return qs.filter(pk=only) if only else qs
