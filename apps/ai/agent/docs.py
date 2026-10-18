"""Static knowledge: the project's own guides, split into one chunk per heading (cached until the file changes)."""
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FILES = [('TUTORIAL_EN.md', 'Tutorial (English)'), ('TUTORIAL_HINGLISH.md', 'Tutorial (Hinglish)'),
         ('DECISIONS.md', 'Design decisions'), ('FLOW.md', 'How it works')]
_cache = {}
SECRET = re.compile(r'Demo@|@demo\.test|password\s*[:=]', re.I)     # never index demo logins or credentials


@dataclass(frozen=True)
class Chunk:
    title: str
    text: str
    kind: str          # 'doc' = from our guides, 'data' = this business's own live records
    source: str


def split_markdown(md, source, limit=900):
    """One chunk per '## ' / '### ' section; long sections are cut on paragraph borders."""
    chunks, title, buf = [], source, []

    def flush():
        body = '\n'.join(buf).strip()
        for part in _cut(body, limit):
            chunks.append(Chunk(title, part, 'doc', source))

    for line in md.splitlines():
        if SECRET.search(line):
            continue
        m = re.match(r'^#{1,3}\s+(.*)', line)
        if m:
            flush(); buf.clear(); title = m.group(1).strip()
        else:
            buf.append(line)
    flush()
    return [c for c in chunks if len(c.text) > 25]


def _cut(body, limit):
    if len(body) <= limit:
        return [body] if body else []
    parts, cur = [], ''
    for para in body.split('\n\n'):
        if cur and len(cur) + len(para) > limit:
            parts.append(cur.strip()); cur = ''
        cur += para + '\n\n'
    return parts + ([cur.strip()] if cur.strip() else [])


def doc_chunks():
    out = []
    for name, label in FILES:
        p = ROOT / name
        if not p.exists():
            continue
        stamp = p.stat().st_mtime
        if _cache.get(name, (None,))[0] != stamp:
            _cache[name] = (stamp, split_markdown(p.read_text(encoding='utf-8', errors='replace'), label))
        out.extend(_cache[name][1])
    return out
