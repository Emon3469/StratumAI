import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import settings

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return
    now = time.monotonic()
    bucket = _hits[client_ip(request)]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        retry_after = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)
    if len(_hits) > 10000:
        stale = [ip for ip, hits in _hits.items() if not hits or now - hits[-1] > _WINDOW_SECONDS]
        for ip in stale:
            _hits.pop(ip, None)
