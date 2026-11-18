import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import get_services
from ..llm import NO_SOURCES_ANSWER, detect_language
from ..schemas import ChatRequest, ChatResponse
from ..services import Services

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger(__name__)


def _answer_tokens(svc: Services, req: ChatRequest, sources) -> Iterator[str]:
    if not sources:
        yield NO_SOURCES_ANSWER[detect_language(req.question)]
        return
    yield from svc.provider.stream(req.question, sources, req.history)


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, svc: Services = Depends(get_services)):
    """Ask a question and get the full answer with its sources in one response."""
    sources = svc.find_sources(req.question, req.document_ids)
    try:
        answer = "".join(_answer_tokens(svc, req, sources)).strip()
    except Exception as e:  # bad key, quota, or a transient outage at the provider
        log.exception("LLM provider failed")
        raise HTTPException(502, f"The AI provider returned an error: {e}") from e
    return ChatResponse(answer=answer, sources=sources, provider=svc.provider.name)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream")
def chat_stream(req: ChatRequest, svc: Services = Depends(get_services)):
    """Same as POST /api/chat but streams Server-Sent Events:
    `sources` (once), then many `token` events, then `done` (or `error`)."""
    sources = svc.find_sources(req.question, req.document_ids)

    def events():
        yield _sse("sources", [s.model_dump() for s in sources])
        try:
            for token in _answer_tokens(svc, req, sources):
                yield _sse("token", token)
            yield _sse("done", {"provider": svc.provider.name})
        except Exception as e:  # surface provider errors (bad key, quota) to the UI
            log.exception("LLM provider failed")
            yield _sse("error", {"message": f"The AI provider returned an error: {e}"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
