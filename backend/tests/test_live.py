import json

import httpx
import pytest

from app.gateway import gateway
from app.main import app

pytestmark = pytest.mark.live

GOLDEN = [
    ("How do you start Redis for a Kubernetes work queue?", "redis-pod.yaml"),
    ("How do I create a CronJob that runs every 5 minutes?", "*/5"),
    ("What does the Horizontal Pod Autoscaler use to decide when to scale?", "cpu"),
]


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(":", 1) for line in block.split("\n") if ":" in line)
        out.append((lines["event"].strip(), json.loads(lines["data"])))
    return out


@pytest.fixture
async def api():
    gateway.reset()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://live", timeout=90) as client:
        yield client


@pytest.mark.parametrize("question,expected", GOLDEN)
async def test_grounded_answers(api, question, expected):
    response = await api.post("/api/chat/stream", json={"message": question})
    stream = events(response.text)
    done = stream[-1]
    assert done[0] == "done", stream[-1]
    answer = "".join(d["content"] for n, d in stream if n == "token")
    sources = next(d["items"] for n, d in stream if n == "sources")
    assert sources, "no sources retrieved"
    assert expected.lower() in answer.lower(), answer[:400]
    assert done[1]["ttft_ms"] < 15000


@pytest.mark.parametrize("provider", ["groq", "openai", "anthropic", "gemini"])
async def test_each_provider_can_answer(api, provider):
    if provider not in gateway.providers:
        pytest.skip(f"{provider} not configured")
    response = await api.post(
        "/api/chat/stream",
        json={"message": "In one sentence, what is a Kubernetes Job?", "provider": provider, "use_knowledge_base": False},
    )
    stream = events(response.text)
    assert stream[-1][0] == "done"
    assert "".join(d["content"] for n, d in stream if n == "token").strip()


async def test_follow_up_uses_history(api):
    history = [
        {"role": "user", "content": "How do I create a CronJob?"},
        {"role": "assistant", "content": "Use kind: CronJob with a schedule field."},
    ]
    response = await api.post("/api/chat/stream", json={"message": "How do I suspend it?", "history": history})
    stream = events(response.text)
    answer = "".join(d["content"] for n, d in stream if n == "token").lower()
    assert "suspend" in answer
