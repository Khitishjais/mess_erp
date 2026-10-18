import csv

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.common.permissions import IsPortalUser
from apps.common.request import get_int

from . import registry
from .models import FavoriteReport


@api_view(['GET'])
@permission_classes([IsPortalUser])
def report_list(request):
    favs = set(FavoriteReport.objects.filter(user=request.user).values_list('report_code', flat=True))
    return Response([{'code': r['code'], 'title': r['title'], 'description': r['description'], 'favorite': r['code'] in favs}
                     for r in registry.REPORTS.values()])


@api_view(['POST'])
@permission_classes([IsPortalUser])
def toggle_favorite(request, code):
    if code not in registry.REPORTS:
        return Response({'detail': 'Unknown report.'}, status=404)
    obj, created = FavoriteReport.objects.get_or_create(user=request.user, report_code=code)
    if not created:
        obj.delete()
    return Response({'favorite': created})


def _run(request, code):
    rep = registry.REPORTS[code]
    cols, rows = rep['build'](request)
    return rep, cols, rows


@api_view(['GET'])
@permission_classes([IsPortalUser])
def report_data(request, code):
    if code not in registry.REPORTS:
        return Response({'detail': 'Unknown report.'}, status=404)
    rep, cols, rows = _run(request, code)
    if request.query_params.get('export') == 'csv':
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="{code}.csv"'
        w = csv.writer(resp)
        w.writerow([c['label'] for c in cols])
        for r in rows:
            w.writerow([r.get(c['key'], '') for c in cols])
        return resp
    page = get_int(request, 'page', 1, lo=1)
    size = get_int(request, 'page_size', 100, lo=1, hi=500)
    return Response({
        'code': code, 'title': rep['title'], 'columns': cols, 'totals': registry.totals(cols, rows),
        'count': len(rows), 'page': page, 'rows': rows[(page - 1) * size: page * size],
    })