import asyncio

import pytest

from app.gateway import GatewayError, StreamStart
from app.gateway.providers import ProviderError, parse_duration
from app.gateway.router import LONG_COOLDOWN_SECONDS, cooldown_for
from tests import fakes

MESSAGES = [{"role": "user", "content": "hi"}]


async def collect(stream):
    start, text = None, ""
    async for item in stream:
        if isinstance(item, StreamStart):
            start = item
        else:
            text += item
    return start, text


async def test_complete_uses_first_healthy_provider(make_gateway):
    gw = make_gateway()
    result = await gw.complete(MESSAGES)
    assert (result.provider, result.model, result.fallbacks, result.cached) == ("alpha", "main", 0, False)
    assert result.text == "Hello world"


async def test_complete_falls_back_on_error(make_gateway):
    gw = make_gateway()
    fakes.SCRIPTS["alpha:main"] = fakes.Script(error=fakes.rate_limited("alpha"))
    result = await gw.complete(MESSAGES)
    assert result.provider == "beta"
    assert result.fallbacks == 1


async def test_backup_model_of_same_provider_is_tried_first(make_gateway):
    gw = make_gateway(models={"alpha": ("big", "small")})
    fakes.SCRIPTS["alpha:big"] = fakes.Script(error=fakes.rate_limited("alpha", 3))
    result = await gw.complete(MESSAGES)
    assert (result.provider, result.model) == ("alpha", "small")


async def test_planner_uses_fast_model(make_gateway):
    gw = make_gateway()
    result = await gw.complete(MESSAGES, fast=True)
    assert result.model == "fast"


async def test_preferred_provider_goes_first(make_gateway):
    gw = make_gateway()
    result = await gw.complete(MESSAGES, preferred="gamma")
    assert result.provider == "gamma"


async def test_unknown_preferred_provider_is_ignored(make_gateway):
    gw = make_gateway()
    result = await gw.complete(MESSAGES, preferred="nope")
    assert result.provider == "alpha"


async def test_auth_failure_cools_down_whole_provider(make_gateway):
    gw = make_gateway(models={"alpha": ("big", "small")})
    fakes.SCRIPTS["alpha:big"] = fakes.Script(error=fakes.auth_error("alpha"))
    await gw.complete(MESSAGES, use_cache=False)
    chain = [t.key for t in gw.chain(None)]
    assert chain[:2] == ["beta:main", "gamma:main"]
    assert set(chain[2:]) == {"alpha:big", "alpha:small"}
    assert not next(s for s in gw.status() if s["id"] == "alpha")["healthy"]


async def test_cooling_targets_are_still_tried_last(make_gateway):
    gw = make_gateway(names=("alpha",))
    fakes.SCRIPTS["alpha:main"] = fakes.Script(error=fakes.rate_limited("alpha", 5))
    with pytest.raises(GatewayError):
        await gw.complete(MESSAGES, use_cache=False)
    fakes.SCRIPTS["alpha:main"] = fakes.Script()
    result = await gw.complete(MESSAGES, use_cache=False)
    assert result.provider == "alpha"


async def test_all_providers_failing_raises_with_attempts(make_gateway):
    gw = make_gateway()
    for name in ("alpha", "beta", "gamma"):
        fakes.SCRIPTS[f"{name}:main"] = fakes.Script(error=ProviderError(name, "server", "down", 503))
    with pytest.raises(GatewayError) as info:
        await gw.complete(MESSAGES)
    assert [a["provider"] for a in info.value.attempts] == ["alpha", "beta", "gamma"]


async def test_empty_completion_triggers_fallback(make_gateway):
    gw = make_gateway()
    fakes.SCRIPTS["alpha:main"] = fakes.Script(tokens=[])
    result = await gw.complete(MESSAGES)
    assert result.provider == "beta"


async def test_complete_cache_hit(make_gateway):
    gw = make_gateway()
    await gw.complete(MESSAGES)
    second = await gw.complete(MESSAGES)
    assert second.cached
    assert fakes.SCRIPTS["alpha:main"].calls == 1


async def test_stream_happy_path(make_gateway):
    gw = make_gateway()
    start, text = await collect(gw.stream(MESSAGES))
    assert (start.provider, start.fallbacks, start.cached) == ("alpha", 0, False)
    assert text == "Hello world"


async def test_stream_falls_back_before_first_token(make_gateway):
    gw = make_gateway()
    fakes.SCRIPTS["alpha:main"] = fakes.Script(error=ProviderError("alpha", "server", "boom", 500))
    start, text = await collect(gw.stream(MESSAGES))
    assert start.provider == "beta"
    assert start.fallbacks == 1
    assert text == "Hello world"


async def test_stream_first_token_timeout_falls_back(make_gateway):
    gw = make_gateway(llm_first_token_timeout_seconds=0.05)
    fakes.SCRIPTS["alpha:main"] = fakes.Script(delay=0.5)
    start, _ = await collect(gw.stream(MESSAGES))
    assert start.provider == "beta"


async def test_stream_interrupted_after_tokens_raises(make_gateway):
    gw = make_gateway()
    fakes.SCRIPTS["alpha:main"] = fakes.Script(
        tokens=["a", "b", "c"], error=ProviderError("alpha", "server", "cut", 500), error_after=2
    )
    with pytest.raises(GatewayError):
        await collect(gw.stream(MESSAGES))
    assert fakes.SCRIPTS.get("beta:main") is None


async def test_stream_cache_replay(make_gateway):
    gw = make_gateway()
    await collect(gw.stream(MESSAGES))
    start, text = await collect(gw.stream(MESSAGES))
    assert start.cached
    assert text == "Hello world"
    assert fakes.SCRIPTS["alpha:main"].calls == 1


async def test_concurrent_streams_are_isolated(make_gateway):
    gw = make_gateway()
    results = await asyncio.gather(
        *[collect(gw.stream([{"role": "user", "content": f"q{i}"}], use_cache=False)) for i in range(20)]
    )
    assert all(text == "Hello world" for _, text in results)


@pytest.mark.parametrize(
    "value,expected",
    [("1.5", 1.5), ("577ms", 0.577), ("7.66s", 7.66), ("1m2.5s", 62.5), ("2h", 7200), (None, None), ("soon", None)],
)
def test_parse_duration(value, expected):
    assert parse_duration(value) == (pytest.approx(expected) if expected is not None else None)


def test_cooldown_policy():
    config = fakes.settings(llm_cooldown_seconds=30)
    assert cooldown_for(fakes.auth_error("a"), config) == LONG_COOLDOWN_SECONDS
    assert cooldown_for(ProviderError("a", "billing", "x", 400), config) == LONG_COOLDOWN_SECONDS
    assert cooldown_for(fakes.rate_limited("a", 0.2), config) == 2.0
    assert cooldown_for(fakes.rate_limited("a", 12), config) == 12
    assert cooldown_for(fakes.rate_limited("a", 999), config) == 30
    assert cooldown_for(fakes.rate_limited("a"), config) == 30
    assert cooldown_for(ProviderError("a", "bad_request", "x", 400), config) == 0
    assert cooldown_for(TimeoutError(), config) > 0


async def test_last_target_gets_full_timeout(make_gateway):
    gw = make_gateway(names=("alpha", "beta"), llm_first_token_timeout_seconds=0.05, llm_timeout_seconds=2)
    fakes.SCRIPTS["alpha:main"] = fakes.Script(error=fakes.rate_limited("alpha", 30))
    fakes.SCRIPTS["beta:main"] = fakes.Script(delay=0.2)
    start, text = await collect(gw.stream(MESSAGES, use_cache=False))
    assert start.provider == "beta" and text == "Hello world"


async def test_second_chance_after_short_rate_limit(make_gateway):
    gw = make_gateway(names=("alpha",))

    class Flaky(fakes.Script):
        def __init__(self):
            super().__init__()
            self.error = fakes.rate_limited("alpha", 0.1)

    script = Flaky()
    fakes.SCRIPTS["alpha:main"] = script
    original = fakes.FakeProvider.complete

    async def recover(self, http, model, request):
        if script.calls >= 1:
            script.error = None
        return await original(self, http, model, request)

    fakes.FakeProvider.complete = recover
    try:
        result = await gw.complete(MESSAGES, use_cache=False)
    finally:
        fakes.FakeProvider.complete = original
    assert result.provider == "alpha"
    assert script.calls == 2


async def test_no_second_chance_for_long_rate_limits(make_gateway):
    gw = make_gateway(names=("alpha",))
    fakes.SCRIPTS["alpha:main"] = fakes.Script(error=fakes.rate_limited("alpha", 45))
    with pytest.raises(GatewayError):
        await gw.complete(MESSAGES, use_cache=False)
    assert fakes.SCRIPTS["alpha:main"].calls == 1
