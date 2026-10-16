import json

import httpx
import pytest

from app.gateway.providers import Anthropic, OpenAICompatible, ProviderError, build_providers
from tests import fakes

REQUEST = {
    "messages": [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}],
    "temperature": 0.2,
    "max_tokens": 100,
    "json_mode": False,
    "timeout": 5,
}


def sse(*chunks: str) -> bytes:
    return "".join(f"data: {c}\n\n" for c in chunks).encode()


def client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def openai_like(name: str) -> OpenAICompatible:
    return OpenAICompatible(name=name, label=name, models=("m",), fast_model="m", api_key="key", base_url="https://api.test/v1")


async def test_openai_compatible_stream_parsing():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        body = sse(
            json.dumps({"choices": [{"delta": {"role": "assistant"}}]}),
            json.dumps({"choices": [{"delta": {"content": "Hel"}}]}),
            ": keep-alive",
            json.dumps({"choices": [{"delta": {"content": "lo"}}]}),
            json.dumps({"choices": []}),
            "[DONE]",
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    async with client(handler) as http:
        tokens = [t async for t in openai_like("groq").stream(http, "openai/gpt-oss-120b", REQUEST)]
    assert "".join(tokens) == "Hello"
    assert seen["auth"] == "Bearer key"
    assert seen["body"]["stream"] is True
    assert seen["body"]["reasoning_effort"] == "low"
    assert seen["body"]["max_tokens"] == 100


async def test_openai_uses_max_completion_tokens_and_json_mode():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": ' {"ok": true} '}}]})

    async with client(handler) as http:
        text = await openai_like("openai").complete(http, "gpt-4.1-mini", {**REQUEST, "json_mode": True})
    assert text == '{"ok": true}'
    assert captured["max_completion_tokens"] == 100
    assert "max_tokens" not in captured
    assert captured["response_format"] == {"type": "json_object"}
    assert "reasoning_effort" not in captured


async def test_gemini_gets_thinking_headroom():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with client(handler) as http:
        await openai_like("gemini").complete(http, "gemini-flash-lite-latest", REQUEST)
    assert captured["reasoning_effort"] == "minimal"
    assert captured["max_tokens"] == 612

    async with client(handler) as http:
        await openai_like("gemini").complete(http, "gemini-flash-latest", REQUEST)
    assert captured["reasoning_effort"] == "low"


@pytest.mark.parametrize(
    "status,body,headers,kind,retry",
    [
        (401, "invalid api key", {}, "auth", None),
        (400, "Your credit balance is too low", {}, "billing", None),
        (404, "model not found", {}, "not_found", None),
        (429, "rate limit", {"retry-after": "3"}, "rate_limit", 3.0),
        (429, "rate limit", {"x-ratelimit-reset-tokens": "1m30s"}, "rate_limit", 90.0),
        (413, "request too large", {}, "too_large", None),
        (503, "overloaded", {}, "server", None),
        (400, "bad param", {}, "bad_request", None),
    ],
)
async def test_error_classification(status, body, headers, kind, retry):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=body, headers=headers)

    async with client(handler) as http:
        with pytest.raises(ProviderError) as info:
            await openai_like("groq").complete(http, "m", REQUEST)
        assert info.value.kind == kind
        assert info.value.retry_after == retry
        with pytest.raises(ProviderError):
            [t async for t in openai_like("groq").stream(http, "m", REQUEST)]


async def test_stream_error_event_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse(json.dumps({"error": {"message": "overloaded"}})))

    async with client(handler) as http:
        with pytest.raises(ProviderError):
            [t async for t in openai_like("gemini").stream(http, "m", REQUEST)]


async def test_anthropic_stream_and_system_prompt():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        events = [
            {"type": "message_start"},
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hi"}},
            {"type": "ping"},
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " there"}},
            {"type": "message_stop"},
        ]
        body = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)
        return httpx.Response(200, content=body.encode())

    provider = Anthropic(name="anthropic", label="A", models=("claude",), fast_model="claude", api_key="key", base_url="https://a.test/v1")
    async with client(handler) as http:
        tokens = [t async for t in provider.stream(http, "claude", REQUEST)]
    assert "".join(tokens) == "Hi there"
    assert captured["headers"]["x-api-key"] == "key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["body"]["system"] == "be brief"
    assert all(m["role"] != "system" for m in captured["body"]["messages"])


async def test_anthropic_complete_joins_text_blocks():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]})

    provider = Anthropic(name="anthropic", label="A", models=("c",), fast_model="c", api_key="k", base_url="https://a.test/v1")
    async with client(handler) as http:
        assert await provider.complete(http, "c", {**REQUEST, "json_mode": True}) == "ab"


def test_build_providers_skips_missing_and_placeholder_keys():
    config = fakes.settings(
        groq_api_key="gsk_real",
        openai_api_key="YOUR_OPENAI_KEY",
        anthropic_api_key="",
        gemini_api_key=None,
        groq_backup_models="b1, b2,b1",
    )
    providers = build_providers(config)
    assert list(providers) == ["groq"]
    assert providers["groq"].models == (config.groq_model, "b1", "b2")
    assert providers["groq"].targets(fast=True)[0] == config.groq_fast_model
