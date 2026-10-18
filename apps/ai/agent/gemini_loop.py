"""Tool-using Gemini loop for the assistant (used when GEMINI_API_KEY is set). Same read-only tools and same rules as the Claude loop."""
import json

from .. import gemini
from . import tools
from .claude import MAX_STEPS, SYSTEM, _context


def plain(result):
    """Tool results hold Decimals and dates; Gemini needs plain JSON, and a huge result would eat the context window."""
    out = json.loads(json.dumps(result, default=str))
    return out if len(json.dumps(out)) < 12000 else {'note': 'Result too long; ask a narrower question.', 'preview': json.dumps(out)[:6000]}


def run(question, ctx, hits, history=(), post=None):
    """Returns (answer, tools_used). `post` can be swapped in tests."""
    post = post or gemini.post
    contents = [{'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [{'text': m['content']}]} for m in history]
    contents.append({'role': 'user', 'parts': [{'text': f'{_context(hits)}\n\nQuestion: {question}'}]})
    used = []
    for _ in range(MAX_STEPS):
        resp = post({'systemInstruction': {'parts': [{'text': SYSTEM}]}, 'tools': gemini.declarations(tools.schemas()), 'contents': contents,
                     'generationConfig': gemini.config(1500)})
        parts = gemini.candidate_parts(resp)
        calls = [p['functionCall'] for p in parts if 'functionCall' in p]
        if not calls:
            return gemini.text_of(resp).strip(), used
        contents.append({'role': 'model', 'parts': parts})
        replies = []
        for c in calls:
            used.append(c['name'])
            replies.append({'functionResponse': {'name': c['name'], 'response': {'result': plain(tools.call(c['name'], ctx, c.get('args')))}}})
        contents.append({'role': 'user', 'parts': replies})
    return 'I could not finish this in a few steps; please ask a narrower question.', used
