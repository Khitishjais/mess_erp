"""Tenant + outlet scoping helpers. Every query goes through these."""
from apps.accounts.models import Role, StaffOutletRole
from apps.outlets.models import Outlet

PORTAL_ROLES = {Role.OWNER, Role.MANAGER, Role.STOREKEEPER}


def owner_of(user):
    return user.tenant_owner


def outlets_for(user):
    """Outlets the user may see. Owner: all of the tenant's outlets. Staff: their assigned outlets."""
    if user.is_owner:
        return Outlet.objects.filter(owner=user)
    ids = StaffOutletRole.objects.filter(user=user).values_list('outlet_id', flat=True)
    return Outlet.objects.filter(owner=user.owner, id__in=ids)


def roles_for(user, outlet_id=None):
    if user.is_owner:
        return {Role.OWNER}
    qs = StaffOutletRole.objects.filter(user=user)
    if outlet_id:
        qs = qs.filter(outlet_id=outlet_id)
    return set(qs.values_list('role', flat=True))


def can_use_portal(user):
    return user.is_owner or bool(roles_for(user) & PORTAL_ROLES)


def can_manage(user):
    """Create/edit staff, menu, outlets: owner or manager."""
    return user.is_owner or Role.MANAGER in roles_for(user)