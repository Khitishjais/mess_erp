"""Match a name printed on a bill ("BASMATI RICE 25KG") to one of the business's raw materials."""
import re
from difflib import SequenceMatcher

NOISE = re.compile(r'\b\d+(\.\d+)?\s*(kg|gm|g|ltr|l|ml|pc|pcs|nos)\b|\b(fresh|premium|grade|pack|packet|loose|brand)\b', re.I)
SURE, MAYBE = 0.9, 0.72


def _word(w):
    if len(w) > 3 and w.endswith('s'):          # plural first ('eggs' -> 'egg'), THEN fold spelling ('egg' -> 'eg') so both sides agree
        w = w[:-1]
    for x, y in (('aa', 'a'), ('ee', 'i'), ('oo', 'u')):
        w = w.replace(x, y)
    return re.sub(r'([a-z])\1+', r'\1', w)


def norm(name):
    s = NOISE.sub(' ', (name or '').lower())
    s = re.sub(r'[^a-z0-9\u0900-\u097f ]+', ' ', s)
    return ' '.join(_word(w) for w in s.split())


def score(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    token = len(ta & tb) / len(ta | tb)
    contain = 0.85 if (ta <= tb or tb <= ta) else 0.0           # "rice" inside "basmati rice"
    head = 0.75 if (na.split()[-1] == nb.split()[-1] and len(na.split()[-1]) >= 3) else 0.0   # "refined oil" ~ "cooking oil": same item type, flagged for a check
    return max(SequenceMatcher(None, na, nb).ratio(), token, contain, head)


def best_match(name, materials):
    """(material, score) for the best candidate, or (None, 0) when nothing is close enough to suggest."""
    best, top = None, 0.0
    for m in materials:
        s = score(name, m.name)
        if s > top:
            best, top = m, s
    return (best, round(top, 2)) if top >= MAYBE else (None, round(top, 2))
