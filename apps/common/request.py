"""Small helpers that read the outlet / date a request is about (shared by mess, AI and other apps)."""
from datetime import date as Date
from datetime import datetime, timedelta

from rest_framework.exceptions import ValidationError

from .scope import outlets_for


def resolve_outlet(request):
    """The outlet from ?outlet= / body, else the caller's first mess outlet, else their first outlet."""
    oid = get_id(request, 'outlet') or body_int(request, 'outlet')
    qs = outlets_for(request.user)
    outlet = qs.filter(pk=oid).first() if oid else qs.filter(kind='mess').first() or qs.first()
    if not outlet:
        raise ValidationError('Outlet not found.')
    return outlet


def resolve_day(request, key='date'):
    """The date from ?date=YYYY-MM-DD / body (default: today)."""
    value = request.query_params.get(key) or body_str(request, key)
    if not value:
        return Date.today() + timedelta(days=1) if request.query_params.get('tomorrow') else Date.today()
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError('Use date as YYYY-MM-DD.')


# ---------------------------------------------------------------- query-string parsing (bad input -> clear 400, never a 500)
def get_date(request, key):
    """?key=YYYY-MM-DD as a date, or None when absent."""
    value = request.query_params.get(key)
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError({key: 'Use a real date as YYYY-MM-DD.'})


def get_int(request, key, default, lo=None, hi=None):
    """?key=<whole number>, clamped to [lo, hi]; absent -> default."""
    value = request.query_params.get(key)
    if value in (None, ''):
        return default
    try:
        n = int(value)
    except ValueError:
        raise ValidationError({key: 'Must be a whole number.'})
    if lo is not None:
        n = max(n, lo)
    if hi is not None:
        n = min(n, hi)
    return n


def get_id(request, key):
    """?key=<id> as an int, or None when absent."""
    return get_int(request, key, None)


def get_id_list(request, key):
    """?key=1,2,3 as a list of ints (empty items ignored)."""
    value = request.query_params.get(key)
    if not value:
        return None
    try:
        return [int(x) for x in value.split(',') if x.strip()]
    except ValueError:
        raise ValidationError({key: 'Use a comma separated list of ids.'})


def filter_dates(request, qs, field, from_key='from', to_key='to'):
    """Apply ?from= / ?to= (inclusive) on a date or datetime field."""
    lo, hi = get_date(request, from_key), get_date(request, to_key)
    if lo:
        qs = qs.filter(**{f'{field}__gte': lo})
    if hi:
        qs = qs.filter(**{f'{field}__lte': hi})
    return qs


# ---------------------------------------------------------------- JSON body parsing (wrong types -> 400, never a 500)
def body_str(request, key, default=''):
    """A text field from the JSON body. Numbers become text; objects/lists are rejected."""
    value = request.data.get(key, default)
    if value is None:
        return default
    if isinstance(value, (bool, dict, list)):
        raise ValidationError({key: 'Must be text.'})
    return str(value)


def body_int(request, key, default=None, lo=None, hi=None):
    """A whole-number field from the JSON body (absent/blank -> default), clamped to [lo, hi]."""
    value = request.data.get(key)
    if value in (None, ''):
        return default
    if isinstance(value, (bool, dict, list)):
        raise ValidationError({key: 'Must be a whole number.'})
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValidationError({key: 'Must be a whole number.'})
    if lo is not None:
        n = max(n, lo)
    if hi is not None:
        n = min(n, hi)
    return n


def body_decimal(request, key, default=None, minimum=None):
    """A money/number field from the JSON body as a Decimal (absent/blank -> default)."""
    from decimal import Decimal, InvalidOperation
    value = request.data.get(key)
    if value in (None, ''):
        return default
    if isinstance(value, (bool, dict, list)):
        raise ValidationError({key: 'Must be a number.'})
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError({key: 'Must be a number.'})
    if not d.is_finite() or (minimum is not None and d < minimum):
        raise ValidationError({key: 'Must be a valid number' + (f' of at least {minimum}.' if minimum is not None else '.')})
    return d
