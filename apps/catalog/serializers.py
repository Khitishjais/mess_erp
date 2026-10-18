from rest_framework import serializers

from .models import Addon, Category, DiningTable, Item, ItemOutletStatus, Tag, Tax


class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ['id', 'name', 'rate']
        extra_kwargs = {'rate': {'min_value': 0, 'max_value': 100}}      # a percentage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'sort_order']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    tax_rate = serializers.DecimalField(source='tax.rate', max_digits=5, decimal_places=2, read_only=True, default=0)

    class Meta:
        model = Item
        fields = ['id', 'name', 'category', 'category_name', 'price', 'tax', 'tax_rate', 'tags',
                  'is_veg', 'is_active', 'updated_at']
        extra_kwargs = {'price': {'min_value': 0}}

    def _own(self, obj):
        owner = self.context['request'].user.tenant_owner
        if obj is not None and obj.owner_id != owner.id:
            raise serializers.ValidationError('Not found in your account.')
        return obj

    def validate_category(self, v):
        return self._own(v)

    def validate_tax(self, v):
        return self._own(v)

    def validate_tags(self, tags):
        for t in tags:
            self._own(t)
        return tags


class AddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Addon
        fields = ['id', 'name', 'price', 'is_active']
        extra_kwargs = {'price': {'min_value': 0}}


class DiningTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiningTable
        fields = ['id', 'outlet', 'name', 'section', 'seats']

    def validate_outlet(self, outlet):
        if outlet.owner_id != self.context['request'].user.tenant_owner.id:
            raise serializers.ValidationError('Outlet does not belong to your account.')
        return outlet


class ItemOutletStatusSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    category_name = serializers.CharField(source='item.category.name', read_only=True)
    outlet_name = serializers.CharField(source='outlet.name', read_only=True)

    class Meta:
        model = ItemOutletStatus
        fields = ['id', 'item', 'item_name', 'category_name', 'outlet', 'outlet_name', 'is_available', 'changed_at']