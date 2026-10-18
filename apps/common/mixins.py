from .scope import outlets_for, owner_of


class OwnerScopedMixin:
    """Queryset filtered to the caller's tenant; owner set automatically on create."""
    owner_field = 'owner'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{self.owner_field: owner_of(self.request.user)})

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: owner_of(self.request.user)})


class OutletScopedMixin:
    """For models with an `outlet` FK: limited to outlets the caller can see."""
    outlet_field = 'outlet'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{f'{self.outlet_field}__in': outlets_for(self.request.user)})