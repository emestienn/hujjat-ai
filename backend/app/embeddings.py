"""Optional semantic embeddings (Gemini). Without a key, search falls back to keyword (BM25) only."""

import logging

from .config import Settings

log = logging.getLogger(__name__)


class Embedder:
    """Wraps the Gemini embedding API. `enabled` is False when no key is configured."""

    BATCH = 100

    def __init__(self, settings: Settings):
        self.model = settings.gemini_embedding_model
        self._client = None
        if settings.gemini_api_key:
            from google import genai

            self._client = genai.Client(api_key=settings.gemini_api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types

        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH):
            batch = texts[i : i + self.BATCH]
            resp = self._client.models.embed_content(
                model=self.model,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            vectors.extend(e.values for e in resp.embeddings)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]] | None:
        if not self.enabled:
            return None
        try:
            return self._embed(texts, "RETRIEVAL_DOCUMENT")
        except Exception:  # keep ingestion working even if the embedding API fails
            log.exception("Embedding documents failed; continuing with keyword search only")
            return None

    def embed_query(self, text: str) -> list[float] | None:
        if not self.enabled:
            return None
        try:
            return self._embed([text], "RETRIEVAL_QUERY")[0]
        except Exception:
            log.exception("Embedding query failed; using keyword search only")
            return None
