from rest_framework import serializers

from .models import Device, Outlet, Zone


class OutletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outlet
        fields = ['id', 'code', 'name', 'brand', 'kind', 'is_active', 'gstin', 'address']

    def validate_code(self, code):
        owner = self.context['request'].user.tenant_owner
        clash = Outlet.objects.filter(owner=owner, code=code).exclude(pk=getattr(self.instance, 'pk', None))
        if clash.exists():
            raise serializers.ValidationError('You already have an outlet with this code.')
        return code


class ZoneSerializer(serializers.ModelSerializer):
    outlet_ids = serializers.PrimaryKeyRelatedField(
        source='outlets', many=True, queryset=Outlet.objects.all(), required=False)

    class Meta:
        model = Zone
        fields = ['id', 'name', 'outlet_ids']

    def validate_name(self, name):
        owner = self.context['request'].user.tenant_owner
        if Zone.objects.filter(owner=owner, name=name).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise serializers.ValidationError('You already have a zone with this name.')
        return name

    def validate_outlet_ids(self, outlets):
        owner = self.context['request'].user.tenant_owner
        if any(o.owner_id != owner.id for o in outlets):
            raise serializers.ValidationError('Outlet does not belong to your account.')
        return outlets


class DeviceSerializer(serializers.ModelSerializer):
    outlet_name = serializers.CharField(source='outlet.name', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ['id', 'outlet', 'outlet_name', 'name', 'invoice_prefix', 'activation_code',
                  'activated_at', 'is_active', 'status']
        read_only_fields = ['activation_code', 'activated_at']

    def get_status(self, d):
        return 'active' if d.activated_at else 'pending'

    def validate_outlet(self, outlet):
        if outlet.owner_id != self.context['request'].user.tenant_owner.id:
            raise serializers.ValidationError('Outlet does not belong to your account.')
        return outlet