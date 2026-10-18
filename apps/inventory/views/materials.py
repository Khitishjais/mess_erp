"""Raw material CRUD."""
from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.common.mixins import OwnerScopedMixin
from apps.common.permissions import IsPortalUser

from ..models import RawMaterial
from ..serializers import RawMaterialSerializer


class RawMaterialViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = RawMaterial.objects.order_by('name')
    serializer_class = RawMaterialSerializer
    permission_classes = [IsPortalUser]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('This material is used in recipes or purchase orders, so it cannot be deleted.')
