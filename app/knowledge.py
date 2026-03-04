"""
Lightweight knowledge base.

Loads the four Markdown documents from data/, chunks them into ~250-word
windows with 40-word overlap, and returns the most relevant chunks for a
query using TF-IDF term-overlap scoring (no external dependencies).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from math import log

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_SOURCES = ["faq.md", "return_policy.md", "shipping_info.md", "warranty.md"]
_CHUNK_WORDS = 250
_CHUNK_OVERLAP = 40


@dataclass
class _Chunk:
    text: str
    source: str
    words: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.words = re.findall(r"[a-z]+", self.text.lower())


def _load_source(path: str, source: str) -> list[_Chunk]:
    with open(path, encoding="utf-8") as fh:
        words = fh.read().split()
    step = _CHUNK_WORDS - _CHUNK_OVERLAP
    chunks: list[_Chunk] = []
    for i in range(0, max(1, len(words) - _CHUNK_OVERLAP), step):
        chunk_words = words[i : i + _CHUNK_WORDS]
        if chunk_words:
            chunks.append(_Chunk(text=" ".join(chunk_words), source=source))
    return chunks


class KnowledgeBase:
    def __init__(self) -> None:
        self._chunks: list[_Chunk] = []
        for fname in _SOURCES:
            path = os.path.join(_DATA_DIR, fname)
            if os.path.exists(path):
                self._chunks.extend(_load_source(path, fname))

        # Build IDF weights
        N = len(self._chunks) or 1
        df: dict[str, int] = {}
        for c in self._chunks:
            for w in set(c.words):
                df[w] = df.get(w, 0) + 1
        self._idf: dict[str, float] = {w: log(N / (1 + d)) for w, d in df.items()}

    def count(self) -> int:
        return len(self._chunks)

    def search(self, query: str, top_k: int = 4) -> list[str]:
        if not self._chunks:
            return []
        q_words = set(re.findall(r"[a-z]+", query.lower()))
        scored: list[tuple[float, _Chunk]] = []
        for chunk in self._chunks:
            score = sum(self._idf.get(w, 0.0) for w in q_words.intersection(chunk.words))
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c.text for _, c in scored[:top_k]]
