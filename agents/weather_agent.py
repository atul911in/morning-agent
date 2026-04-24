"""
agents/weather_agent.py
───────────────────────
Independent LangGraph ReAct agent responsible for:
  • Fetching current weather for DA7 5SN, Bexleyheath via Open-Meteo
  • Checking Met Office warnings (if API key configured)
  • Returning a structured WeatherReport to the supervisor graph

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

from tools.shared_tools import get_current_weather, get_met_office_warnings


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class WeatherAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    weather_report: str         # final human-readable summary
    temperature_c: float        # current temp for use by supervisor
    feels_like_c: float
    wind_speed_mph: float
    wind_direction: str
    condition: str
    has_warnings: bool


# ─────────────────────────────────────────────────────────────────────────────
# Tools available to this agent
# ─────────────────────────────────────────────────────────────────────────────

WEATHER_TOOLS = [get_current_weather, get_met_office_warnings]


# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────

def _get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=0)
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.bind_tools(WEATHER_TOOLS)


# ─────────────────────────────────────────────────────────────────────────────
# Agent nodes
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Weather Checker Agent for DA7 5SN, Bexleyheath, London.

Your job:
1. Call get_current_weather with lat=51.461, lon=0.151 (DA7 5SN coordinates).
2. Call get_met_office_warnings to check for any active weather alerts.
3. Produce a clear weather report.

Report format (plain text, under 150 words):
- Current condition (e.g. Partly cloudy)
- Temperature: X°C (feels like Y°C)
- Wind: X mph, Direction
- Humidity: X%
- Today's high/low: X°C / Y°C
- Expected rain: X mm
- Warnings: [list any] or "No active warnings"

Be concise and accurate. Use the exact values from the tool responses.
"""


def agent_node(state: WeatherAgentState) -> dict:
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm
    response = chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}


def summarise_node(state: WeatherAgentState) -> dict:
    """Extract the final weather summary and key metrics from messages."""
    last = state["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last)

    # Try to pull structured values from tool results in message history
    temp_c      = 0.0
    feels_like  = 0.0
    wind_speed  = 0.0
    wind_dir    = ""
    condition   = ""
    has_warnings = False

    for msg in state["messages"]:
        if not hasattr(msg, "content"):
            continue
        # ToolMessage content is the raw tool output dict (as string or dict)
        raw = msg.content
        if isinstance(raw, str):
            import json, ast
            try:
                raw = json.loads(raw)
            except Exception:
                try:
                    raw = ast.literal_eval(raw)
                except Exception:
                    continue
        if isinstance(raw, dict) and raw.get("ok"):
            temp_c     = raw.get("temp_c", 0.0)
            feels_like = raw.get("feels_like_c", 0.0)
            wind_speed = raw.get("wind_speed_mph", 0.0)
            wind_dir   = raw.get("wind_direction", "")
            condition  = raw.get("condition", "")
        if isinstance(raw, dict) and raw.get("has_warnings"):
            has_warnings = True

    return {
        "weather_report":  content,
        "temperature_c":   temp_c,
        "feels_like_c":    feels_like,
        "wind_speed_mph":  wind_speed,
        "wind_direction":  wind_dir,
        "condition":       condition,
        "has_warnings":    has_warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build graph
# ─────────────────────────────────────────────────────────────────────────────

def build_weather_agent() -> StateGraph:
    tool_node = ToolNode(WEATHER_TOOLS)

    graph = StateGraph(WeatherAgentState)

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

def run_weather_agent() -> dict:
    app = build_weather_agent()
    initial_state: WeatherAgentState = {
        "messages": [
            HumanMessage(
                content=(
                    "Fetch the current weather for DA7 5SN, Bexleyheath, London "
                    "(lat=51.461, lon=0.151). Include temperature, feels-like, "
                    "wind speed and direction, humidity, today's high/low, "
                    "expected rain, and any Met Office warnings."
                )
            )
        ],
        "weather_report": "",
        "temperature_c":  0.0,
        "feels_like_c":   0.0,
        "wind_speed_mph": 0.0,
        "wind_direction": "",
        "condition":      "",
        "has_warnings":   False,
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = run_weather_agent()
    print("\n=== WEATHER REPORT ===")
    print(result["weather_report"])
