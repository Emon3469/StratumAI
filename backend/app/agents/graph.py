from langgraph.graph import END, START, StateGraph

from app.agents.nodes.planner import analyze_node
from app.agents.nodes.responder import refuse_node, respond_node
from app.agents.nodes.retriever import retrieve_node
from app.agents.state import AgentState


def route_after_analysis(state: AgentState) -> str:
    intent = state.get("intent")
    if intent in ("blocked", "off_topic"):
        return "refuse"
    if intent == "technical" and state.get("use_knowledge_base", True):
        return "retrieve"
    return "respond"


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("respond", respond_node)
    workflow.add_node("refuse", refuse_node)

    workflow.add_edge(START, "analyze")
    workflow.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {"refuse": "refuse", "retrieve": "retrieve", "respond": "respond"},
    )
    workflow.add_edge("retrieve", "respond")
    workflow.add_edge("respond", END)
    workflow.add_edge("refuse", END)
    return workflow.compile()


rag_agent = build_graph()
