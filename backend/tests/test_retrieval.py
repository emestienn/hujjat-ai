import numpy as np

from app.db import Store
from app.llm import detect_language
from app.retrieval import Retriever, tokenize


class FakeEmbedder:
    """Maps text to a tiny 'semantic' vector so we can test the hybrid path offline."""

    enabled = True
    TOPICS = {"money": ("fee", "tuition", "pay", "payment", "cost"), "books": ("library", "book")}

    def _vec(self, text):
        t = text.lower()
        return [float(any(w in t for w in words)) for words in self.TOPICS.values()] + [0.1]

    def embed_query(self, text):
        return self._vec(text)

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]


class NoEmbedder:
    enabled = False

    def embed_query(self, text):
        return None


def make_store(tmp_path, embedder=None):
    store = Store(tmp_path / "t.db")
    chunks = [
        (1, "Tuition is 24,000,000 UZS and is paid in two instalments."),
        (2, "The library is open from 08:00 to 21:00 and lends 5 books."),
        (3, "Stipendiya oyiga 1 200 000 so‘m miqdorida beriladi."),
    ]
    embs = embedder.embed_documents([c for _, c in chunks]) if embedder else None
    doc_a = store.add_document("a.pdf", 3, 100, chunks, embs)
    doc_b = store.add_document(
        "b.txt",
        1,
        10,
        [(1, "Unrelated text about weather in Tashkent.")],
        embedder.embed_documents(["weather"]) if embedder else None,
    )
    return store, doc_a, doc_b


def test_tokenize_normalises_uzbek_apostrophes():
    assert tokenize("So‘m va soʻm, O'zbekiston!") == ["so'm", "va", "so'm", "o'zbekiston"]


def test_keyword_search_finds_exact_terms(tmp_path):
    store, doc_a, _ = make_store(tmp_path)
    hits = Retriever(store, NoEmbedder()).search("library hours", k=2)
    assert hits[0].chunk.page == 2
    assert hits[0].score == 1.0


def test_uzbek_query_matches_uzbek_text(tmp_path):
    store, *_ = make_store(tmp_path)
    hits = Retriever(store, NoEmbedder()).search("stipendiya qancha so'm?", k=1)
    assert hits and "Stipendiya" in hits[0].chunk.text


def test_semantic_search_finds_paraphrase(tmp_path):
    emb = FakeEmbedder()
    store, *_ = make_store(tmp_path, emb)
    # "cost" never appears in the text, so only the embedding side can find the tuition chunk.
    hits = Retriever(store, emb).search("how much does it cost?", k=1)
    assert hits[0].chunk.page == 1


def test_filter_by_document(tmp_path):
    store, doc_a, doc_b = make_store(tmp_path)
    hits = Retriever(store, NoEmbedder()).search("weather Tashkent", k=5, document_ids=[doc_a])
    assert all(h.chunk.document_id == doc_a for h in hits)


def test_cache_refreshes_after_delete(tmp_path):
    store, doc_a, _ = make_store(tmp_path)
    r = Retriever(store, NoEmbedder())
    assert r.search("library")
    store.delete_document(doc_a)
    assert r.search("library") == []


def test_embeddings_round_trip(tmp_path):
    store, *_ = make_store(tmp_path, FakeEmbedder())
    assert all(isinstance(c.embedding, np.ndarray) for c in store.all_chunks())


def test_detect_language():
    assert detect_language("Сколько стоит обучение?") == "ru"
    assert detect_language("Stipendiya olish uchun nima qilish kerak?") == "uz"
    assert detect_language("How much is the tuition?") == "en"
