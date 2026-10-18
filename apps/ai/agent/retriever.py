"""Hybrid retrieval: keyword BM25 over guides + the tenant's live records, with a score floor so we never invent an answer."""
from dataclasses import dataclass

from .bm25 import BM25
from .docs import Chunk, doc_chunks
from .live import live_chunks

MIN_SCORE = 1.2          # below this nothing relevant was found
MIN_COVERAGE = 0.5       # at least half of the question's words must appear in the passage


@dataclass
class Hit:
    chunk: Chunk
    score: float

    def public(self):
        return {'title': self.chunk.title, 'kind': self.chunk.kind, 'source': self.chunk.source,
                'snippet': self.chunk.text[:260], 'score': round(self.score, 2)}


def search(owner, outlets, query, k=5):
    """Top-k chunks for the question. Live records come ONLY from `owner`'s tenant."""
    chunks = live_chunks(owner, outlets) + doc_chunks()
    index = BM25([c.title + ' ' + c.text for c in chunks])
    hits = [Hit(chunks[i], s) for s, i in index.top(query, k * 3) if index.coverage(query, i) >= MIN_COVERAGE]
    return [h for h in hits if h.score >= MIN_SCORE][:k]
