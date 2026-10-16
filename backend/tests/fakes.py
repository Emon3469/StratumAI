import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.gateway.providers import Provider, ProviderError


@dataclass
class Script:
    tokens: list[str] = field(default_factory=lambda: ["Hello", " world"])
    error: Exception | None = None
    error_after: int | None = None
    delay: float = 0.0
    calls: int = 0


class FakeProvider(Provider):
    def script(self, model: str) -> Script:
        return SCRIPTS.setdefault(f"{self.name}:{model}", Script())

    async def complete(self, http, model: str, request: dict[str, Any]) -> str:
        script = self.script(model)
        script.calls += 1
        if script.delay:
            await asyncio.sleep(script.delay)
        if script.error:
            raise script.error
        return "".join(script.tokens)

    async def stream(self, http, model: str, request: dict[str, Any]) -> AsyncIterator[str]:
        script = self.script(model)
        script.calls += 1
        if script.delay:
            await asyncio.sleep(script.delay)
        if script.error and script.error_after is None:
            raise script.error
        for index, token in enumerate(script.tokens):
            if script.error and script.error_after == index:
                raise script.error
            yield token


SCRIPTS: dict[str, Script] = {}


def fake_provider(name: str, models: tuple[str, ...] = ("main",), fast: str = "fast") -> FakeProvider:
    return FakeProvider(name=name, label=name.title(), models=models, fast_model=fast, api_key="k", base_url="http://x")


def settings(**overrides: Any) -> Settings:
    base = dict(
        llm_fallback_order="alpha,beta,gamma",
        llm_first_token_timeout_seconds=0.5,
        llm_timeout_seconds=2,
        llm_cooldown_seconds=30,
        rate_limit_per_minute=0,
    )
    base.update(overrides)
    return Settings(**base)


def rate_limited(provider: str, retry_after: float | None = None) -> ProviderError:
    return ProviderError(provider, "rate_limit", "slow down", 429, retry_after)


def auth_error(provider: str) -> ProviderError:
    return ProviderError(provider, "auth", "bad key", 401)
