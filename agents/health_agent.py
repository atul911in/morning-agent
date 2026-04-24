"""
agents/health_agent.py
──────────────────────
Independent LangGraph ReAct agent responsible for:
  - Querying Samsung SmartThings for Galaxy Watch device data
  - Reporting battery level, connectivity, and any available sensor data
  - Returning a structured HealthReport to the supervisor graph

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

from tools.shared_tools import (
    list_smartthings_devices,
    get_smartthings_device_status,
    get_smartthings_device_health,
    get_smartthings_device_history,
)


class HealthAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    health_report: str
    device_count: int
    watch_online: bool


HEALTH_TOOLS = [
    list_smartthings_devices,
    get_smartthings_device_status,
    get_smartthings_device_health,
    get_smartthings_device_history,
]


def _get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=0)
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.bind_tools(HEALTH_TOOLS)


SYSTEM_PROMPT = """You are the Health & Wearable Agent for the Morning Briefing system.

Your job:
1. Call list_smartthings_devices to find all connected Samsung devices (Galaxy Watch, Galaxy Ring, phone, etc.)
2. For each wearable device found (watch, ring, band), call get_smartthings_device_health to check connectivity.
3. For each wearable device found, call get_smartthings_device_status to get battery level and any sensor data.
4. Optionally call get_smartthings_device_history for recent events on the wearable.
5. Produce a clear health/wearable status report.

Report format (plain text, under 200 words):
- List each wearable device found with its name and type
- Connectivity: ONLINE / OFFLINE with last seen time
- Battery level if available
- Any health-related sensor readings (heart rate, steps, etc.) if exposed
- Recent notable events from history
- If no wearable devices found, say so clearly
- If SMARTTHINGS_TOKEN is not set, report that configuration is needed

Be concise and factual. Report exactly what the API returns.
"""


def agent_node(state: HealthAgentState) -> dict:
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}


def summarise_node(state: HealthAgentState) -> dict:
    last = state["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last)

    device_count = 0
    watch_online = False

    for msg in state["messages"]:
        if not hasattr(msg, "content"):
            continue
        raw = msg.content
        if isinstance(raw, str):
            import json
            try:
                raw = json.loads(raw)
            except Exception:
                continue
        if isinstance(raw, dict):
            if raw.get("ok") and "devices" in raw:
                device_count = raw.get("count", 0)
            if raw.get("ok") and raw.get("state") == "ONLINE":
                watch_online = True

    return {
        "health_report": content,
        "device_count": device_count,
        "watch_online": watch_online,
    }


def build_health_agent() -> StateGraph:
    tool_node = ToolNode(HEALTH_TOOLS)

    graph = StateGraph(HealthAgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("summarise", summarise_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: "summarise"},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("summarise", END)

    return graph.compile()


def run_health_agent() -> dict:
    app = build_health_agent()
    initial_state: HealthAgentState = {
        "messages": [
            HumanMessage(
                content=(
                    "Check all Samsung SmartThings connected devices. "
                    "Find any Galaxy Watch, Galaxy Ring, or wearable devices. "
                    "Report their connectivity status, battery level, "
                    "and any available health sensor data or recent events."
                )
            )
        ],
        "health_report": "",
        "device_count": 0,
        "watch_online": False,
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = run_health_agent()
    print("\n=== HEALTH REPORT ===")
    print(result["health_report"])