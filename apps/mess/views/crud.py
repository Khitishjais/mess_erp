"""CRUD endpoints: settings, special days, recipes, meal plan, attendance, wastage."""
from decimal import Decimal

from rest_framework import viewsets

from apps.common.mixins import OutletScopedMixin, OwnerScopedMixin
from apps.common.permissions import IsPortalManagerOrReadOnly, IsPortalUser
from apps.common.scope import outlets_for

from .. import automation
from .. import services as svc
from ..models import Attendance, MealPlan, MessSetting, Recipe, SpecialDay, WastageLog
from ..serializers import (
    AttendanceSerializer,
    MealPlanSerializer,
    RecipeSerializer,
    SettingSerializer,
    SpecialDaySerializer,
    WastageSerializer,
)


class SettingViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = MessSetting.objects.order_by('outlet__name', 'id')
    serializer_class = SettingSerializer
    permission_classes = [IsPortalManagerOrReadOnly]
    filterset_fields = ['outlet']

    def list(self, request, *a, **kw):
        for o in outlets_for(request.user):          # every outlet gets a row with the estimate defaults
            svc.setting_for(o)
        return super().list(request, *a, **kw)


class SpecialDayViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = SpecialDay.objects.order_by('-date')
    serializer_class = SpecialDaySerializer
    permission_classes = [IsPortalManagerOrReadOnly]
    filterset_fields = ['outlet']


class RecipeViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related('lines__material')
    serializer_class = RecipeSerializer
    permission_classes = [IsPortalManagerOrReadOnly]


class MealPlanViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = MealPlan.objects.select_related('recipe').order_by('weekday', 'meal')
    serializer_class = MealPlanSerializer
    permission_classes = [IsPortalManagerOrReadOnly]
    filterset_fields = ['outlet', 'weekday', 'meal']


class AttendanceViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = Attendance.objects.order_by('-date')
    serializer_class = AttendanceSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['outlet', 'date', 'meal']

    # Entering attendance immediately deducts that meal's ingredients from stock (automation #3).
    def perform_create(self, ser):
        a = ser.save()
        automation.apply_consumption(a.outlet, a.date, a.meal)

    def perform_update(self, ser):
        a = ser.save()
        automation.apply_consumption(a.outlet, a.date, a.meal)

    def perform_destroy(self, inst):
        o, d, m = inst.outlet, inst.date, inst.meal
        inst.delete()
        automation.apply_consumption(o, d, m)       # no attendance any more -> puts the stock back


class WastageViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = WastageLog.objects.select_related('recipe', 'material').order_by('-date', '-id')
    serializer_class = WastageSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['outlet', 'date', 'reason', 'meal']

    @staticmethod
    def _cost(d):
        """Raw material: qty (in its consumption unit) x unit cost. Dish: portions x the dish's cost per plate."""
        if d.get('material'):
            return svc.material_cost(d['material'], d['qty'])
        return (svc.recipe_plate_cost(d['recipe']) * d['qty']).quantize(Decimal('0.01'))

    def perform_create(self, ser):
        ser.save(cost=self._cost(ser.validated_data), created_by=self.request.user)

    def perform_update(self, ser):
        merged = {'material': ser.instance.material, 'recipe': ser.instance.recipe, 'qty': ser.instance.qty, **ser.validated_data}
        ser.save(cost=self._cost(merged))              # editing the quantity re-prices the entry
