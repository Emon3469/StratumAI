import argparse
import asyncio
import json
import statistics
import time

import httpx

QUESTIONS = [
    "How do I create a Kubernetes CronJob that runs every 5 minutes?",
    "How does the Horizontal Pod Autoscaler decide when to scale?",
    "How do I process a work queue in parallel with a Job and Redis?",
    "What commands should I use to monitor a running Job?",
    "How do I suspend a CronJob temporarily?",
    "What is the difference between Indexed and NonIndexed Jobs?",
    "How do I set resource requests and limits for a Job container?",
    "How can I view the logs of the most recent CronJob run?",
    "What happens when a Job exceeds its backoffLimit?",
    "How do I configure HPA with a custom metric?",
]


async def ask(client: httpx.AsyncClient, url: str, question: str, ip: str) -> dict:
    started = time.perf_counter()
    result = {"question": question, "ok": False, "ttft": None, "provider": None, "model": None, "fallbacks": 0, "chars": 0}
    try:
        async with client.stream(
            "POST", f"{url}/api/chat/stream", json={"message": question}, headers={"X-Forwarded-For": ip}
        ) as response:
            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                return result
            event = None
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:])
                    if event == "token":
                        if result["ttft"] is None:
                            result["ttft"] = time.perf_counter() - started
                        result["chars"] += len(data["content"])
                    elif event == "done":
                        result.update(ok=result["chars"] > 0, provider=data["provider"], model=data["model"], fallbacks=data["fallbacks"])
                    elif event == "error":
                        result["error"] = data["message"]
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    result["total"] = time.perf_counter() - started
    return result


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=8)
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=120) as client:
        started = time.perf_counter()
        results = await asyncio.gather(
            *[ask(client, args.url, QUESTIONS[i % len(QUESTIONS)], f"10.0.0.{i}") for i in range(args.users)]
        )
        elapsed = time.perf_counter() - started

    for r in results:
        status = "OK  " if r["ok"] else "FAIL"
        ttft = f"{r['ttft']:.2f}s" if r["ttft"] else "  -  "
        print(f"{status} ttft {ttft} total {r['total']:.2f}s {r['provider']}:{r['model']} fb={r['fallbacks']} {r.get('error', '')}")
    ok = [r for r in results if r["ok"]]
    ttfts = [r["ttft"] for r in ok if r["ttft"]]
    print(f"\n{len(ok)}/{len(results)} succeeded in {elapsed:.1f}s")
    if ttfts:
        print(f"time to first token: median {statistics.median(ttfts):.2f}s, max {max(ttfts):.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
