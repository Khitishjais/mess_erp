"""Google Gemini transport (used when GEMINI_API_KEY is set). Same job as the Claude path: read bill photos, answer free-form questions, call our read-only tools."""
import base64
import json
import os
import time
import urllib.error
import urllib.request

BASE = 'https://generativelanguage.googleapis.com/v1beta/models/'


KEY_NAMES = ('GEMINI_API_KEY', 'GEMINI_APIKEY', 'GOOGLE_API_KEY')     # people spell it differently in .env


def key():
    return next((os.environ[n] for n in KEY_NAMES if os.environ.get(n)), '')


DEFAULT_MODELS = ('gemini-2.5-flash', 'gemini-2.5-flash-lite')      # tried in order; each has its own free-tier quota


def models():
    """GEMINI_MODEL may hold one name or a comma-separated list."""
    names = [m.strip() for m in os.environ.get('GEMINI_MODEL', '').split(',') if m.strip()]
    return names or list(DEFAULT_MODELS)


def model():
    return models()[0]


RETRY = (429, 500, 502, 503, 504)      # busy / temporary errors worth trying again
WAITS = (1.5, 4)                       # seconds before retry 1 and 2


def _send(name, body):
    req = urllib.request.Request(f'{BASE}{name}:generateContent', data=json.dumps(body).encode(), method='POST',
                                 headers={'x-goog-api-key': key(), 'content-type': 'application/json'})
    for wait in (*WAITS, None):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in RETRY or e.code == 429 or wait is None:      # 429 = quota: waiting seconds will not help, try another model
                raise
            time.sleep(wait)


def post(body, mdl=None):
    """One generateContent call; returns parsed JSON. The key goes in a header, never in the URL (URLs end up in logs).
    Temporary overload (503 ...) is retried; if a model is over its quota (429), missing (404) or still overloaded, the next model is tried."""
    last = None
    for name in ([mdl] if mdl else models()):
        try:
            return _send(name, body)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 404, *RETRY):
                raise
            last = e
    raise last


def friendly(e):
    """A short, human reason for an AI failure (used in messages to the user)."""
    code = getattr(e, 'code', None)
    if code == 429:
        return 'the AI usage limit was reached (free plan limits are per minute and per day); try again in a minute'
    if code in (401, 403):
        return 'the AI key was refused; check the key in backend/.env'
    if code in RETRY:
        return 'the AI service is busy right now'
    return type(e).__name__


def parts(content):
    """Anthropic-style content (a string, or a list of image/text blocks) -> Gemini parts."""
    if isinstance(content, str):
        return [{'text': content}]
    out = []
    for b in content:
        if b.get('type') == 'image':
            s = b['source']
            out.append({'inline_data': {'mime_type': s['media_type'], 'data': s['data']}})
        else:
            out.append({'text': b.get('text', '')})
    return out


def candidate_parts(resp):
    c = (resp.get('candidates') or [{}])[0]
    return (c.get('content') or {}).get('parts') or []


def text_of(resp):
    got = ''.join(p.get('text', '') for p in candidate_parts(resp))
    if not got and resp.get('promptFeedback', {}).get('blockReason'):
        raise ValueError('The request was blocked by the AI service.')
    return got


def config(max_tokens):
    """Generation settings. 2.5-flash 'thinks' first and thinking tokens count against the limit, which cut bill JSON off mid-way in a real
    test; our jobs (read a bill, answer from given data) do not need it, so it is switched off for flash models."""
    c = {'maxOutputTokens': max_tokens}
    if 'flash' in model():
        c['thinkingConfig'] = {'thinkingBudget': 0}
    return c


def generate(content, system='', max_tokens=800, json_out=False, post_fn=None):
    body = {'contents': [{'role': 'user', 'parts': parts(content)}], 'generationConfig': config(max_tokens)}
    if system:
        body['systemInstruction'] = {'parts': [{'text': system}]}
    if json_out:
        body['generationConfig']['responseMimeType'] = 'application/json'
    return text_of((post_fn or post)(body))


def declarations(schemas):
    """Our tool schemas -> Gemini functionDeclarations (tools with no arguments omit `parameters`)."""
    out = []
    for s in schemas:
        d = {'name': s['name'], 'description': s['description']}
        if s['input_schema'].get('properties'):
            d['parameters'] = {'type': 'object', 'properties': s['input_schema']['properties']}
        out.append(d)
    return [{'functionDeclarations': out}]


def b64(data):
    return base64.b64encode(data).decode()
