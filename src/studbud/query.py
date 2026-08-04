from __future__ import annotations

from dataclasses import dataclass

from .embeddings import Embedder
from .stores.base import SearchHit, VectorStore


@dataclass
class RetrievedContext:
    hits: list[SearchHit]
    

def retrieve(
        store: VectorStore, embedder: Embedder, question: str, k: int
) -> RetrievedContext:
    [vec] = embedder.embed(question)
    return RetrievedContext(hits=store.search(question, vec, k))