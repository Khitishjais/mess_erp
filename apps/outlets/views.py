import secrets

from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.mixins import OutletScopedMixin, OwnerScopedMixin
from apps.common.permissions import IsPortalManagerOrReadOnly
from apps.common.request import body_int, body_str
from apps.common.scope import outlets_for

from .models import Device, Outlet, Zone
from .serializers import DeviceSerializer, OutletSerializer, ZoneSerializer


class OutletViewSet(viewsets.ModelViewSet):
    queryset = Outlet.objects.all()
    serializer_class = OutletSerializer
    permission_classes = [IsPortalManagerOrReadOnly]

    def get_queryset(self):
        return outlets_for(self.request.user)

    def perform_create(self, serializer):
        # Only the owner may create outlets.
        if not self.request.user.is_owner:
            raise PermissionDenied('Only the owner can create outlets.')
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        if not self.request.user.is_owner:
            raise PermissionDenied('Only the owner can delete outlets.')
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('This outlet already has bills, so it cannot be deleted. Mark it inactive instead.')


class ZoneViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = Zone.objects.prefetch_related('outlets').order_by('name')
    serializer_class = ZoneSerializer
    permission_classes = [IsPortalManagerOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('search')
        return qs.filter(name__icontains=q) if q else qs


class DeviceViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = Device.objects.select_related('outlet').order_by('outlet__name', 'invoice_prefix')
    serializer_class = DeviceSerializer
    permission_classes = [IsPortalManagerOrReadOnly]
    filterset_fields = ['outlet']

    @action(detail=True, methods=['post'], url_path='code')
    def code(self, request, pk=None):
        """'Get Code': issue a fresh one-time activation code (invalidates the old token)."""
        d = self.get_object()
        d.activation_code = Device.new_code()
        d.token = None
        d.activated_at = None
        d.save()
        return Response({'activation_code': d.activation_code})

    @action(detail=False, methods=['post'], url_path='quick-add')
    def quick_add(self, request):
        """'Quick Add': create a terminal for an outlet and return its code."""
        outlet_id = body_int(request, 'outlet')
        ser = self.get_serializer(data={
            'outlet': outlet_id,
            'name': body_str(request, 'name'),
            'invoice_prefix': body_str(request, 'invoice_prefix') or f'T{Device.objects.filter(outlet_id=outlet_id).count() + 1}',
        })
        ser.is_valid(raise_exception=True)
        d = ser.save(activation_code=Device.new_code())
        return Response(DeviceSerializer(d).data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def activate_device(request):
    """POS terminal first run: exchange the code for a long-lived device token."""
    code = body_str(request, 'code').strip().upper()
    d = Device.objects.select_related('outlet').filter(activation_code=code, is_active=True).first()
    if not d:
        return Response({'detail': 'Invalid or used code.'}, status=400)
    d.token = secrets.token_hex(24)
    d.activation_code = None
    d.activated_at = timezone.now()
    d.save()
    return Response({'device_token': d.token, 'device_id': d.id, 'invoice_prefix': d.invoice_prefix,
                     'outlet': {'id': d.outlet_id, 'code': d.outlet.code, 'name': d.outlet.name, 'gstin': d.outlet.gstin, 'address': d.outlet.address}})