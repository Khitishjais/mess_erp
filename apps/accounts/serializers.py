from rest_framework import serializers

from apps.common.scope import owner_of
from apps.outlets.models import Outlet

from .models import Role, StaffOutletRole, User


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    outlets = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'mobile', 'is_owner', 'is_2fa_enabled', 'roles', 'outlets']

    def get_roles(self, u):
        from apps.common.scope import roles_for
        return sorted(roles_for(u))

    def get_outlets(self, u):
        from apps.common.scope import outlets_for
        return [{'id': o.id, 'code': o.code, 'name': o.name, 'kind': o.kind} for o in outlets_for(u)]


class OutletRoleSerializer(serializers.Serializer):
    outlet = serializers.PrimaryKeyRelatedField(queryset=Outlet.objects.all())
    role = serializers.ChoiceField(choices=[r for r in Role.choices if r[0] != Role.OWNER])


class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pin = serializers.RegexField(r'^\d{4,8}$', write_only=True, required=False, allow_blank=True,
                                 error_messages={'invalid': 'PIN must be 4 to 8 digits.'})
    outlet_roles = OutletRoleSerializer(many=True, required=False)
    has_pin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'mobile', 'is_active', 'password', 'pin', 'has_pin', 'outlet_roles']

    def get_has_pin(self, u):
        return bool(u.pin_hash)

    def to_representation(self, u):
        data = super().to_representation(u)
        data['outlet_roles'] = [
            {'outlet': r.outlet_id, 'outlet_name': r.outlet.name, 'role': r.role}
            for r in u.outlet_roles.select_related('outlet')
        ]
        return data

    def validate_outlet_roles(self, roles):
        pairs = [(r['outlet'].pk, r['role']) for r in roles]
        if len(pairs) != len(set(pairs)):
            raise serializers.ValidationError('The same outlet and role is listed more than once.')
        return roles

    def _check_outlets(self, roles):
        owner = owner_of(self.context['request'].user)
        for r in roles:
            if r['outlet'].owner_id != owner.id:
                raise serializers.ValidationError('Outlet does not belong to your account.')

    def _save_roles(self, user, roles):
        user.outlet_roles.all().delete()
        StaffOutletRole.objects.bulk_create(
            [StaffOutletRole(user=user, outlet=r['outlet'], role=r['role']) for r in roles])

    def create(self, data):
        roles = data.pop('outlet_roles', [])
        self._check_outlets(roles)
        pwd, pin = data.pop('password', ''), data.pop('pin', '')
        owner = owner_of(self.context['request'].user)
        user = User(owner=owner, is_owner=False, **data)
        user.set_password(pwd) if pwd else user.set_unusable_password()
        if pin:
            user.set_pin(pin)
        user.save()
        self._save_roles(user, roles)
        return user

    def update(self, user, data):
        roles = data.pop('outlet_roles', None)
        pwd, pin = data.pop('password', ''), data.pop('pin', '')
        for k, v in data.items():
            setattr(user, k, v)
        if pwd:
            user.set_password(pwd)
        if pin:
            user.set_pin(pin)
        user.save()
        if roles is not None:
            self._check_outlets(roles)
            self._save_roles(user, roles)
        return user