"""LangGraph agent that powers the conversational side of the Log Interaction
Screen. The agent is a standard ReAct-style loop:

    START -> agent (LLM decides whether to call a tool) -> tools -> agent -> ... -> END

The LLM is Groq's gemma2-9b-it (fast + cheap, good for tool-calling on a
narrow domain). If it fails we transparently retry with
llama-3.3-70b-versatile (see app/agent/llm.py).
"""
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from app.agent.llm import get_primary_llm, get_fallback_llm
from app.agent.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the AI Assistant embedded in an AI-first CRM's "Log HCP
Interaction" screen, used by pharmaceutical field representatives.

You can:
- Log a new interaction from a free-text description (log_interaction).
- Edit a previously logged interaction (edit_interaction).
- Look up an HCP's interaction history (get_hcp_history).
- Suggest concrete follow-up actions for a logged interaction (suggest_followups).
- Search available marketing materials / drug samples (search_materials).

Always prefer calling a tool over guessing. When a rep describes an
interaction in free text, call log_interaction with their text as raw_notes.
After logging, proactively call suggest_followups on the new interaction id
and share the suggestions. Be concise and professional; you are a life-science
domain expert.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _call_model(state: AgentState):
    llm = get_primary_llm().bind_tools(ALL_TOOLS)
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    try:
        response = llm.invoke(messages)
    except Exception:
        response = get_fallback_llm().bind_tools(ALL_TOOLS).invoke(messages)
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", _call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()


# Compiled once, reused across requests.
agent_app = build_graph()
