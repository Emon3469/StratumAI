from dataclasses import dataclass

import logfire

from app.config import settings
from app.guardrails.policies import MAX_INPUT_CHARS, RESPONSES, matches_injection
from app.httpclient import http_client


@dataclass
class GuardResult:
    blocked: bool
    category: str | None = None
    message: str | None = None
    score: float | None = None

    @classmethod
    def allow(cls, score: float | None = None) -> "GuardResult":
        return cls(blocked=False, score=score)

    @classmethod
    def block(cls, category: str, score: float | None = None) -> "GuardResult":
        return cls(blocked=True, category=category, message=RESPONSES[category], score=score)


async def _classifier_score(text: str) -> float | None:
    if not settings.groq_api_key:
        return None
    try:
        response = await http_client().post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={"model": settings.groq_guard_model, "messages": [{"role": "user", "content": text[:2000]}]},
            timeout=2,
        )
        response.raise_for_status()
        return float((response.json()["choices"][0]["message"].get("content") or "0").strip())
    except Exception as error:
        logfire.warn("guard.classifier_unavailable", error=str(error)[:160])
        return None


async def check_input(text: str) -> GuardResult:
    if not settings.guard_enabled:
        return GuardResult.allow()
    if len(text) > MAX_INPUT_CHARS:
        return GuardResult.block("too_long")
    if matches_injection(text):
        logfire.info("guard.blocked", category="injection", layer="pattern")
        return GuardResult.block("injection", 1.0)

    score = await _classifier_score(text)
    if score is not None and score >= settings.guard_threshold:
        logfire.info("guard.blocked", category="injection", layer="classifier", score=score)
        return GuardResult.block("injection", score)
    return GuardResult.allow(score)
