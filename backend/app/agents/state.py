import operator
from typing import Annotated, Any, Literal, TypedDict

Intent = Literal["technical", "conversational", "off_topic", "blocked"]


class ChatTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class AgentState(TypedDict, total=False):
    question: str
    history: list[ChatTurn]
    preferred_provider: str | None
    use_knowledge_base: bool
    regenerate: bool
    intent: Intent
    search_query: str
    refusal: str | None
    sources: list[dict[str, Any]]
    context: str
    plan: Annotated[list[str], operator.add]
    answer: str
    provider: str | None
    model: str | None
    cached: bool
    fallbacks: int
