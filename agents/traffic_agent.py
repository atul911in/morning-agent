"""
agents/traffic_agent.py
───────────────────────
Independent LangGraph ReAct agent responsible for:
  • Checking live traffic conditions on A2, A207, A220, A221, A222
    within ~2 miles of DA7 5SN, Bexleyheath
  • Summarising incidents, roadworks and alerts
  • Returning a structured TrafficReport to the supervisor graph

Traced automatically via LangSmith when LANGCHAIN_TRACING_V2=true.
"""

from __future__ import annotations

import os
from typing import TypedDict, Annotated
import operator

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

from tools.shared_tools import get_tfl_road_disruptions, get_highways_england_incidents


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class TrafficAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    traffic_report: str        # final human-readable summary
    incident_count: int        # number of active incidents found
    raw_incidents: list[str]   # raw incident strings


# ─────────────────────────────────────────────────────────────────────────────
# Tools available to this agent
# ─────────────────────────────────────────────────────────────────────────────

TRAFFIC_TOOLS = [get_tfl_road_disruptions, get_highways_england_incidents]


# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────

def _get_llm():
    """Return bound LLM. Supports OpenAI (default) or Anthropic via env var."""
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=0)
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.bind_tools(TRAFFIC_TOOLS)


# ─────────────────────────────────────────────────────────────────────────────
# Agent nodes
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Traffic Checker Agent for DA7 5SN, Bexleyheath, London.

Your job:
1. Use get_tfl_road_disruptions to check A2, A207, A220, A221, A222 for live incidents.
2. Use get_highways_england_incidents specifically on the A2 (it runs closest to DA7 5SN).
3. Analyse the results and produce a concise traffic report.

Report format (plain text, under 200 words):
- Overall status (Clear / Minor delays / Significant disruption)
- List each incident with road name, type, and impact
- Note any roadworks with expected duration if available
- If all clear, explicitly say so

Be factual and concise. Do not fabricate incidents.
"""


def agent_node(state: TrafficAgentState) -> dict:
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}


def summarise_node(state: TrafficAgentState) -> dict:
    """Extract the final text summary from the last AI message."""
    last = state["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last)

    # Pull raw incidents if available from tool results
    raw = []
    for msg in state["messages"]:
        if hasattr(msg, "content") and isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    data = block.get("content", {})
                    if isinstance(data, dict):
                        raw.extend(data.get("incidents", []))

    return {
        "traffic_report": content,
        "incident_count": len(raw),
        "raw_incidents":  raw,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build graph
# ─────────────────────────────────────────────────────────────────────────────

def build_traffic_agent() -> StateGraph:
    tool_node = ToolNode(TRAFFIC_TOOLS)

    graph = StateGraph(TrafficAgentState)

    graph.add_node("agent",     agent_node)
    graph.add_node("tools",     tool_node)
    graph.add_node("summarise", summarise_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: "summarise"},
    )
    graph.add_edge("tools",     "agent")
    graph.add_edge("summarise", END)

    return graph.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Convenience runner
# ─────────────────────────────────────────────────────────────────────────────

def run_traffic_agent() -> dict:
    """Run the traffic agent and return the final state."""
    app = build_traffic_agent()
    initial_state: TrafficAgentState = {
        "messages": [
            HumanMessage(
                content=(
                    "Check live traffic conditions within 2 miles of DA7 5SN, "
                    "Bexleyheath, London. Check roads A2, A207, A220, A221, A222. "
                    "Report all incidents, roadworks and alerts. If all clear, say so."
                )
            )
        ],
        "traffic_report": "",
        "incident_count": 0,
        "raw_incidents":  [],
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = run_traffic_agent()
    print("\n=== TRAFFIC REPORT ===")
    print(result["traffic_report"])
