from rest_framework.permissions import SAFE_METHODS, BasePermission

from .scope import can_manage, can_use_portal


class IsPortalUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and can_use_portal(request.user))


class IsPortalManagerOrReadOnly(BasePermission):
    """Portal users may read; only owner/manager may write."""
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated and can_use_portal(u)):
            return False
        return request.method in SAFE_METHODS or can_manage(u)


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_owner)