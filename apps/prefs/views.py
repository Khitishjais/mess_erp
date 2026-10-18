from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.common.permissions import IsPortalUser
from apps.common.scope import can_manage, outlets_for

from . import service


def _outlet(user, raw):
    """The outlet the caller may use, or None for "all outlets / business-wide". Anything else is an error."""
    if raw in (None, ''):
        return None
    if isinstance(raw, bool) or not str(raw).isdigit():
        raise ValidationError('Outlet not found.')
    outlet = outlets_for(user).filter(pk=int(raw)).first()
    if not outlet:
        raise ValidationError('Outlet not found.')
    return outlet


@api_view(['GET', 'PUT'])
@permission_classes([IsPortalUser])
def settings_view(request):
    """GET ?outlet=<id>  -> settings for that outlet (no outlet = business-wide defaults).  PUT {outlet?, values:{key: value|null}} (owner/manager)."""
    owner = request.user.tenant_owner
    if request.method == 'GET':
        outlet = _outlet(request.user, request.query_params.get('outlet'))
        return Response({'outlet': outlet.id if outlet else None, 'groups': service.describe(owner, outlet)})
    if not can_manage(request.user):
        raise PermissionDenied('Only the owner or a manager can change settings.')
    body = request.data if isinstance(request.data, dict) else {}
    outlet = _outlet(request.user, body.get('outlet'))
    warnings = service.save(request.user, outlet, body.get('values'))
    return Response({'saved': True, 'warnings': warnings, 'groups': service.describe(owner, outlet)})
