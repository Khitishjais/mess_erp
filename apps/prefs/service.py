"""Reading and writing settings. Lookup order for one outlet: that outlet's own value, then the business-wide default, then the built-in default."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog

from .models import Setting
from .registry import BY_KEY, DEFS, GROUPS, clean, public


def _rows(owner, outlet):
    """{key: value} from the settings table for this owner: business-wide rows overlaid by the outlet's own rows."""
    out = {}
    for r in Setting.objects.filter(owner=owner, outlet__isnull=True):
        out[r.key] = (r.value, 'default')
    if outlet is not None:
        for r in Setting.objects.filter(owner=owner, outlet=outlet):
            out[r.key] = (r.value, 'outlet')
    return out


def effective(owner, outlet=None):
    """{key: (value, source)} for every setting. source is 'outlet', 'default' (business-wide) or 'builtin'."""
    rows = _rows(owner, outlet)
    res = {}
    for d in DEFS:
        if d.outlet_field and outlet is not None:
            res[d.key] = (getattr(outlet, d.outlet_field), 'outlet')
        else:
            res[d.key] = rows.get(d.key, (d.default, 'builtin'))
    return res


def get(owner, key, outlet=None):
    return effective(owner, outlet)[key][0]


def describe(owner, outlet=None):
    """What the Settings screen shows: groups of settings with their current value and where it comes from."""
    eff = effective(owner, outlet)
    groups = []
    for g in GROUPS:
        items = []
        for d in (x for x in DEFS if x.group == g):
            value, source = eff[d.key]
            items.append({**public(d), 'value': value, 'source': source})
        groups.append({'title': g, 'items': items})
    return groups


def pos_payload(outlet):
    """The settings the counter app needs to print bills and apply its rules."""
    eff = effective(outlet.owner, outlet)
    return {d.key: eff[d.key][0] for d in DEFS if d.pos}


def save(user, outlet, values):
    """Validate everything first, then write all-or-nothing. A value of null removes the override (back to the default)."""
    if not isinstance(values, dict) or not values:
        raise ValidationError('Send the settings to change.')
    owner = user.tenant_owner
    plan, warnings = [], []
    for key, raw in values.items():
        d = BY_KEY.get(key)
        if not d:
            raise ValidationError(f'Unknown setting: {key}.')
        if d.scope == 'tenant' and outlet is not None:
            raise ValidationError(f'{d.label}: applies to the whole business. Choose "All outlets" to change it.')
        if d.outlet_field and outlet is None:
            raise ValidationError(f'{d.label}: choose an outlet first.')
        if raw is None:
            plan.append((d, None, True))
            continue
        value, warn = clean(d, raw)
        if warn:
            warnings.append(warn)
        plan.append((d, value, False))
    with transaction.atomic():
        for d, value, reset in plan:
            if d.outlet_field:
                setattr(outlet, d.outlet_field, '' if reset else value)
                continue
            if reset:
                Setting.objects.filter(owner=owner, outlet=outlet, key=d.key).delete()
            else:
                Setting.objects.update_or_create(owner=owner, outlet=outlet, key=d.key, defaults={'value': value, 'updated_by': user})
        if outlet is not None and any(d.outlet_field for d, _, _ in plan):
            outlet.save(update_fields=[d.outlet_field for d, _, _ in plan if d.outlet_field])
        AuditLog.objects.create(owner=owner, outlet=outlet, actor=user, kind='settings',
                                message=('Settings changed: ' + ', '.join(sorted(d.label for d, _, _ in plan)))[:300])
    return warnings
