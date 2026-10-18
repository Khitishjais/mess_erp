"""The daily stock ledger: one row per outlet + material + day. Shared by stock entry, purchase receiving and the mess automation."""
from .models import StockLedger


def compute_closing(row):
    """closing = opening + purchase + excess - consumed - wastage - normal loss - transfer - shortage + production."""
    row.closing = (row.opening + row.purchase + row.excess - row.consumed - row.wastage - row.normal_loss
                   - row.transfer - row.shortage + row.production)


def ledger_row(outlet, material, day):
    """The day's row for this material; a new day starts from the previous closing so stock carries over."""
    row = StockLedger.objects.filter(outlet=outlet, material=material, date=day).first()
    if row:
        return row
    prev = StockLedger.objects.filter(outlet=outlet, material=material, date__lt=day).order_by('-date').first()
    return StockLedger(outlet=outlet, material=material, date=day, opening=prev.closing if prev else 0)


def add_to_ledger(outlet, material, day, field, delta):
    """Add `delta` (purchase units) to one column of the day's row and recompute the closing."""
    row = ledger_row(outlet, material, day)
    setattr(row, field, (getattr(row, field) or 0) + delta)
    compute_closing(row)
    row.save()
    return row
