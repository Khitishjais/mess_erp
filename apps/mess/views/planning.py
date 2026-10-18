"""Read-only planning endpoints: weekly menu, forecast, plan, purchases, alerts, insights."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.permissions import IsPortalManagerOrReadOnly, IsPortalUser
from apps.common.request import body_int, get_int, resolve_day, resolve_outlet
from apps.inventory.models import PurchaseOrder, PurchaseOrderLine

from .. import services as svc
from ..models import MealPlan


@api_view(['GET'])
@permission_classes([IsPortalUser])
def weekly_menu(request):
    """7-day x 3-meal grid."""
    o = resolve_outlet(request)
    grid = {str(w): {m: [] for m in svc.MEALS} for w in range(7)}
    for p in MealPlan.objects.filter(outlet=o).select_related('recipe'):
        grid[str(p.weekday)][p.meal].append({'id': p.id, 'recipe': p.recipe_id, 'name': p.recipe.name, 'take_rate': p.take_rate})
    return Response({'outlet': o.id, 'grid': grid})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def forecast(request):
    o, d = resolve_outlet(request), resolve_day(request)
    return Response({'outlet': o.id, 'date': d.isoformat(), 'meals': [svc.forecast_headcount(o, d, m) for m in svc.MEALS],
                     'accuracy': svc.forecast_accuracy(o)})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def plan(request):
    """What to cook (per dish, per meal) and the raw material needed for the day."""
    o, d = resolve_outlet(request), resolve_day(request)
    return Response({'outlet': o.id, **svc.day_plan(o, d), 'staffing': svc.staffing(o, d)})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def purchases(request):
    o, d = resolve_outlet(request), resolve_day(request)
    return Response(svc.purchase_plan(o, d, get_int(request, 'days', 7, lo=1, hi=14)))


@api_view(['POST'])
@permission_classes([IsPortalManagerOrReadOnly])
def purchase_draft(request):
    """Turn the suggestion into a pending purchase order a manager can approve."""
    o, d = resolve_outlet(request), resolve_day(request)
    p = svc.purchase_plan(o, d, body_int(request, 'days', 7, lo=1, hi=14))
    rows = [r for r in p['rows'] if r['buy'] > 0]
    if not rows:
        return Response({'detail': 'Nothing to buy — stock covers the plan.'}, status=200)
    po = PurchaseOrder.objects.create(outlet=o, created_by=request.user, status='pending')
    PurchaseOrderLine.objects.bulk_create([PurchaseOrderLine(po=po, material_id=r['material_id'], qty=r['buy'], rate=r['rate']) for r in rows])
    return Response({'po': po.id, 'lines': len(rows), 'total': p['total']}, status=201)


@api_view(['GET'])
@permission_classes([IsPortalUser])
def alerts(request):
    return Response(svc.stock_alerts(resolve_outlet(request)))


@api_view(['GET'])
@permission_classes([IsPortalUser])
def wastage_report(request):
    return Response(svc.wastage_insights(resolve_outlet(request), get_int(request, 'days', 30, lo=1, hi=365)))


@api_view(['GET'])
@permission_classes([IsPortalUser])
def menu_eng(request):
    return Response(svc.menu_engineering(resolve_outlet(request)))
