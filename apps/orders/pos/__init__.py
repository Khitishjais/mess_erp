"""POS terminal API (auth, menu sync, bill sync, shifts)."""
from .auth import POS_ROLES, HasDevice, get_device, pos_login, pos_staff
from .menu_sync import bootstrap, changes
from .shifts import shift_close, shift_open
from .sync import sync_orders

__all__ = [
    'POS_ROLES',
    'get_device',
    'HasDevice',
    'pos_login',
    'pos_staff',
    'bootstrap',
    'changes',
    'sync_orders',
    'shift_open',
    'shift_close',
]
