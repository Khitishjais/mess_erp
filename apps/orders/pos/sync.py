"""Idempotent push of bills from the POS outbox."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..services import upsert_order
from .auth import HasDevice

MAX_BATCH = 200


def _uuid_of(payload):
    return payload.get('client_uuid') if isinstance(payload, dict) else None


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasDevice])
def sync_orders(request):
    """Batch push of bills. Safe to retry: each order is upserted by client_uuid; one bad bill never blocks the others."""
    orders = request.data.get('orders') if isinstance(request.data, dict) else None
    if not isinstance(orders, list):
        raise ValidationError({'orders': 'Send a list of bills as "orders".'})
    if len(orders) > MAX_BATCH:
        raise ValidationError({'orders': f'At most {MAX_BATCH} bills per request.'})
    results = []
    for payload in orders:
        try:
            order = upsert_order(request.device, payload, request.user)
            results.append({'client_uuid': str(order.client_uuid), 'ok': True, 'id': order.id})
        except Exception as e:      # reported per bill; the POS keeps it in its outbox and shows the reason
            results.append({'client_uuid': _uuid_of(payload), 'ok': False, 'error': str(e)})
    return Response({'results': results})
