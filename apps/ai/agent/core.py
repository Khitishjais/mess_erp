"""The assistant: retrieve, decide, answer, cite. One entry point used by the API."""
from .. import gemini, llm
from . import claude, gemini_loop, offline
from .normalize import to_roman
from .retriever import search
from .tools import Ctx

MAX_Q = 800
MAX_TURNS = 6


def clean_history(history):
    """Keep only well-formed, recent user/assistant text turns from the client."""
    out = []
    for m in (history if isinstance(history, list) else [])[-MAX_TURNS:]:
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and isinstance(m.get('content'), str) and m['content'].strip():
            out.append({'role': m['role'], 'content': m['content'][:MAX_Q]})
    while out and out[0]['role'] != 'user':
        out.pop(0)
    return out


def run_agent(user, question, outlet, outlets, history=None, post=None):
    question = (question or '').strip()[:MAX_Q]
    owner = user if user.is_owner else user.owner
    ctx = Ctx(owner=owner, outlet=outlet, outlets=outlets)
    roman = to_roman(question)           # spoken Hindi arrives in Devanagari; our guides and rules are Roman
    hits = search(owner, outlets, roman)
    local, used, conf = offline.run(roman, ctx, hits)        # free and instant; also the fallback when the AI is unavailable
    heard = roman if roman != question else ''
    note = ''
    if (llm.allowed(owner) or post) and conf != 'high':           # a direct numbers answer needs no model (saves the AI quota)
        try:
            loop = gemini_loop if (llm.provider() == 'gemini' and not post) else claude
            answer, tools_used = loop.run(question, ctx, hits[:3], clean_history(history), post=post)
            if answer:
                return _reply(answer, 'llm', tools_used, hits, 'high' if tools_used else 'medium', heard)
        except Exception as e:
            note = f' (AI unavailable: {gemini.friendly(e)}. Answered from local data.)'
    return _reply(local + note, 'offline', used, hits, conf, heard)


def _reply(answer, mode, used, hits, confidence, heard=''):
    return {'understood_as': heard, 'answer': answer, 'mode': mode, 'tools_used': used, 'confidence': confidence, 'sources': [h.public() for h in hits[:4]]}
