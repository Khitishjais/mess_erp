from datetime import date
from decimal import Decimal

from rest_framework import serializers

from apps.common.scope import outlets_for

from .models import (
    Attendance,
    MealPlan,
    MessSetting,
    Recipe,
    RecipeLine,
    SpecialDay,
    WastageLog,
)
from .services import material_cost

WEEKDAY_KEYS = {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}
MEAL_KEYS = {'breakfast', 'lunch', 'dinner'}


class OutletChecked:
    def validate_outlet(self, outlet):
        if not outlets_for(self.context['request'].user).filter(pk=outlet.pk).exists():
            raise serializers.ValidationError('Outlet not accessible.')
        return outlet


def not_in_future(value):
    if value > date.today():
        raise serializers.ValidationError('The date cannot be in the future.')
    return value


class SettingSerializer(OutletChecked, serializers.ModelSerializer):
    class Meta:
        model = MessSetting
        fields = ['id', 'outlet', 'members', 'buffer_pct', 'attendance', 'staff_plates_per_cook', 'staff_plates_per_server']
        extra_kwargs = {
            'members': {'min_value': 1}, 'buffer_pct': {'min_value': 0, 'max_value': 100},
            'staff_plates_per_cook': {'min_value': 1}, 'staff_plates_per_server': {'min_value': 1},
        }

    def validate_attendance(self, value):
        """{"mon": {"lunch": 60}} : weekday keys, meal keys, whole-or-decimal percentages 0-100."""
        if not isinstance(value, dict):
            raise serializers.ValidationError('Use {"mon": {"lunch": 60}}.')
        for day, meals in value.items():
            if day not in WEEKDAY_KEYS or not isinstance(meals, dict):
                raise serializers.ValidationError(f'"{day}" is not a weekday (use mon..sun with a meal map).')
            for meal, pct in meals.items():
                if meal not in MEAL_KEYS:
                    raise serializers.ValidationError(f'"{meal}" is not a meal (breakfast, lunch, dinner).')
                if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not 0 <= pct <= 100:
                    raise serializers.ValidationError('Percentages must be numbers from 0 to 100.')
        return value


class SpecialDaySerializer(OutletChecked, serializers.ModelSerializer):
    class Meta:
        model = SpecialDay
        fields = ['id', 'outlet', 'date', 'factor', 'note']
        extra_kwargs = {'factor': {'min_value': 0, 'max_value': 5}}


class LineSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    unit = serializers.CharField(source='material.consumption_unit', read_only=True)

    class Meta:
        model = RecipeLine
        fields = ['id', 'material', 'material_name', 'unit', 'qty']
        extra_kwargs = {'qty': {'min_value': Decimal('0.01')}}


class RecipeSerializer(serializers.ModelSerializer):
    lines = LineSerializer(many=True)
    cost_per_plate = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'take_rate', 'popularity', 'is_estimate', 'lines', 'cost_per_plate']
        extra_kwargs = {'take_rate': {'min_value': 0, 'max_value': 1}, 'popularity': {'min_value': Decimal('0.5'), 'max_value': Decimal('1.5')}}

    def get_cost_per_plate(self, r):
        return sum(material_cost(l.material, l.qty / (l.material.yield_pct / 100)) for l in r.lines.all())

    def _owner(self):
        return self.context['request'].user.tenant_owner

    def validate_name(self, name):
        clash = Recipe.objects.filter(owner=self._owner(), name=name).exclude(pk=getattr(self.instance, 'pk', None))
        if clash.exists():
            raise serializers.ValidationError('You already have a recipe with this name.')
        return name

    def validate_lines(self, lines):
        for line in lines:
            if line['material'].owner_id != self._owner().id:
                raise serializers.ValidationError('Material not in your account.')
        return lines

    def _save_lines(self, recipe, lines):
        recipe.lines.all().delete()
        RecipeLine.objects.bulk_create([RecipeLine(recipe=recipe, **line) for line in lines])

    def create(self, data):
        lines = data.pop('lines', [])
        data.pop('owner', None)           # OwnerScopedMixin also passes owner; the tenant always wins
        r = Recipe.objects.create(owner=self._owner(), **data)
        self._save_lines(r, lines)
        return r

    def update(self, r, data):
        lines = data.pop('lines', None)
        for k, v in data.items():
            setattr(r, k, v)
        r.save()
        if lines is not None:
            self._save_lines(r, lines)
        return r


class MealPlanSerializer(OutletChecked, serializers.ModelSerializer):
    recipe_name = serializers.CharField(source='recipe.name', read_only=True)

    class Meta:
        model = MealPlan
        fields = ['id', 'outlet', 'weekday', 'meal', 'recipe', 'recipe_name', 'take_rate']
        extra_kwargs = {'take_rate': {'min_value': 0, 'max_value': 1}}

    def validate_recipe(self, r):
        if r.owner_id != self.context['request'].user.tenant_owner.id:
            raise serializers.ValidationError('Recipe not in your account.')
        return r


class AttendanceSerializer(OutletChecked, serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['id', 'outlet', 'date', 'meal', 'actual', 'prepared_portions', 'leftover_portions']

    def validate_date(self, value):
        return not_in_future(value)

    def validate(self, d):
        prepared = d.get('prepared_portions', getattr(self.instance, 'prepared_portions', None))
        left = d.get('leftover_portions', getattr(self.instance, 'leftover_portions', None))
        if prepared is not None and left is not None and left > prepared:
            raise serializers.ValidationError('Left-over portions cannot be more than the portions cooked.')
        return d


class WastageSerializer(OutletChecked, serializers.ModelSerializer):
    recipe_name = serializers.CharField(source='recipe.name', read_only=True, default='')
    material_name = serializers.CharField(source='material.name', read_only=True, default='')

    class Meta:
        model = WastageLog
        fields = ['id', 'outlet', 'date', 'meal', 'recipe', 'recipe_name', 'material', 'material_name', 'qty', 'reason', 'cost']
        read_only_fields = ['cost']
        extra_kwargs = {'qty': {'min_value': Decimal('0.001')}}

    def _mine(self, obj):
        if obj is not None and obj.owner_id != self.context['request'].user.tenant_owner.id:
            raise serializers.ValidationError('Not found in your account.')
        return obj

    def validate_date(self, value):
        return not_in_future(value)

    def validate_recipe(self, r):
        return self._mine(r)

    def validate_material(self, m):
        return self._mine(m)

    def validate(self, d):
        recipe = d.get('recipe', getattr(self.instance, 'recipe', None))
        material = d.get('material', getattr(self.instance, 'material', None))
        if not recipe and not material:
            raise serializers.ValidationError('Choose a dish or a raw material.')
        return d
