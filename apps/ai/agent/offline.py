"""No-LLM answering: the existing numbers-based router first, then plain retrieval from guides + the business's own records.
Works with no internet and no API key, and says so honestly when it finds nothing."""
import re

from ..services import answer as rules_answer

HINGLISH = ('kya', 'kitna', 'kitne', 'kaise', 'hai', 'kal', 'aaj', 'batao', 'mujhe', 'ka ', 'ki ', 'ke ', 'nahi', 'karna', 'chahiye')


def is_hindi(q):
    low = q.lower() + ' '
    return any('ऀ' <= ch <= 'ॿ' for ch in q) or sum(w in low for w in HINGLISH) >= 2


OTHER_INDIC = re.compile('[ঀ-෿]')      # Bengali, Gujarati, Tamil, Telugu, Kannada, Malayalam, Punjabi ... scripts


def other_script_message():
    return ('Is bhasha ko samajhne ke liye AI key chahiye (GEMINI_API_KEY ya ANTHROPIC_API_KEY). Bina key ke main Hindi, Hinglish aur English samajhta hoon. '
            'This language needs the AI key; without it I understand Hindi, Hinglish and English.')


def not_found(q):
    if OTHER_INDIC.search(q):
        return other_script_message()
    if is_hindi(q):
        return ('Mujhe is sawal ka jawab apne guides ya aapke records me nahi mila. Aap menu, recipe, stock, kharid, wastage, staff, sales '
                'ya setup ke baare me poochh sakte hain. (Khule sawalon ke liye AI key set karein: GEMINI_API_KEY ya ANTHROPIC_API_KEY.)')
    return ("I couldn't find that in the guides or your records. Try asking about menu, recipes, stock, purchases, wastage, staffing, sales or setup. "
            '(Open-ended questions need an AI key: GEMINI_API_KEY or ANTHROPIC_API_KEY.)')


HOWTO = re.compile(r'\b(how (do|can|to|should)|kaise|kahan|kaha|where|steps?|set ?up|guide|tutorial|banana|banao|add karna|jodna)\b', re.I)
RECORD = re.compile(r'\b(per plate|ek plate|plate me|per serving|recipe|ingredients?|menu|price|rate|daam|kimat|costs?)\b', re.I)


def preferred_kind(question):
    """How-to questions belong to the guides ('doc'); 'what is in / what does it cost' questions to the records ('data')."""
    if HOWTO.search(question):
        return 'doc'
    return 'data' if RECORD.search(question) else None


def run(question, ctx, hits):
    """Returns (answer, tools_used, confidence)."""
    kind = preferred_kind(question)
    top = [h for h in hits[:4] if h.chunk.kind == kind]
    if top:
        hits = top + [h for h in hits if h not in top]
    r = None if top else rules_answer(question, ctx.outlet, ctx.outlets)
    if r:
        return r['answer'], [r['intent']], 'high'
    if not hits:
        return not_found(question), [], 'none'
    best = hits[0]
    lines = [best.chunk.text.strip()]
    for h in hits[1:3]:
        if h.chunk.kind == best.chunk.kind and h.score > best.score * 0.6:
            lines.append(h.chunk.text.strip())
    prefix = f'From "{best.chunk.title}" ({best.chunk.source}):\n'
    return prefix + '\n\n'.join(lines)[:1400], ['knowledge'], 'medium' if best.score >= 3 else 'low'
