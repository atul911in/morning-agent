"""
graph/supervisor_graph.py
LangGraph supervisor: parallel fan-out (3 agents), merge, email.
Traced end-to-end in LangSmith.
"""

from __future__ import annotations

import os
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from agents.traffic_agent import run_traffic_agent
from agents.weather_agent import run_weather_agent
from agents.health_agent import run_health_agent
from config import DISPLAY_POSTCODE, LOCATION, TO_EMAIL, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ALEXA_NOTIFY_CODE

load_dotenv()


class SupervisorState(TypedDict):
    location: str
    postcode: str
    to_email: str
    traffic_report: str
    traffic_count: int
    weather_report: str
    temperature_c: float
    feels_like_c: float
    wind_speed_mph: float
    wind_direction: str
    condition: str
    has_warnings: bool
    health_report: str
    device_count: int
    watch_online: bool
    html_body: str
    plain_body: str
    email_sent: bool
    email_subject: str
    error: str


def traffic_node(state: SupervisorState) -> dict:
    print('Traffic Agent starting...')
    try:
        result = run_traffic_agent()
        print(f'   Traffic Agent complete')
        return {
            'traffic_report': result.get('traffic_report', 'No report generated.'),
            'traffic_count': result.get('incident_count', 0),
        }
    except Exception as e:
        print(f'   Traffic Agent error: {e}')
        return {'traffic_report': f'Traffic check failed: {e}', 'traffic_count': 0}


def weather_node(state: SupervisorState) -> dict:
    print('Weather Agent starting...')
    try:
        result = run_weather_agent()
        print(f'   Weather Agent complete')
        return {
            'weather_report': result.get('weather_report', 'No report generated.'),
            'temperature_c': result.get('temperature_c', 0.0),
            'feels_like_c': result.get('feels_like_c', 0.0),
            'wind_speed_mph': result.get('wind_speed_mph', 0.0),
            'wind_direction': result.get('wind_direction', ''),
            'condition': result.get('condition', ''),
            'has_warnings': result.get('has_warnings', False),
        }
    except Exception as e:
        print(f'   Weather Agent error: {e}')
        return {'weather_report': f'Weather check failed: {e}', 'has_warnings': False}


def health_node(state: SupervisorState) -> dict:
    print('Health Agent starting...')
    try:
        result = run_health_agent()
        print(f'   Health Agent complete')
        return {
            'health_report': result.get('health_report', 'No report generated.'),
            'device_count': result.get('device_count', 0),
            'watch_online': result.get('watch_online', False),
        }
    except Exception as e:
        print(f'   Health Agent error: {e}')
        return {'health_report': f'Health check failed: {e}', 'device_count': 0, 'watch_online': False}


def merge_node(state: SupervisorState) -> dict:
    print("Merging reports...")
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%H:%M")
    postcode = state.get("postcode", "DA7 5SN")

    traffic_html = state.get("traffic_report", "Unavailable").replace("\n", "<br>")
    weather_html = state.get("weather_report", "Unavailable").replace("\n", "<br>")
    health_html = state.get("health_report", "Unavailable").replace("\n", "<br>")
    traffic_count = state.get("traffic_count", 0)
    has_warnings = state.get("has_warnings", False)
    watch_online = state.get("watch_online", False)

    badge_traffic = "#c62828" if traffic_count > 0 else "#2e7d32"
    badge_weather = "#c62828" if has_warnings else "#2e7d32"
    badge_health = "#2e7d32" if watch_online else "#ff8f00"
    traffic_label = f"{traffic_count} incident(s)" if traffic_count else "All clear"
    weather_label = "Warnings active" if has_warnings else "No warnings"
    health_label = "Watch online" if watch_online else "Check status"

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:640px;margin:0 auto;padding:20px;">
  <div style="background:#1a237e;color:#fff;padding:18px 22px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;font-size:22px;">Morning Briefing</h1>
    <p style="margin:5px 0 0;opacity:0.85;font-size:13px;">{postcode}, Bexleyheath - {date_str} - Generated {time_str} BST</p>
  </div>
  <div style="border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;padding:22px;">
    <h2 style="font-size:17px;color:#1565C0;margin-top:0;">Traffic - 2-mile radius <span style="background:{badge_traffic};color:#fff;font-size:11px;padding:3px 10px;border-radius:12px;margin-left:8px;">{traffic_label}</span></h2>
    <div style="background:#f5f5f5;border-radius:6px;padding:14px 16px;font-size:13px;line-height:1.7;color:#333;">{traffic_html}</div>
    <hr style="border:none;border-top:1px solid #eee;margin:22px 0;">
    <h2 style="font-size:17px;color:#2e7d32;margin-top:0;">Weather - {postcode} <span style="background:{badge_weather};color:#fff;font-size:11px;padding:3px 10px;border-radius:12px;margin-left:8px;">{weather_label}</span></h2>
    <div style="background:#f5f5f5;border-radius:6px;padding:14px 16px;font-size:13px;line-height:1.7;color:#333;">{weather_html}</div>
    <hr style="border:none;border-top:1px solid #eee;margin:22px 0;">
    <h2 style="font-size:17px;color:#6A1B9A;margin-top:0;">Galaxy Watch - SmartThings <span style="background:{badge_health};color:#fff;font-size:11px;padding:3px 10px;border-radius:12px;margin-left:8px;">{health_label}</span></h2>
    <div style="background:#f5f5f5;border-radius:6px;padding:14px 16px;font-size:13px;line-height:1.7;color:#333;">{health_html}</div>
    <hr style="border:none;border-top:1px solid #eee;margin:22px 0;">
    <p style="color:#999;font-size:11px;margin:0;line-height:1.6;">Sent by <strong>Morning Agent</strong> (LangGraph + LangSmith)<br>Agents: TrafficChecker, WeatherChecker, HealthChecker<br>Data: TfL API, Open-Meteo, Met Office, Samsung SmartThings</p>
  </div>
</body>
</html>"""

    plain = (
        f"MORNING BRIEFING - {date_str} - {postcode}\n\n"
        f"TRAFFIC\n" + "-" * 40 + f"\n{state.get('traffic_report', 'Unavailable')}\n\n"
        f"WEATHER\n" + "-" * 40 + f"\n{state.get('weather_report', 'Unavailable')}\n\n"
        f"GALAXY WATCH\n" + "-" * 40 + f"\n{state.get('health_report', 'Unavailable')}\n\n"
        f"-- Morning Agent (LangGraph) --"
    )

    subject = f"Morning briefing - {date_str}"

    return {"html_body": html, "plain_body": plain, "email_subject": subject}



def send_email_node(state: SupervisorState) -> dict:
    gmail_addr = GMAIL_ADDRESS
    app_password = GMAIL_APP_PASSWORD
    to_email = state.get("to_email", os.getenv("TO_EMAIL", ""))
    subject = state.get("email_subject", "Morning briefing")
    html_body = state.get("html_body", "")
    plain_body = state.get("plain_body", "")

    if not gmail_addr or not app_password:
        err = "Gmail credentials not set"
        print(f"Warning: {err}")
        return {"email_sent": False, "error": err}

    print(f"Sending email to {to_email}...")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_addr
        msg["To"] = to_email
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, app_password)
            server.sendmail(gmail_addr, to_email, msg.as_string())

        print(f"Email sent successfully to {to_email}")
        return {"email_sent": True, "error": ""}
    except Exception as e:
        print(f"Email failed: {e}")
        return {"email_sent": False, "error": str(e)}



def notify_alexa_node(state: SupervisorState) -> dict:
    code = ALEXA_NOTIFY_CODE
    if not code:
        print("ALEXA_NOTIFY_CODE not set, skipping Alexa notification")
        return {}

    postcode = state.get("postcode", "DA7 5SN")
    traffic = state.get("traffic_report", "unavailable")
    weather = state.get("weather_report", "unavailable")

    # Extract only disrupted lines from traffic report
    # Look for keywords that indicate issues
    disruption_keywords = [
        "minor delay", "severe delay", "part closure", "planned closure",
        "suspended", "part suspended", "reduced service", "bus service",
        "special service", "disruption", "closure", "delay", "incident",
    ]
    traffic_lines = traffic.split("\n")
    disrupted_lines = []
    for line in traffic_lines:
        lower = line.lower().strip()
        if any(kw in lower for kw in disruption_keywords):
            disrupted_lines.append(line.strip())

    if disrupted_lines:
        traffic_summary = "Transport alerts: " + ". ".join(disrupted_lines[:10])
    else:
        traffic_summary = "All tube lines and roads are running a good service"

    if len(traffic_summary) > 1000:
        traffic_summary = traffic_summary[:1000] + "..."

    if len(weather) > 400:
        weather = weather[:400] + "..."

    summary = f"Good morning! Here is your briefing for {postcode}. {traffic_summary}. Weather: {weather}."

    print("Sending Alexa notification...")
    try:
        import requests
        r = requests.post(
            "https://api.notifymyecho.com/v1/NotifyMe",
            json={"notification": summary, "accessCode": code},
            timeout=10,
        )
        if r.status_code == 202:
            print("Alexa notification sent successfully")
        else:
            print(f"Alexa notification failed: {r.status_code} {r.text[:100]}")
    except Exception as e:
        print(f"Alexa notification error: {e}")
    return {}

def build_supervisor_graph() -> StateGraph:
    graph = StateGraph(SupervisorState)

    graph.add_node("traffic_agent", traffic_node)
    graph.add_node("weather_agent", weather_node)
    graph.add_node("health_agent", health_node)
    graph.add_node("merge", merge_node)
    graph.add_node("send_email", send_email_node)
    graph.add_node("notify_alexa", notify_alexa_node)

    graph.add_edge(START, "traffic_agent")
    graph.add_edge(START, "weather_agent")
    graph.add_edge(START, "health_agent")

    graph.add_edge("traffic_agent", "merge")
    graph.add_edge("weather_agent", "merge")
    graph.add_edge("health_agent", "merge")

    graph.add_edge("merge", "send_email")
    graph.add_edge("send_email", "notify_alexa")
    graph.add_edge("notify_alexa", END)

    return graph.compile()


def run_morning_agent():
    print("\n" + "=" * 55)
    print("  MORNING AGENT - DA7 5SN, Bexleyheath")
    print("  " + datetime.datetime.now().strftime("%A %d %B %Y  %H:%M BST"))
    print("=" * 55 + "\n")

    graph = build_supervisor_graph()

    initial_state: SupervisorState = {
        "location": LOCATION,
        "postcode": DISPLAY_POSTCODE,
        "to_email": TO_EMAIL,
        "traffic_report": "",
        "traffic_count": 0,
        "weather_report": "",
        "temperature_c": 0.0,
        "feels_like_c": 0.0,
        "wind_speed_mph": 0.0,
        "wind_direction": "",
        "condition": "",
        "has_warnings": False,
        "health_report": "",
        "device_count": 0,
        "watch_online": False,
        "html_body": "",
        "plain_body": "",
        "email_sent": False,
        "email_subject": "",
        "error": "",
    }

    result = graph.invoke(initial_state)

    print("\n" + "-" * 55)
    print(f"  Email sent:    {result['email_sent']}")
    if result.get("error"):
        print(f"  Error:         {result['error']}")
    print(f"  Subject:       {result.get('email_subject', '')}")
    print("-" * 55 + "\n")

    return result


if __name__ == "__main__":
    run_morning_agent()
