import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")


class ProviderError(Exception):
    def __init__(
        self,
        provider: str,
        kind: str,
        message: str,
        status: int | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(f"{provider} {kind}: {message}")
        self.provider = provider
        self.kind = kind
        self.status = status
        self.retry_after = retry_after


def parse_duration(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        pass
    total = 0.0
    matched = False
    for amount, unit in _DURATION_RE.findall(value):
        matched = True
        total += float(amount) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total if matched else None


def classify(provider: str, response: httpx.Response, body: str) -> ProviderError:
    status = response.status_code
    lowered = body.lower()
    retry_after = None
    if status in (401, 403):
        kind = "auth"
    elif status == 402 or "credit balance" in lowered or "billing" in lowered or "insufficient_quota" in lowered:
        kind = "billing"
    elif status == 404:
        kind = "not_found"
    elif status == 429:
        kind = "rate_limit"
        retry_after = parse_duration(response.headers.get("retry-after")) or parse_duration(
            response.headers.get("x-ratelimit-reset-tokens")
        )
    elif status == 413:
        kind = "too_large"
    elif status >= 500:
        kind = "server"
    else:
        kind = "bad_request"
    return ProviderError(provider, kind, body[:300], status, retry_after)


def _split(value: str | None) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    models: tuple[str, ...]
    fast_model: str
    api_key: str
    base_url: str

    @property
    def model(self) -> str:
        return self.models[0]

    def targets(self, fast: bool) -> list[str]:
        if fast:
            return [self.fast_model] + [m for m in self.models if m != self.fast_model][-1:]
        return list(self.models)

    async def complete(self, http: httpx.AsyncClient, model: str, request: dict[str, Any]) -> str:
        raise NotImplementedError

    def stream(self, http: httpx.AsyncClient, model: str, request: dict[str, Any]) -> AsyncIterator[str]:
        raise NotImplementedError


class OpenAICompatible(Provider):
    def _payload(self, model: str, request: dict[str, Any], stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": request["messages"],
            "temperature": request["temperature"],
            "stream": stream,
        }
        if self.name == "openai":
            payload["max_completion_tokens"] = request["max_tokens"]
        elif self.name == "gemini":
            payload["max_tokens"] = request["max_tokens"] + 512
            payload["reasoning_effort"] = "minimal" if "lite" in model else "low"
        else:
            payload["max_tokens"] = request["max_tokens"]
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"
        if request.get("json_mode"):
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def complete(self, http: httpx.AsyncClient, model: str, request: dict[str, Any]) -> str:
        response = await http.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(model, request, stream=False),
            timeout=request["timeout"],
        )
        if response.status_code >= 400:
            raise classify(self.name, response, response.text)
        data = response.json()
        return (data["choices"][0]["message"].get("content") or "").strip()

    async def stream(self, http: httpx.AsyncClient, model: str, request: dict[str, Any]) -> AsyncIterator[str]:
        async with http.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(model, request, stream=True),
            timeout=request["timeout"],
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", "ignore")
                raise classify(self.name, response, body)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if chunk.get("error"):
                    raise ProviderError(self.name, "server", str(chunk["error"])[:300])
                choices = chunk.get("choices") or []
                if choices:
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        yield delta


class Anthropic(Provider):
    def _payload(self, model: str, request: dict[str, Any], stream: bool) -> dict[str, Any]:
        system_parts = [m["content"] for m in request["messages"] if m["role"] == "system"]
        messages = [m for m in request["messages"] if m["role"] != "system"]
        if request.get("json_mode"):
            system_parts.append("Respond with a single valid JSON object and nothing else.")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request["max_tokens"],
            "temperature": min(request["temperature"], 1.0),
            "stream": stream,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        return payload

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def complete(self, http: httpx.AsyncClient, model: str, request: dict[str, Any]) -> str:
        response = await http.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=self._payload(model, request, stream=False),
            timeout=request["timeout"],
        )
        if response.status_code >= 400:
            raise classify(self.name, response, response.text)
        blocks = response.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()

    async def stream(self, http: httpx.AsyncClient, model: str, request: dict[str, Any]) -> AsyncIterator[str]:
        async with http.stream(
            "POST",
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=self._payload(model, request, stream=True),
            timeout=request["timeout"],
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", "ignore")
                raise classify(self.name, response, body)
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                kind = event.get("type")
                if kind == "content_block_delta":
                    text = (event.get("delta") or {}).get("text")
                    if text:
                        yield text
                elif kind == "error":
                    raise ProviderError(self.name, "server", str(event.get("error"))[:300])
                elif kind == "message_stop":
                    break


def build_providers(settings: Settings) -> dict[str, Provider]:
    providers: dict[str, Provider] = {}

    if settings.groq_api_key:
        providers["groq"] = OpenAICompatible(
            name="groq",
            label="Groq",
            models=tuple(dict.fromkeys([settings.groq_model, *_split(settings.groq_backup_models)])),
            fast_model=settings.groq_fast_model,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    if settings.openai_api_key:
        providers["openai"] = OpenAICompatible(
            name="openai",
            label="OpenAI",
            models=(settings.openai_model,),
            fast_model=settings.openai_fast_model or settings.openai_model,
            api_key=settings.openai_api_key,
            base_url="https://api.openai.com/v1",
        )

    if settings.anthropic_api_key:
        providers["anthropic"] = Anthropic(
            name="anthropic",
            label="Anthropic",
            models=(settings.anthropic_model,),
            fast_model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            base_url="https://api.anthropic.com/v1",
        )

    if settings.gemini_api_key:
        providers["gemini"] = OpenAICompatible(
            name="gemini",
            label="Google Gemini",
            models=tuple(dict.fromkeys([settings.gemini_model, *_split(settings.gemini_backup_models)])),
            fast_model=settings.gemini_model,
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        )

    return providers
