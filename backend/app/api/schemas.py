from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=12000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=40)
    provider: str | None = Field(default=None, description="auto, groq, openai, anthropic or gemini")
    use_knowledge_base: bool = True
    regenerate: bool = False

    @field_validator("message")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")
        return value

    @field_validator("provider")
    @classmethod
    def _provider(cls, value: str | None) -> str | None:
        if not value or value.lower() == "auto":
            return None
        return value.lower()


class LegacyQueryRequest(BaseModel):
    q: str = Field(min_length=1, max_length=8000)
    thread_id: str | None = None


class Source(BaseModel):
    id: int
    source: str
    source_type: str
    score: float
    snippet: str


class ChatResponse(BaseModel):
    question: str
    answer: str
    intent: str | None
    thought_process: list[str]
    status: str
    sources: list[Source]
    provider: str | None
    model: str | None
    latency_ms: int
