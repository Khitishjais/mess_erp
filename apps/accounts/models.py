from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('is_owner', True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    # An owner is the tenant root. Staff users point to their owner.
    is_owner = models.BooleanField(default=False)
    owner = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='staff')
    is_2fa_enabled = models.BooleanField(default=False)
    pin_hash = models.CharField(max_length=128, blank=True)  # POS quick login
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'

    def set_pin(self, pin):
        self.pin_hash = make_password(pin)

    def check_pin(self, pin):
        return bool(self.pin_hash) and check_password(pin, self.pin_hash)

    @property
    def tenant_owner(self):
        return self if self.is_owner else self.owner

    def __str__(self):
        return self.email


class Role(models.TextChoices):
    OWNER = 'owner', 'Owner'
    MANAGER = 'manager', 'Manager'
    CASHIER = 'cashier', 'Cashier / Biller'
    CAPTAIN = 'captain', 'Captain / Waiter'
    KITCHEN = 'kitchen', 'Kitchen'
    STOREKEEPER = 'storekeeper', 'Store keeper'


class StaffOutletRole(models.Model):
    """A staff member holds a role in a specific outlet."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outlet_roles')
    outlet = models.ForeignKey('outlets.Outlet', on_delete=models.CASCADE, related_name='staff_roles')
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        unique_together = ('user', 'outlet', 'role')
