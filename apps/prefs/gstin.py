"""GSTIN checks. A GSTIN is 15 characters: 2-digit state code, 10-character PAN, entity number, 'Z', and a check character."""
import re

SHAPE = re.compile(r'^(0[1-9]|[12][0-9]|3[0-8])[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')
CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
STATES = {'01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab', '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana', '07': 'Delhi',
          '08': 'Rajasthan', '09': 'Uttar Pradesh', '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh', '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
          '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam', '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha', '22': 'Chhattisgarh', '23': 'Madhya Pradesh',
          '24': 'Gujarat', '26': 'Dadra & Nagar Haveli and Daman & Diu', '27': 'Maharashtra', '29': 'Karnataka', '30': 'Goa', '31': 'Lakshadweep', '32': 'Kerala',
          '33': 'Tamil Nadu', '34': 'Puducherry', '35': 'Andaman & Nicobar', '36': 'Telangana', '37': 'Andhra Pradesh', '38': 'Ladakh'}


def check_char(first14):
    """The official check character (mod-36 weighted sum)."""
    total = 0
    for i, ch in enumerate(first14):
        v = CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += v // 36 + v % 36
    return CHARS[(36 - total % 36) % 36]


def inspect(value):
    """(normalised, problem, warning). Shape errors are problems (refused); a wrong check character is only a warning, so a number is never blocked by a typo-prone rule."""
    g = (value or '').strip().upper().replace(' ', '')
    if not g:
        return '', None, None
    if not SHAPE.match(g):
        return g, 'GSTIN must be 15 characters like 21ABCDE1234F1Z5 (state code, PAN, entity number, Z, check character).', None
    if g[:2] not in STATES:
        return g, f'{g[:2]} is not a valid state code.', None
    warn = None if check_char(g[:14]) == g[14] else 'The last character does not match the GSTIN check rule. Please verify the number on your GST certificate.'
    return g, None, warn
