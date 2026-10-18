"""Generic report engine. A report = columns + a function returning rows. Shared by all 23 reports."""
from . import definitions  # noqa: E402,F401  (importing it registers all 23 reports)
from .columns import DATE, INT, MODES, MONEY, TEXT, ZERO, col
from .core import REPORTS, reg, totals
from .filters import item_qs, order_qs
from .items import ITEM_AGG, hourly_items, item_group, item_rows, tag_wise
from .orders import order_rows
from .sales import (
    LABELS_FOR,
    SALES_COLS,
    SUMS,
    grouped_sales,
    outlet_performance,
    sales_report,
)

__all__ = [
    'DATE',
    'INT',
    'MODES',
    'MONEY',
    'TEXT',
    'ZERO',
    'col',
    'REPORTS',
    'reg',
    'totals',
    'item_qs',
    'order_qs',
    'ITEM_AGG',
    'hourly_items',
    'item_group',
    'item_rows',
    'tag_wise',
    'order_rows',
    'LABELS_FOR',
    'SALES_COLS',
    'SUMS',
    'grouped_sales',
    'outlet_performance',
    'sales_report',
]
