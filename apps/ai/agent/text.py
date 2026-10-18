"""Tokenising for English / Hindi / Hinglish questions. Pure python, no model download, works offline."""
import re

WORD = re.compile(r'[\wऀ-ॿ]+', re.UNICODE)
STOP = set('a an the is are was were be to of in on for and or at by with it this that what which how do does did me my our i you we can '
           'ka ki ke ko se me mein hai hain tha thi ho hoga kya kaise kitna kitni kitne aur ya par pe bhi ek yeh ye wo woh please batao bata do '
           'dena de'.split())
# Hinglish (and a few Hindi) words mapped to the English words our documents use.
SYN = {
    'kharid': 'purchase buy', 'kharidna': 'purchase buy', 'kharidni': 'purchase buy', 'mangwa': 'purchase order', 'bikri': 'sales',
    'kamai': 'sales revenue', 'bika': 'sales', 'barbaad': 'waste wastage', 'phenk': 'waste', 'fenk': 'waste', 'bacha': 'leftover',
    'bachha': 'leftover', 'kal': 'tomorrow', 'aaj': 'today', 'parso': 'day after tomorrow', 'daam': 'price rate cost', 'kimat': 'price cost',
    'kharcha': 'cost expense', 'log': 'people headcount', 'students': 'people headcount', 'chawal': 'rice', 'murgi': 'chicken', 'murga': 'chicken',
    'pyaz': 'onion', 'pyaaz': 'onion', 'aloo': 'potato', 'dahi': 'curd', 'doodh': 'milk', 'tel': 'oil', 'cheeni': 'sugar', 'anda': 'egg',
    'mirch': 'chilli', 'masala': 'spices masala', 'dal': 'dal lentil', 'sabzi': 'vegetable', 'paneer': 'paneer', 'rasoiya': 'cook staff',
    'kaam': 'work', 'shuru': 'start setup', 'kaise': 'how', 'chalu': 'start run', 'internet': 'offline online', 'band': 'offline off',
    'password': 'password login', 'pin': 'pin login', 'bill': 'bill order invoice', 'hisab': 'report account', 'stock': 'stock inventory',
    'khatam': 'low stock finished', 'expire': 'expiry shelf life', 'kharab': 'spoil expiry', 'menu': 'menu', 'recipe': 'recipe', 'naya': 'new add',
}


FOLD = (('aa', 'a'), ('ee', 'i'), ('ii', 'i'), ('oo', 'u'), ('uu', 'u'))


def fold(w):
    """Spelling-variance folding so 'paneer'/'panir', 'tikka'/'tikkaa', 'aloo'/'alu' meet (speech and transliteration spell loosely)."""
    for a, b in FOLD:
        w = w.replace(a, b)
    return re.sub(r'([a-z])\1+', r'\1', w)


def stem(w):
    for suf in ('ing', 'es', 's', 'ed'):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    return fold(w)


def tokens(text, expand=False):
    """Lower-cased word stems; with expand=True Hinglish words also add their English meaning."""
    out = []
    for w in WORD.findall((text or '').lower()):
        if w in STOP or len(w) < 2:
            continue
        out.append(stem(w))
        if expand and w in SYN:
            out.extend(stem(x) for x in SYN[w].split())
    return out
