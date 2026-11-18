"""LLM providers that answer a question using only the retrieved document passages.

All providers expose the same `stream(question, sources, history)` generator, so the API
layer doesn't care whether Claude, Gemini or the offline demo is answering.
"""

import math
import re
from collections.abc import Iterator
from typing import Protocol

from .config import Settings
from .retrieval import tokenize
from .schemas import ChatTurn, Source

SYSTEM_PROMPT = """You are Hujjat AI, an assistant that answers questions about the user's documents.

Rules:
1. Use ONLY the numbered sources provided. If they don't contain the answer, say so clearly
   and suggest what document might help. Never invent facts.
2. Cite every claim with the source number in square brackets, e.g. [1] or [2][3].
3. Answer in the same language as the user's question (Uzbek, Russian or English),
   even if the sources are in a different language.
4. Be concise: a short direct answer first, then details or a bulleted list if useful.
"""

NO_SOURCES_ANSWER = {
    "uz": "Yuklangan hujjatlarda bu savolga javob topilmadi. Boshqa hujjat yuklab ko‘ring yoki savolni boshqacha bering.",
    "ru": "В загруженных документах ответ на этот вопрос не найден. Попробуйте загрузить другой документ или переформулировать вопрос.",
    "en": "I couldn't find an answer to this in your documents. Try uploading another document or rephrasing the question.",
}


def detect_language(text: str) -> str:
    """Very small heuristic: Cyrillic -> ru, Uzbek markers -> uz, otherwise en."""
    if re.search(r"[а-яА-ЯёЁ]", text):
        return "ru"
    lowered = text.lower()
    uz_markers = (
        "o‘",
        "o'",
        "g‘",
        "g'",
        "sh",
        "ch",
        "qanday",
        "nima",
        "qancha",
        "qachon",
        "kim",
        "uchun",
        "bo",
        "mi?",
        "lar",
        "dagi",
        "ning",
    )
    hits = sum(1 for m in uz_markers if m in lowered)
    return "uz" if hits >= 2 else "en"


def build_context(sources: list[Source]) -> str:
    blocks = [f"[{s.index}] (file: {s.filename}, page {s.page})\n{s.text}" for s in sources]
    return "\n\n".join(blocks)


def build_user_message(question: str, sources: list[Source]) -> str:
    return f"Sources:\n\n{build_context(sources)}\n\nQuestion: {question}"


class Provider(Protocol):
    name: str

    def stream(self, question: str, sources: list[Source], history: list[ChatTurn]) -> Iterator[str]: ...


class ClaudeProvider:
    name = "claude"

    def __init__(self, settings: Settings):
        import anthropic

        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def stream(self, question, sources, history):
        messages = [{"role": t.role, "content": t.content} for t in history]
        messages.append({"role": "user", "content": build_user_message(question, sources)})
        with self.client.messages.stream(
            model=self.model, max_tokens=1024, system=SYSTEM_PROMPT, messages=messages
        ) as stream:
            yield from stream.text_stream


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: Settings):
        from google import genai

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    def stream(self, question, sources, history):
        from google.genai import types

        contents = [
            types.Content(
                role="model" if t.role == "assistant" else "user", parts=[types.Part(text=t.content)]
            )
            for t in history
        ]
        contents.append(
            types.Content(role="user", parts=[types.Part(text=build_user_message(question, sources))])
        )
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, max_output_tokens=1024),
        ):
            if chunk.text:
                yield chunk.text


def _stem(token: str) -> str:
    """Crude, language-agnostic stemming: 'retaking'/'retake' -> 'retak'."""
    return token[:5] if len(token) > 5 else token


class DemoProvider:
    """Works offline with no API key: picks the most relevant sentences from the sources.

    It is extractive (it quotes, it doesn't reason), but it lets anyone try the app and
    keeps the test suite free of network calls.
    """

    name = "demo"
    INTRO = {
        "uz": "Hujjatlaringizdan eng mos parchalar (demo rejim, AI kalitisiz):",
        "ru": "Наиболее подходящие фрагменты из ваших документов (демо-режим, без ключа AI):",
        "en": "Most relevant passages from your documents (demo mode, no AI key):",
    }

    def stream(self, question, sources, history):
        lang = detect_language(question)
        q_tokens = {_stem(t) for t in tokenize(question)}

        candidates: list[tuple[int, str, set[str]]] = []
        for s in sources:
            for sentence in re.split(r"(?<=[.!?])\s+|\n\n+", s.text):
                sentence = " ".join(sentence.split())
                if len(sentence) >= 25:
                    candidates.append((s.index, sentence, {_stem(t) for t in tokenize(sentence)}))

        # Weight rare words higher (IDF), so "retake" counts more than "exam".
        n = len(candidates) or 1
        df = {t: sum(t in toks for _, _, toks in candidates) for t in q_tokens}
        weight = {t: math.log(1 + n / df[t]) for t in q_tokens if df[t]}

        picked = [
            (sum(weight.get(t, 0) for t in q_tokens & toks), idx, sentence)
            for idx, sentence, toks in candidates
        ]
        picked = sorted((p for p in picked if p[0] > 0), key=lambda p: p[0], reverse=True)

        if not picked:
            yield NO_SOURCES_ANSWER[lang]
            return

        best = picked[0][0]
        picked = [p for p in picked if p[0] >= best * 0.6]

        yield self.INTRO[lang] + "\n\n"
        seen = set()
        for _, idx, sentence in picked[:3]:
            if sentence in seen:
                continue
            seen.add(sentence)
            # Stream word by word so the demo feels like a real model.
            yield from re.findall(r"\S+\s*", f"- {sentence} [{idx}]\n")


def get_provider(settings: Settings) -> Provider:
    match settings.resolved_provider:
        case "claude":
            return ClaudeProvider(settings)
        case "gemini":
            return GeminiProvider(settings)
        case _:
            return DemoProvider()
