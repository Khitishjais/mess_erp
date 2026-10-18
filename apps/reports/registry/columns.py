"""Column helpers and constants shared by all reports."""
from decimal import Decimal

MODES = ['cash', 'card', 'due', 'other', 'wallet', 'upi', 'online']


ZERO = Decimal(0)


MONEY, INT, TEXT, DATE = 'money', 'int', 'text', 'date'


def col(key, label, typ=TEXT):
    return {'key': key, 'label': label, 'type': typ}
