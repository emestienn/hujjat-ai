"""Hybrid retrieval: BM25 keyword search + (optional) embedding similarity, merged with
Reciprocal Rank Fusion (RRF).

Why hybrid? Keyword search is great for exact terms (article numbers, names, Uzbek words that
embedding models handle poorly). Embeddings catch paraphrases ("fee" vs "payment"). RRF combines
both rankings without needing to calibrate their scores against each other.
"""

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from .db import Chunk, Store
from .embeddings import Embedder

_APOSTROPHES = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "`": "'"})
_TOKEN = re.compile(r"[\w']+", re.UNICODE)
RRF_K = 60


def tokenize(text: str) -> list[str]:
    """Lowercase, normalise Uzbek apostrophes (o‘ / gʻ), split into word tokens."""
    text = text.lower().translate(_APOSTROPHES)
    return [t.strip("'") for t in _TOKEN.findall(text) if t.strip("'")]


@dataclass
class Hit:
    chunk: Chunk
    score: float


class Retriever:
    def __init__(self, store: Store, embedder: Embedder):
        self.store = store
        self.embedder = embedder
        self._cache_version = -1
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None
        self._matrix: np.ndarray | None = None  # normalised embeddings, one row per chunk

    def _refresh(self) -> None:
        if self._cache_version == self.store.version:
            return
        self._chunks = self.store.all_chunks()
        corpus = [tokenize(c.text) for c in self._chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

        embs = [c.embedding for c in self._chunks]
        if embs and all(e is not None for e in embs):
            m = np.vstack(embs)
            self._matrix = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
        else:
            self._matrix = None
        self._cache_version = self.store.version

    def search(self, query: str, k: int = 5, document_ids: list[str] | None = None) -> list[Hit]:
        self._refresh()
        if not self._chunks:
            return []

        allowed = np.ones(len(self._chunks), dtype=bool)
        if document_ids:
            wanted = set(document_ids)
            allowed = np.array([c.document_id in wanted for c in self._chunks])
            if not allowed.any():
                return []

        rankings: list[np.ndarray] = []

        tokens = tokenize(query)
        bm25_scores = np.zeros(len(self._chunks))
        if tokens and self._bm25 is not None:
            bm25_scores = np.asarray(self._bm25.get_scores(tokens))
            ranked = [i for i in np.argsort(-bm25_scores) if allowed[i] and bm25_scores[i] > 0]
            rankings.append(np.array(ranked, dtype=int))

        if self._matrix is not None:
            q = self.embedder.embed_query(query)
            if q is not None:
                qv = np.asarray(q, dtype=np.float32)
                qv /= np.linalg.norm(qv) + 1e-9
                sims = self._matrix @ qv
                ranked = [i for i in np.argsort(-sims) if allowed[i]]
                rankings.append(np.array(ranked[: max(k * 4, 20)], dtype=int))

        if not rankings or all(len(r) == 0 for r in rankings):
            return []

        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[int(idx)] = fused.get(int(idx), 0.0) + 1.0 / (RRF_K + rank + 1)

        best = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]
        top = best[0][1]
        return [Hit(self._chunks[i], round(score / top, 4)) for i, score in best]
