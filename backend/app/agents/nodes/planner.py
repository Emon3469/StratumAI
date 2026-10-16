import asyncio
import json
import re

import logfire

from app.agents.nodes.events import status
from app.agents.prompts import PLANNER_SYSTEM
from app.agents.state import AgentState
from app.config import settings
from app.gateway import gateway
from app.guardrails import RESPONSES, check_input

VALID_INTENTS = {"technical", "conversational", "off_topic"}
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_SMALL_TALK_RE = re.compile(
    r"^\s*(hi|hello|hey|yo|thanks|thank you|thx|good (morning|afternoon|evening)|bye|goodbye|who are you|"
    r"what (can|do) you (do|help( me)? with)|how are you)\b[\s\w,!?.']{0,30}$",
    re.IGNORECASE,
)


def heuristic_plan(question: str) -> tuple[str, str]:
    if _SMALL_TALK_RE.match(question):
        return "conversational", ""
    return "technical", question


def _parse_plan(raw: str, question: str) -> tuple[str, str]:
    match = _JSON_RE.search(raw)
    try:
        data = json.loads(match.group(0) if match else raw)
    except (json.JSONDecodeError, AttributeError):
        return "technical", question
    intent = str(data.get("intent", "technical")).strip().lower()
    if intent not in VALID_INTENTS:
        intent = "technical"
    query = str(data.get("query") or "").strip() or question
    return intent, query


def _transcript(state: AgentState) -> str:
    lines = []
    for turn in state.get("history", [])[-6:]:
        speaker = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {turn['content'][:600]}")
    lines.append(f"User (latest): {state['question']}")
    return "\n".join(lines)


async def _plan(state: AgentState) -> tuple[str, str]:
    question = state["question"]
    try:
        completion = await asyncio.wait_for(
            gateway.complete(
                [
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": _transcript(state)},
                ],
                fast=True,
                json_mode=True,
                max_tokens=300,
                timeout=settings.planner_budget_seconds,
            ),
            timeout=settings.planner_budget_seconds,
        )
        return _parse_plan(completion.text, question)
    except Exception as error:
        logfire.warn("planner.degraded", error=str(error)[:160] or type(error).__name__)
        return heuristic_plan(question)


async def analyze_node(state: AgentState) -> dict:
    status("analyzing", "Understanding your question")
    guard_result, (intent, query) = await asyncio.gather(check_input(state["question"]), _plan(state))

    if guard_result.blocked:
        return {
            "intent": "blocked",
            "refusal": guard_result.message,
            "plan": [f"Guardrail: blocked ({guard_result.category})"],
        }

    plan = ["Guardrail: passed", f"Intent: {intent}"]
    if intent == "off_topic":
        return {"intent": intent, "refusal": RESPONSES["off_topic"], "plan": plan}
    if intent == "technical":
        plan.append(f"Search query: {query}")
    return {"intent": intent, "search_query": query, "plan": plan}
