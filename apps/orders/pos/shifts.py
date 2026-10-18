"""Shift open / close."""
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.request import body_decimal, body_str

from ..models import Order, Payment, Shift
from .auth import HasDevice


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasDevice])
def shift_open(request):
    s = Shift.objects.create(device=request.device, cashier=request.user,
                             opened_at=parse_datetime(body_str(request, 'opened_at')) or timezone.now(),
                             opening_cash=body_decimal(request, 'opening_cash', 0, minimum=0))
    return Response({'id': s.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated, HasDevice])
def shift_close(request, pk):
    s = Shift.objects.filter(pk=pk, device=request.device).first()
    if not s:
        return Response({'detail': 'Shift not found.'}, status=404)
    s.closed_at = timezone.now()
    s.closing_cash = body_decimal(request, 'closing_cash', None, minimum=0)
    s.save()
    orders = Order.objects.filter(device=request.device, created_at__gte=s.opened_at, status='success')
    by_mode = Payment.objects.filter(order__in=orders).values('mode').annotate(total=Sum('amount'))
    return Response({'id': s.id, 'bills': orders.count(), 'by_mode': list(by_mode)})
