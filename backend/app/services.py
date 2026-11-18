"""Wires the store, embedder, retriever and LLM provider together for the API."""

from dataclasses import dataclass

from .config import Settings
from .db import Store
from .embeddings import Embedder
from .ingest import chunk_pages, parse_file
from .llm import Provider, get_provider
from .retrieval import Retriever
from .schemas import Source


@dataclass
class Services:
    settings: Settings
    store: Store
    embedder: Embedder
    retriever: Retriever
    provider: Provider

    @classmethod
    def create(cls, settings: Settings) -> "Services":
        store = Store(settings.db_path)
        embedder = Embedder(settings)
        return cls(settings, store, embedder, Retriever(store, embedder), get_provider(settings))

    def ingest(self, filename: str, data: bytes) -> str:
        parsed = parse_file(filename, data)
        chunks = chunk_pages(parsed.pages, self.settings.chunk_size, self.settings.chunk_overlap)
        embeddings = self.embedder.embed_documents([text for _, text in chunks])
        return self.store.add_document(filename, len(parsed.pages), len(data), chunks, embeddings)

    def find_sources(self, question: str, document_ids: list[str] | None) -> list[Source]:
        hits = self.retriever.search(question, self.settings.top_k, document_ids)
        return [
            Source(
                index=i,
                document_id=h.chunk.document_id,
                filename=h.chunk.filename,
                page=h.chunk.page,
                text=h.chunk.text,
                score=h.score,
            )
            for i, h in enumerate(hits, start=1)
        ]
