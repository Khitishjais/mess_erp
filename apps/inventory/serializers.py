from decimal import Decimal

from rest_framework import serializers

from .models import PurchaseOrder, PurchaseOrderLine, RawMaterial, StockLedger


class RawMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawMaterial
        fields = ['id', 'name', 'category', 'purchase_unit', 'consumption_unit', 'conversion', 'unit_cost', 'shelf_life_days', 'yield_pct', 'pack_size']
        extra_kwargs = {                      # a zero here would divide by zero in every plan
            'conversion': {'min_value': Decimal('0.0001')}, 'yield_pct': {'min_value': 1, 'max_value': 100},
            'unit_cost': {'min_value': 0}, 'pack_size': {'min_value': Decimal('0.001')}, 'shelf_life_days': {'min_value': 1},
        }


class StockLedgerSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)

    class Meta:
        model = StockLedger
        fields = ['id', 'outlet', 'material', 'material_name', 'date', 'opening', 'purchase', 'excess', 'consumed',
                  'wastage', 'normal_loss', 'transfer', 'shortage', 'production', 'closing', 'stock_closing']
        read_only_fields = ['closing']
        extra_kwargs = {f: {'min_value': 0} for f in ('opening', 'purchase', 'excess', 'consumed', 'wastage', 'normal_loss', 'transfer',
                                                       'shortage', 'production', 'stock_closing')}

    def validate(self, d):
        user = self.context['request'].user
        from apps.common.scope import outlets_for
        outlet = d.get('outlet') or self.instance.outlet            # PATCH may omit them
        material = d.get('material') or self.instance.material
        if not outlets_for(user).filter(pk=outlet.pk).exists():
            raise serializers.ValidationError('Outlet not accessible.')
        if material.owner_id != user.tenant_owner.id:
            raise serializers.ValidationError('Material not in your account.')
        return d


class POLineSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = ['id', 'material', 'material_name', 'qty', 'rate']
        extra_kwargs = {'qty': {'min_value': Decimal('0.001')}, 'rate': {'min_value': 0}}


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = POLineSerializer(many=True, allow_empty=False)
    outlet_name = serializers.CharField(source='outlet.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'outlet', 'outlet_name', 'status', 'created_at', 'lines']
        read_only_fields = ['status']

    def validate_outlet(self, o):
        from apps.common.scope import outlets_for
        if not outlets_for(self.context['request'].user).filter(pk=o.pk).exists():
            raise serializers.ValidationError('Outlet not accessible.')
        return o

    def validate_lines(self, lines):
        owner = self.context['request'].user.tenant_owner
        for line in lines:
            if line['material'].owner_id != owner.id:
                raise serializers.ValidationError('Material not in your account.')
        return lines

    def create(self, data):
        lines = data.pop('lines')
        po = PurchaseOrder.objects.create(created_by=self.context['request'].user, **data)
        PurchaseOrderLine.objects.bulk_create([PurchaseOrderLine(po=po, **l) for l in lines])
        return po