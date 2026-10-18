"""BM25 ranking (the classic keyword-relevance formula). Small, deterministic, explainable."""
import math
from collections import Counter

from .text import SYN, stem, tokens


class BM25:
    def __init__(self, texts, k1=1.4, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokens(t)) for t in texts]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def score(self, query_tokens, i):
        d, ln, s = self.docs[i], self.lens[i], 0.0
        for w in set(query_tokens):
            f = d.get(w)
            if f:
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * ln / (self.avg or 1)))
        return s

    def top(self, query, k=5):
        q = tokens(query, expand=True)
        if not q or not self.docs:
            return []
        ranked = sorted(((self.score(q, i), i) for i in range(len(self.docs))), reverse=True)
        return [(s, i) for s, i in ranked[:k] if s > 0]

    def coverage(self, query, i):
        """Share of the question's meaningful words (counting their English meanings) that this document contains."""
        groups = []
        for w in tokens(query):
            groups.append({w} | {stem(x) for src, syn in SYN.items() if stem(src) == w for x in syn.split()})
        if not groups:
            return 0.0
        return sum(1 for g in groups if any(x in self.docs[i] for x in g)) / len(groups)
