"""
agents/traffic_agent.py
───────────────────────
Independent LangGraph ReAct agent responsible for:
  - Checking live road traffic on A2, A207, A220, A221, A222
  - Checking Elizabeth line status and disruptions
  - Checking ALL tube line statuses
  - Reporting incidents, delays, and alerts from DA7 5SN area

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
    get_tfl_road_disruptions,
    get_highways_england_incidents,
    get_tube_status,
    get_all_tube_status,
    get_line_disruptions_forecast,
    plan_tfl_journey,
)


class TrafficAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    traffic_report: str
    incident_count: int
    raw_incidents: list[str]


TRAFFIC_TOOLS = [
    get_tfl_road_disruptions,
    get_highways_england_incidents,
    get_tube_status,
    get_all_tube_status,
    get_line_disruptions_forecast,
    plan_tfl_journey,
]


def _get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=0)
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.bind_tools(TRAFFIC_TOOLS)


SYSTEM_PROMPT = """You are the Traffic & Transport Agent for DA7 5SN, Bexleyheath, London.

Your job is to produce a comprehensive morning transport briefing. Do ALL of the following:

1. ELIZABETH LINE (priority - nearest line to DA7 5SN):
   - Call get_tube_status with line_id="elizabeth" for current status
   - Call get_line_disruptions_forecast with line_id="elizabeth" for planned disruptions/alerts

2. ALL TUBE LINES:
   - Call get_all_tube_status to get status of every tube line, Elizabeth line, DLR, and Overground
   - Highlight any lines with disruptions

3. ROAD TRAFFIC:
   - Call get_tfl_road_disruptions for A2, A207, A220, A221, A222
   - Call get_highways_england_incidents for the A2

Report format (plain text, under 300 words):

ELIZABETH LINE
- Current status (Good Service / Minor Delays / etc.)
- Any disruptions or planned works today

TUBE & RAIL OVERVIEW
- Lines with Good Service (list briefly)
- Lines with issues (detail each: line name, status, reason)

ROAD TRAFFIC (2-mile radius of DA7 5SN)
- Overall status (Clear / Minor delays / Significant disruption)
- List each incident with road name and impact
- If all clear, say so

Be factual and concise. Do not fabricate information.
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
    last = state["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last)

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
        "raw_incidents": raw,
    }


def build_traffic_agent() -> StateGraph:
    tool_node = ToolNode(TRAFFIC_TOOLS)

    graph = StateGraph(TrafficAgentState)

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

    return graph.compile(recursion_limit=50)


def run_traffic_agent() -> dict:
    app = build_traffic_agent()
    initial_state: TrafficAgentState = {
        "messages": [
            HumanMessage(
                content=(
                    "Produce a complete morning transport briefing for DA7 5SN, Bexleyheath, London. "
                    "Check: 1) Elizabeth line current status and any planned disruptions, "
                    "2) ALL tube line statuses to find any disruptions across the network, "
                    "3) Road traffic on A2, A207, A220, A221, A222 within 2 miles. "
                    "Report everything clearly."
                )
            )
        ],
        "traffic_report": "",
        "incident_count": 0,
        "raw_incidents": [],
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = run_traffic_agent()
    print("\n=== TRAFFIC & TRANSPORT REPORT ===")
    print(result["traffic_report"])