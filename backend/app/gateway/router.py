import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import logfire

from app.config import Settings, settings
from app.gateway.providers import Provider, ProviderError, build_providers
from app.httpclient import http_client

LONG_COOLDOWN_SECONDS = 600.0
TRANSIENT_COOLDOWN_SECONDS = 15.0
MIN_RATE_LIMIT_COOLDOWN = 2.0
SECOND_CHANCE_MAX_WAIT = 8.0


class GatewayError(RuntimeError):
    def __init__(self, message: str, attempts: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.attempts = attempts or []


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    cached: bool
    latency_ms: int
    fallbacks: int


@dataclass
class StreamStart:
    provider: str
    model: str
    cached: bool
    fallbacks: int


@dataclass(frozen=True)
class Target:
    provider: Provider
    model: str

    @property
    def key(self) -> str:
        return f"{self.provider.name}:{self.model}"


class TTLCache:
    def __init__(self, max_size: int, ttl_seconds: int):
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.monotonic() + self._ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self._max_size:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


def cooldown_for(error: Exception, config: Settings = settings) -> float:
    if isinstance(error, ProviderError):
        if error.kind in ("auth", "billing", "not_found"):
            return LONG_COOLDOWN_SECONDS
        if error.kind == "rate_limit":
            if error.retry_after is not None:
                return min(max(error.retry_after, MIN_RATE_LIMIT_COOLDOWN), config.llm_cooldown_seconds)
            return config.llm_cooldown_seconds
        if error.kind in ("bad_request", "too_large"):
            return 0.0
    return TRANSIENT_COOLDOWN_SECONDS


def _short_error(error: Exception) -> str:
    text = str(error).replace("\n", " ") or type(error).__name__
    return f"{type(error).__name__}: {text[:200]}"


RECOVERABLE = (ProviderError, httpx.HTTPError, asyncio.TimeoutError, KeyError, ValueError, StopAsyncIteration)


class LLMGateway:
    def __init__(self, config: Settings):
        self.config = config
        self.providers = build_providers(config)
        self._cooldowns: dict[str, float] = {}
        self._cache = TTLCache(config.llm_cache_size, config.llm_cache_ttl_seconds)

    def available(self) -> list[Provider]:
        ordered = [self.providers[n] for n in self.config.fallback_order if n in self.providers]
        extras = [p for n, p in self.providers.items() if n not in self.config.fallback_order]
        return ordered + extras

    def _cooling(self, key: str, now: float | None = None) -> bool:
        return self._cooldowns.get(key, 0) > (now or time.monotonic())

    def status(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        return [
            {
                "id": p.name,
                "label": p.label,
                "model": p.model,
                "models": list(p.models),
                "healthy": any(not self._cooling(f"{p.name}:{m}", now) for m in p.models),
            }
            for p in self.available()
        ]

    def chain(self, preferred: str | None, fast: bool = False) -> list[Target]:
        providers = self.available()
        if preferred and preferred in self.providers:
            providers = [self.providers[preferred]] + [p for p in providers if p.name != preferred]
        targets = [Target(p, m) for p in providers for m in p.targets(fast)]
        now = time.monotonic()
        healthy = [t for t in targets if not self._cooling(t.key, now)]
        cooling = sorted((t for t in targets if self._cooling(t.key, now)), key=lambda t: self._cooldowns[t.key])
        return healthy + cooling

    def _mark_failure(self, target: Target, error: Exception) -> None:
        seconds = cooldown_for(error, self.config)
        if seconds <= 0:
            return
        if self._provider_wide(error):
            for model in {*target.provider.models, target.provider.fast_model}:
                self._cooldowns[f"{target.provider.name}:{model}"] = time.monotonic() + seconds
        else:
            self._cooldowns[target.key] = time.monotonic() + seconds

    def _mark_success(self, target: Target) -> None:
        self._cooldowns.pop(target.key, None)

    def reset(self) -> None:
        self._cooldowns.clear()
        self._cache.clear()

    @staticmethod
    def _cache_key(messages: list[dict[str, str]], **options: Any) -> str:
        payload = json.dumps({"m": messages, "o": options}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _provider_wide(error: Exception) -> bool:
        return isinstance(error, ProviderError) and error.kind in ("auth", "billing")

    async def _attempts(
        self,
        preferred: str | None,
        fast: bool,
        dead: set[str],
        failures: list[tuple[Target, Exception]],
    ) -> AsyncIterator[tuple[Target, bool]]:
        chain = self.chain(preferred, fast)
        for index, target in enumerate(chain):
            if target.provider.name in dead:
                continue
            remaining = [t for t in chain[index + 1 :] if t.provider.name not in dead]
            yield target, not remaining

        waits = [
            (error.retry_after, target)
            for target, error in failures
            if isinstance(error, ProviderError)
            and error.kind == "rate_limit"
            and error.retry_after is not None
            and error.retry_after <= SECOND_CHANCE_MAX_WAIT
        ]
        if waits:
            wait, target = min(waits, key=lambda item: item[0])
            logfire.info("llm.second_chance {provider}", provider=target.provider.name, model=target.model, wait=wait)
            await asyncio.sleep(wait + 0.25)
            self._cooldowns.pop(target.key, None)
            yield target, True

    def _record(
        self,
        attempts: list[dict[str, str]],
        target: Target,
        error: Exception,
        dead: set[str],
        failures: list[tuple[Target, Exception]],
    ) -> None:
        if self._provider_wide(error):
            dead.add(target.provider.name)
        failures.append((target, error))
        self._mark_failure(target, error)
        attempts.append({"provider": target.provider.name, "model": target.model, "error": _short_error(error)})
        logfire.warn("llm.fallback {provider}", provider=target.provider.name, model=target.model, error=_short_error(error))

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        preferred: str | None = None,
        fast: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 512,
        json_mode: bool = False,
        use_cache: bool = True,
        timeout: float | None = None,
    ) -> Completion:
        started = time.perf_counter()
        key = self._cache_key(messages, fast=fast, json=json_mode, max=max_tokens, t=temperature)
        if use_cache and (hit := self._cache.get(key)):
            provider, model, text = hit
            return Completion(text, provider, model, True, int((time.perf_counter() - started) * 1000), 0)

        request = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "json_mode": json_mode,
            "timeout": timeout or self.config.llm_timeout_seconds,
        }
        attempts: list[dict[str, str]] = []
        dead: set[str] = set()
        failures: list[tuple[Target, Exception]] = []
        async for target, _ in self._attempts(preferred, fast, dead, failures):
            try:
                with logfire.span("llm.complete {provider}", provider=target.provider.name, model=target.model):
                    text = await target.provider.complete(http_client(), target.model, request)
                if not text:
                    raise ProviderError(target.provider.name, "empty", "empty completion")
                self._mark_success(target)
                if use_cache:
                    self._cache.set(key, (target.provider.name, target.model, text))
                latency = int((time.perf_counter() - started) * 1000)
                return Completion(text, target.provider.name, target.model, False, latency, len(attempts))
            except RECOVERABLE as error:
                self._record(attempts, target, error, dead, failures)

        raise GatewayError("All language model providers failed.", attempts)

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        preferred: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        use_cache: bool = True,
    ) -> AsyncIterator[StreamStart | str]:
        max_tokens = max_tokens or self.config.llm_max_output_tokens
        key = self._cache_key(messages, stream=True, max=max_tokens, t=temperature, p=preferred)
        if use_cache and (hit := self._cache.get(key)):
            provider, model, text = hit
            yield StreamStart(provider, model, True, 0)
            for i in range(0, len(text), 24):
                yield text[i : i + 24]
                await asyncio.sleep(0.004)
            return

        request = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "json_mode": False,
            "timeout": httpx.Timeout(self.config.llm_timeout_seconds, connect=5.0),
        }
        attempts: list[dict[str, str]] = []
        dead: set[str] = set()
        failures: list[tuple[Target, Exception]] = []
        async for target, is_last in self._attempts(preferred, False, dead, failures):
            emitted = False
            parts: list[str] = []
            started = time.perf_counter()
            first_token_timeout = (
                self.config.llm_timeout_seconds if is_last else self.config.llm_first_token_timeout_seconds
            )
            iterator = target.provider.stream(http_client(), target.model, request).__aiter__()
            try:
                first = await asyncio.wait_for(iterator.__anext__(), timeout=first_token_timeout)
                logfire.info(
                    "llm.first_token {provider}",
                    provider=target.provider.name,
                    model=target.model,
                    ttft_ms=int((time.perf_counter() - started) * 1000),
                )
                self._mark_success(target)
                yield StreamStart(target.provider.name, target.model, False, len(attempts))
                emitted = True
                parts.append(first)
                yield first
                async for delta in iterator:
                    parts.append(delta)
                    yield delta
                if use_cache and parts:
                    self._cache.set(key, (target.provider.name, target.model, "".join(parts)))
                return
            except RECOVERABLE as error:
                if emitted:
                    logfire.error("llm.stream_interrupted", provider=target.provider.name, error=_short_error(error))
                    raise GatewayError("The response stream was interrupted.") from error
                self._record(attempts, target, error, dead, failures)
            finally:
                await _close(iterator)

        raise GatewayError("All language model providers failed.", attempts)


async def _close(iterator: Any) -> None:
    closer = getattr(iterator, "aclose", None)
    if closer:
        try:
            await closer()
        except Exception:
            pass


gateway = LLMGateway(settings)
