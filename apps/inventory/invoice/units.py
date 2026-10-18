"""Units on supplier bills ("kgs", "Ltr", "dz") mapped to our units, and conversion between them."""
ALIAS = {
    'kg': 'kg', 'kgs': 'kg', 'kilo': 'kg', 'kilos': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
    'g': 'gm', 'gm': 'gm', 'gms': 'gm', 'gram': 'gm', 'grams': 'gm', 'gr': 'gm',
    'l': 'ltr', 'lt': 'ltr', 'ltr': 'ltr', 'ltrs': 'ltr', 'litre': 'ltr', 'litres': 'ltr', 'liter': 'ltr', 'liters': 'ltr',
    'ml': 'ml', 'millilitre': 'ml',
    'pc': 'pc', 'pcs': 'pc', 'piece': 'pc', 'pieces': 'pc', 'nos': 'pc', 'no': 'pc', 'no.': 'pc', 'unit': 'pc', 'units': 'pc', 'each': 'pc', 'ea': 'pc',
    'dozen': 'dozen', 'doz': 'dozen', 'dz': 'dozen',
}
# how many of the key unit are in ONE of the inner unit: FACTOR[(from, to)] = to-units per 1 from-unit
FACTOR = {('kg', 'gm'): 1000, ('gm', 'kg'): 0.001, ('ltr', 'ml'): 1000, ('ml', 'ltr'): 0.001, ('dozen', 'pc'): 12, ('pc', 'dozen'): 1 / 12}


def canon(unit):
    u = (unit or '').strip().lower().rstrip('.')
    return ALIAS.get(u) or ALIAS.get(u + '.') or u


def factor(from_unit, to_unit):
    """How many `to_unit` equal one `from_unit` (1 when the same), or None when they cannot be converted (kg vs pc)."""
    a, b = canon(from_unit), canon(to_unit)
    if a == b:
        return 1.0
    return FACTOR.get((a, b))


def base_units(unit):
    """For a brand-new raw material bought in `unit`: (consumption unit, conversion)."""
    return {'kg': ('gm', 1000), 'ltr': ('ml', 1000), 'dozen': ('pc', 12)}.get(canon(unit), (canon(unit) or 'pc', 1))
