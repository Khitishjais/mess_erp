"""POS terminal authentication: device token + staff PIN login."""
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response

from apps.accounts.models import Role, StaffOutletRole, User
from apps.accounts.views import tokens_for
from apps.common.throttle import PIN_LIMITER
from apps.outlets.models import Device

POS_ROLES = {Role.OWNER, Role.MANAGER, Role.CASHIER, Role.CAPTAIN, Role.KITCHEN}


def get_device(request):
    token = request.headers.get('X-Device-Token', '')
    d = Device.objects.select_related('outlet').filter(token=token, is_active=True).first() if token else None
    if not d:
        raise AuthenticationFailed('Unknown or deactivated device.')
    return d


class HasDevice(BasePermission):
    def has_permission(self, request, view):
        request.device = get_device(request)
        return True


def _pos_users(outlet):
    ids = StaffOutletRole.objects.filter(outlet=outlet, role__in=POS_ROLES).values_list('user_id', flat=True)
    return User.objects.filter(is_active=True).filter(id__in=list(ids)) | User.objects.filter(pk=outlet.owner_id)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def pos_login(request):
    """Staff PIN login on a mapped terminal."""
    dev = get_device(request)
    staff_id, pin = request.data.get('staff_id'), str(request.data.get('pin') or '')
    key = f'{dev.id}:{staff_id}'
    PIN_LIMITER.check(key)                       # locked out after 5 wrong PINs, even if the next one is right
    try:
        user = _pos_users(dev.outlet).filter(pk=int(staff_id)).first()
    except (TypeError, ValueError):
        user = None
    if not user or not user.check_pin(pin):
        PIN_LIMITER.fail(key)
        return Response({'detail': 'Wrong PIN.'}, status=status.HTTP_401_UNAUTHORIZED)
    PIN_LIMITER.reset(key)
    roles = ['owner'] if user.is_owner else list(StaffOutletRole.objects.filter(user=user, outlet=dev.outlet).values_list('role', flat=True))
    return Response({**tokens_for(user), 'user': {'id': user.id, 'name': user.name or user.email, 'roles': roles}})


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def pos_staff(request):
    """Names for the PIN-login picker (no secrets). PIN hashes are never exposed."""
    dev = get_device(request)
    return Response([{'id': u.id, 'name': u.name or u.email, 'is_owner': u.is_owner}
                     for u in _pos_users(dev.outlet).filter(pin_hash__gt='').distinct()])
