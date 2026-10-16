import asyncio

import httpx

_client: httpx.AsyncClient | None = None
_loop: asyncio.AbstractEventLoop | None = None


def http_client() -> httpx.AsyncClient:
    global _client, _loop
    loop = asyncio.get_running_loop()
    if _client is None or _client.is_closed or _loop is not loop:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=120),
        )
        _loop = loop
    return _client


async def close_http_client() -> None:
    global _client, _loop
    if _client is not None and not _client.is_closed and _loop is asyncio.get_running_loop():
        await _client.aclose()
    _client = None
    _loop = None
