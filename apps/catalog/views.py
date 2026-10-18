from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.common.mixins import OutletScopedMixin, OwnerScopedMixin
from apps.common.permissions import IsPortalManagerOrReadOnly
from apps.common.request import body_int, get_id, get_int
from apps.common.scope import outlets_for

from .models import Addon, Category, DiningTable, Item, ItemOutletStatus, Tag, Tax
from .serializers import (
    AddonSerializer,
    CategorySerializer,
    DiningTableSerializer,
    ItemOutletStatusSerializer,
    ItemSerializer,
    TagSerializer,
    TaxSerializer,
)


class _Base(OwnerScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsPortalManagerOrReadOnly]


class TaxViewSet(_Base):
    queryset = Tax.objects.order_by('name', 'id')
    serializer_class = TaxSerializer


class CategoryViewSet(_Base):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('This category still has items. Move or delete them first.')


class TagViewSet(_Base):
    queryset = Tag.objects.order_by('name', 'id')
    serializer_class = TagSerializer


class AddonViewSet(_Base):
    queryset = Addon.objects.order_by('name', 'id')
    serializer_class = AddonSerializer


class ItemViewSet(_Base):
    queryset = Item.objects.select_related('category', 'tax').prefetch_related('tags')
    serializer_class = ItemSerializer
    filterset_fields = ['category', 'is_active']

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('search')
        return qs.filter(name__icontains=q) if q else qs


class DiningTableViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = DiningTable.objects.order_by('outlet__name', 'name', 'id')
    serializer_class = DiningTableSerializer
    permission_classes = [IsPortalManagerOrReadOnly]
    filterset_fields = ['outlet']


class ItemStatusViewSet(OutletScopedMixin, viewsets.ReadOnlyModelViewSet):
    """Item availability per outlet (Out-of-stock tracking) + toggle."""
    queryset = ItemOutletStatus.objects.select_related('item__category', 'outlet').order_by('-changed_at')
    serializer_class = ItemOutletStatusSerializer
    permission_classes = [IsPortalManagerOrReadOnly]
    filterset_fields = ['outlet', 'is_available']

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if get_id(self.request, 'category'):
            qs = qs.filter(item__category_id=get_id(self.request, 'category'))
        if p.get('search'):
            qs = qs.filter(item__name__icontains=p['search'])
        mins = get_int(self.request, 'off_for_minutes', None, lo=0)
        if mins is not None:
            qs = qs.filter(is_available=False, changed_at__lte=timezone.now() - timezone.timedelta(minutes=mins))
        return qs

    @action(detail=False, methods=['post'])
    def set(self, request):
        """Mark an item in/out of stock at an outlet; logged for tracking."""
        outlet = outlets_for(request.user).filter(pk=body_int(request, 'outlet')).first()
        item = Item.objects.filter(pk=body_int(request, 'item'), owner=request.user.tenant_owner).first()
        if not outlet or not item:
            raise ValidationError('Invalid outlet or item.')
        raw = request.data.get('is_available')
        if raw is None or (isinstance(raw, str) and raw.lower() not in ('true', 'false')) or not isinstance(raw, (bool, str)):
            raise ValidationError('is_available (true/false) is required.')
        avail = raw if isinstance(raw, bool) else raw.lower() == 'true'
        row, _ = ItemOutletStatus.objects.update_or_create(item=item, outlet=outlet, defaults={'is_available': avail})
        Item.objects.filter(pk=item.pk).update(updated_at=timezone.now())      # so terminals pull the new availability on their next sync
        AuditLog.objects.create(owner=request.user.tenant_owner, outlet=outlet, actor=request.user, kind='item_status',
                                message=f'{item.name} marked {"in" if avail else "out of"} stock')
        return Response(ItemOutletStatusSerializer(row).data)