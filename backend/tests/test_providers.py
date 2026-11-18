"""Check that the Claude and Gemini providers send the right request, using stub clients."""

from contextlib import contextmanager
from types import SimpleNamespace

from app.config import Settings
from app.llm import SYSTEM_PROMPT, ClaudeProvider, GeminiProvider, get_provider
from app.schemas import ChatTurn, Source

SOURCES = [Source(index=1, document_id="d", filename="f.pdf", page=2, text="Fee is 5.", score=1.0)]
HISTORY = [ChatTurn(role="user", content="hi"), ChatTurn(role="assistant", content="hello")]


def test_auto_provider_selection():
    assert get_provider(Settings(_env_file=None)).name == "demo"
    assert get_provider(Settings(_env_file=None, anthropic_api_key="k")).name == "claude"
    assert get_provider(Settings(_env_file=None, gemini_api_key="k")).name == "gemini"
    both = Settings(_env_file=None, anthropic_api_key="k", gemini_api_key="k", llm_provider="gemini")
    assert get_provider(both).name == "gemini"


def test_claude_request_shape():
    sent = {}

    @contextmanager
    def stream(**kwargs):
        sent.update(kwargs)
        yield SimpleNamespace(text_stream=iter(["The fee ", "is 5 [1]."]))

    p = ClaudeProvider(Settings(_env_file=None, anthropic_api_key="k"))
    p.client = SimpleNamespace(messages=SimpleNamespace(stream=stream))

    assert "".join(p.stream("What is the fee?", SOURCES, HISTORY)) == "The fee is 5 [1]."
    assert sent["system"] == SYSTEM_PROMPT
    assert [m["role"] for m in sent["messages"]] == ["user", "assistant", "user"]
    assert "[1] (file: f.pdf, page 2)" in sent["messages"][-1]["content"]


def test_gemini_request_shape():
    sent = {}

    def generate_content_stream(**kwargs):
        sent.update(kwargs)
        return iter([SimpleNamespace(text="5 "), SimpleNamespace(text=None), SimpleNamespace(text="[1]")])

    p = GeminiProvider(Settings(_env_file=None, gemini_api_key="k"))
    p.client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate_content_stream))

    assert "".join(p.stream("fee?", SOURCES, HISTORY)) == "5 [1]"
    assert [c.role for c in sent["contents"]] == ["user", "model", "user"]
    assert sent["config"].system_instruction == SYSTEM_PROMPT
