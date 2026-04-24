# Morning Agent — DA7 5SN
### LangGraph Multi-Agent System · Deployed on LangSmith

A production-ready morning briefing agent for **DA7 5SN, Bexleyheath, London**
built with **LangGraph** and traced/deployed via **LangSmith**.

---

## Architecture

```
START
  ├──► TrafficCheckerAgent  ──────────────────────────────┐
  │      • get_tfl_road_disruptions (A2, A207, A220...)   │
  │      • get_highways_england_incidents (A2)            │
  │                                                       ▼
  └──► WeatherCheckerAgent  ──────────────────────────► merge_reports
         • get_current_weather (Open-Meteo)                │
         • get_met_office_warnings                          ▼
                                                       send_email (Gmail SMTP)
                                                           │
                                                           ▼
                                                         END
```

Both agents run **in parallel** via LangGraph's fan-out pattern.
The supervisor merges their outputs and dispatches a single HTML email.

---

## Project Structure

```
morning_agent/
├── main.py                      # Entry point — run this
├── langgraph.json               # LangSmith deployment config
├── requirements.txt
├── .env.example                 # Copy to .env and fill in
│
├── agents/
│   ├── traffic_agent.py         # TrafficCheckerAgent (independent ReAct graph)
│   └── weather_agent.py         # WeatherCheckerAgent (independent ReAct graph)
│
├── graph/
│   └── supervisor_graph.py      # Supervisor — fan-out, merge, email
│
└── tools/
    └── shared_tools.py          # LangChain @tool definitions
```

---

## Setup

### 1. Clone & install dependencies

```bash
git clone <your-repo>
cd morning_agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `LANGCHAIN_API_KEY` | From [smith.langchain.com](https://smith.langchain.com) → Settings → API Keys |
| `LANGCHAIN_PROJECT` | e.g. `morning-agent-da75sn` |
| `OPENAI_API_KEY` | GPT-4o-mini powers the agents (or use `ANTHROPIC_API_KEY`) |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | 16-char App Password (see below) |

**Getting a Gmail App Password:**
1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Search "App passwords" → create one named "Morning Agent"
4. Copy the 16-character password into `.env`

### 3. Test locally

```bash
python main.py
```

You'll see the two agents run in parallel, then an email sent to `atul911in@gmail.com`.

---

## LangSmith Tracing

Set these in `.env` to enable full tracing:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key_here
LANGCHAIN_PROJECT=morning-agent-da75sn
```

Every run will appear in [smith.langchain.com](https://smith.langchain.com) under your project,
showing the full agent trace: tool calls, LLM inputs/outputs, latency per node.

---

## Deploy to LangSmith (LangGraph Cloud)

### Prerequisites
- LangSmith account with LangGraph Cloud access
- `langgraph` CLI installed: `pip install langgraph-cli`

### Deploy

```bash
# Authenticate
langgraph auth login

# Deploy all three graphs (supervisor + 2 agents)
langgraph deploy

# Check deployment status
langgraph deployments list
```

Your graphs will be available as REST API endpoints:

```
POST https://api.smith.langchain.com/v1/runs/...
  Body: { "input": { "location": "Bexleyheath", "postcode": "DA7 5SN", ... } }
```

### Trigger via cron (LangSmith Cron Jobs)

In LangSmith → your deployment → **Cron Jobs** → New:
- Schedule: `0 7 * * *`  (07:00 daily)
- Graph: `morning_agent`
- Input: `{"location": "Bexleyheath", "postcode": "DA7 5SN", "to_email": "atul911in@gmail.com"}`

---

## Schedule Locally (without LangSmith Cloud)

### Mac / Linux (cron)
```bash
crontab -e
# Add:
0 7 * * * cd /full/path/to/morning_agent && python main.py >> logs/agent.log 2>&1
```

### Windows (Task Scheduler)
1. Open **Task Scheduler** → Create Basic Task
2. Name: `Morning Agent`
3. Trigger: Daily at 07:00
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `C:\path\to\morning_agent\main.py`
   - Start in: `C:\path\to\morning_agent`

---

## Data Sources

| Source | Used for | API Key |
|---|---|---|
| [TfL Unified API](https://api.tfl.gov.uk) | Live road disruptions | None required |
| [Open-Meteo](https://open-meteo.com) | Weather (temp, wind, rain) | None required |
| [Met Office DataPoint](https://datahub.metoffice.gov.uk) | Weather warnings | Free (optional) |

---

## Customisation

- **Change location**: Update `LAT`, `LON`, `POSTCODE` in `.env`
- **Change roads**: Edit the `roads` parameter in `get_tfl_road_disruptions`
- **Add agents**: Create a new agent in `agents/`, register it in `supervisor_graph.py`
- **Change LLM**: Set `ANTHROPIC_API_KEY` instead of `OPENAI_API_KEY` to use Claude

---

## Extending

To add a new agent (e.g. Calendar Agent):
1. Create `agents/calendar_agent.py` with its own `StateGraph`
2. Add tools to `tools/shared_tools.py`
3. Add a node in `graph/supervisor_graph.py` alongside traffic/weather
4. Wire it into the fan-out and merge nodes
5. Register it in `langgraph.json`
