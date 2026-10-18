"""Every setting the business can configure: ONE list, used by the API, the Settings screen and the code that reads the values.
Adding a setting = adding one line here (plus using it where it matters)."""
import re
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from . import gstin as gst

CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
PHONE = re.compile(r'^[0-9+\-() ]{6,20}$')
UPI = re.compile(r'^[A-Za-z0-9._\-]{2,}@[A-Za-z][A-Za-z0-9]{1,}$')


@dataclass(frozen=True)
class Def:
    key: str
    group: str
    label: str
    help: str
    kind: str                       # text | bool | int | choice
    default: object = ''
    scope: str = 'outlet'           # 'outlet': can differ per outlet (or be a business-wide default); 'tenant': one value for the whole business
    pos: bool = False               # also sent to the POS counter app
    maxlen: int = 120
    lo: int = 0
    hi: int = 0
    choices: tuple = ()
    check: str = ''                 # gstin | phone | fssai | upi
    outlet_field: str = ''          # stored on the Outlet itself instead of the settings table
    unit: str = ''


DEFS = [
    Def('address', 'Business and bill header', 'Address on the bill', 'Printed under the name on every bill.', 'text', '', pos=True, maxlen=300, outlet_field='address'),
    Def('gstin', 'Business and bill header', 'GSTIN', 'Your 15-character GST number. Printed on the bill. Leave empty if not registered.', 'text', '', pos=True, maxlen=15, check='gstin', outlet_field='gstin'),
    Def('bill_name', 'Business and bill header', 'Name printed on the bill', 'Leave empty to use the outlet name.', 'text', '', pos=True, maxlen=80),
    Def('phone', 'Business and bill header', 'Phone number', 'Printed on the bill so customers can call.', 'text', '', pos=True, maxlen=20, check='phone'),
    Def('fssai', 'Business and bill header', 'FSSAI licence number', '14 digits. Printed on the bill (food businesses must show it).', 'text', '', pos=True, maxlen=14, check='fssai'),
    Def('bill_footer', 'Bill content', 'Thank-you line at the bottom', 'The last line of the bill.', 'text', 'Thank you! Visit again.', pos=True, maxlen=120),
    Def('bill_note', 'Bill content', 'Extra note (optional)', 'For example: "Prices include all taxes" or "No refund on food".', 'text', '', pos=True, maxlen=160),
    Def('upi_id', 'Bill content', 'UPI ID to print', 'Printed as "Pay by UPI: name@bank" so customers can pay you directly.', 'text', '', pos=True, maxlen=60, check='upi'),
    Def('tax_style', 'Bill content', 'How GST is shown', 'CGST + SGST split (usual for restaurants in one state) or one GST line.', 'choice', 'cgst_sgst', pos=True, choices=(('cgst_sgst', 'CGST + SGST'), ('gst', 'One GST line'))),
    Def('show_gstin', 'Bill content', 'Print GSTIN on the bill', '', 'bool', True, pos=True),
    Def('show_cashier', 'Bill content', 'Print cashier name', '', 'bool', True, pos=True),
    Def('show_item_rate', 'Bill content', 'Print rate under each item', 'Shows "2 x 220.00" under each item.', 'bool', True, pos=True),
    Def('paper_width', 'Bill content', 'Paper width', 'Match your receipt printer roll.', 'choice', '80', pos=True, choices=(('80', '80 mm'), ('58', '58 mm'))),
    Def('auto_print_bill', 'Counter (POS) behaviour', 'Print the bill automatically on Settle', 'If off, the cashier prints with "Reprint bill".', 'bool', True, pos=True),
    Def('auto_print_kot', 'Counter (POS) behaviour', 'Print the kitchen slip automatically on KOT', '', 'bool', True, pos=True),
    Def('require_discount_reason', 'Counter (POS) behaviour', 'Ask for a reason when a discount is given', 'The cashier must type why. Helps catch misuse.', 'bool', False, pos=True),
    Def('max_discount_pct', 'Counter (POS) behaviour', 'Highest discount a cashier can give', 'Percent of the bill. Managers and owners are not limited. 100 = no limit.', 'int', 100, pos=True, lo=0, hi=100, unit='%'),
    Def('auto_deduct_stock', 'Mess automation', 'Deduct ingredients from stock when attendance is saved', 'Turn off if you track stock only by counting.', 'bool', True),
    Def('reminders_enabled', 'Mess automation', 'Send reminders (attendance, stock count, wastage)', 'They appear under the bell icon.', 'bool', True),
    Def('alert_horizon_days', 'Stock and alerts', 'Look-ahead for stock alerts', 'Stock alerts compare stock with the need for this many days.', 'int', 7, scope='tenant', lo=1, hi=30, unit='days'),
    Def('rate_jump_pct', 'Stock and alerts', 'Warn when a bill price differs by more than', 'Used when reading supplier bills against your raw-material rates.', 'int', 30, scope='tenant', lo=5, hi=200, unit='%'),
    Def('overcook_pct', 'Stock and alerts', 'Flag cooking more than this % of people served', '140 means: flag when plates cooked are over 140% of people who ate.', 'int', 140, scope='tenant', lo=105, hi=300, unit='%'),
    Def('ai_external', 'AI and privacy', 'Allow the external AI service (Gemini / Claude)', 'If off, bill photos and open questions are not sent to any outside service. Local answers still work.', 'bool', True, scope='tenant'),
]
BY_KEY = {d.key: d for d in DEFS}
GROUPS = list(dict.fromkeys(d.group for d in DEFS))


def clean(d, raw):
    """(value, warning). Raises ValidationError with a message the owner can act on."""
    if d.kind == 'bool':
        if not isinstance(raw, bool):
            raise ValidationError(f'{d.label}: use on or off.')
        return raw, None
    if d.kind == 'int':
        if isinstance(raw, bool) or not (isinstance(raw, int) or (isinstance(raw, str) and re.fullmatch(r'-?\d{1,6}', raw.strip()))):
            raise ValidationError(f'{d.label}: enter a whole number.')
        n = int(raw)
        if not d.lo <= n <= d.hi:
            raise ValidationError(f'{d.label}: must be between {d.lo} and {d.hi}.')
        return n, None
    if not isinstance(raw, str):
        raise ValidationError(f'{d.label}: enter text.')
    s = re.sub(r'[ \t]+', ' ', raw).strip()
    if CONTROL.search(s):
        raise ValidationError(f'{d.label}: contains characters that cannot be printed.')
    if d.kind == 'choice':
        if s not in dict(d.choices):
            raise ValidationError(f'{d.label}: choose one of {", ".join(v for v, _ in d.choices)}.')
        return s, None
    if len(s) > d.maxlen:
        raise ValidationError(f'{d.label}: at most {d.maxlen} characters.')
    return _check_text(d, s)


def _check_text(d, s):
    if not s:
        return '', None
    if d.check == 'gstin':
        g, problem, warn = gst.inspect(s)
        if problem:
            raise ValidationError(f'{d.label}: {problem}')
        return g, warn
    if d.check == 'phone' and not PHONE.match(s):
        raise ValidationError(f'{d.label}: use digits, spaces, + - ( ) only (6 to 20 characters).')
    if d.check == 'fssai' and not re.fullmatch(r'\d{14}', s):
        raise ValidationError(f'{d.label}: must be exactly 14 digits.')
    if d.check == 'upi' and not UPI.match(s):
        raise ValidationError(f'{d.label}: must look like name@bank.')
    return s, None


def public(d):
    return {'key': d.key, 'group': d.group, 'label': d.label, 'help': d.help, 'kind': d.kind, 'default': d.default, 'scope': d.scope, 'maxlen': d.maxlen, 'lo': d.lo,
            'hi': d.hi, 'unit': d.unit, 'choices': [{'value': v, 'label': lbl} for v, lbl in d.choices], 'needs_outlet': bool(d.outlet_field)}
