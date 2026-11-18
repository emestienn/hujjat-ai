import json


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "provider": "demo", "semantic_search": False, "documents": 0}


def test_upload_list_delete(client, uploaded):
    assert uploaded["filename"] == "student-handbook.pdf"
    assert uploaded["pages"] == 4
    assert uploaded["chunks"] >= 4

    docs = client.get("/api/documents").json()
    assert [d["id"] for d in docs] == [uploaded["id"]]

    assert client.delete(f"/api/documents/{uploaded['id']}").status_code == 204
    assert client.get("/api/documents").json() == []
    assert client.delete(f"/api/documents/{uploaded['id']}").status_code == 404


def test_upload_rejects_unsupported_type(client):
    r = client.post("/api/documents", files={"file": ("x.exe", b"MZ...", "application/octet-stream")})
    assert r.status_code == 415


def test_upload_rejects_empty_file(client):
    r = client.post("/api/documents", files={"file": ("x.txt", b"", "text/plain")})
    assert r.status_code == 400


def test_chat_returns_answer_with_cited_page(client, uploaded):
    r = client.post("/api/chat", json={"question": "What is the retake fee for a failed exam?"})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "demo"
    assert body["sources"][0]["page"] == 2
    assert "500,000 UZS" in body["answer"]
    assert "[1]" in body["answer"]


def test_chat_in_uzbek(client, uploaded):
    body = client.post("/api/chat", json={"question": "Kutubxona soat nechagacha ishlaydi?"}).json()
    assert body["sources"][0]["page"] == 3
    assert "21:00" in body["answer"]
    assert body["answer"].startswith("Hujjatlaringizdan")


def test_chat_without_documents_says_not_found(client):
    body = client.post("/api/chat", json={"question": "Сколько стоит обучение?"}).json()
    assert body["sources"] == []
    assert body["answer"].startswith("В загруженных документах")


def test_chat_validation(client):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422


def test_chat_reports_provider_errors(client, uploaded):
    def boom(question, sources, history):
        def gen():
            raise RuntimeError("quota exceeded")
            yield  # makes this a generator, matching Provider.stream's contract

        return gen()

    client.app.state.services.provider.stream = boom
    r = client.post("/api/chat", json={"question": "What is the retake fee for a failed exam?"})
    assert r.status_code == 502
    assert "quota exceeded" in r.json()["detail"]


def test_stream_sends_sources_tokens_done(client, uploaded):
    with client.stream(
        "POST", "/api/chat/stream", json={"question": "When is the first instalment due?"}
    ) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        raw = "".join(r.iter_text())

    events = []
    for block in raw.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))

    names = [e for e, _ in events]
    assert names[0] == "sources" and names[-1] == "done"
    assert names.count("token") > 3
    answer = "".join(d for e, d in events if e == "token")
    assert "15 September" in answer
