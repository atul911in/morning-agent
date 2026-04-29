# Morning Agent — DA7 5SN
### LangGraph Multi-Agent System · GitHub Actions · Alexa Notifications

A production-ready morning briefing agent for **DA7 5SN, Bexleyheath, London**
built with **LangGraph**, traced via **LangSmith**, deployed on **GitHub Actions** (free).

Delivers a daily 7am briefing via **email** and **Alexa voice notification**.

---

## Architecture

```
START
  ├──► TrafficAgent (parallel)  ─────────────────────────────┐
  │      • get_tube_status (Elizabeth line)                   │
  │      • get_all_tube_status (all Underground + DLR)       │
  │      • get_line_disruptions_forecast                     │
  │      • get_tfl_road_disruptions (A2, A207, A220...)      │
  │      • get_highways_england_incidents (A2)                │
  │                                                          │
  ├──► WeatherAgent (parallel)  ─────────────────────────────┤
  │      • get_current_weather (Open-Meteo)                  │
  │      • get_met_office_warnings                           │
  │                                                          │
  └──► HealthAgent (parallel)  ──────────────────────────────┤
         • list_smartthings_devices                          │
         • get_smartthings_device_status                     │
         • get_smartthings_device_health                     │
         • get_smartthings_device_history                    ▼
                                                        merge_reports
                                                             │
                                                             ▼
                                                        send_email (Gmail SMTP)
                                                             │
                                                             ▼
                                                        notify_alexa (voice alert)
                                                             │
                                                             ▼
                                                           END
```

Three agents run **in parallel** via LangGraph’s fan-out pattern.
The supervisor merges outputs, sends an HTML email, then pushes a voice notification to Alexa (only announcing disruptions).

---

## Project Structure

```
morning_agent/
├── main.py                          # Entry point
├── langgraph.json                   # LangGraph deployment config (4 graphs)
├── requirements.txt
├── .env.example                     # Copy to .env and fill in
├── .gitignore
│
├── .github/workflows/
│   └── morning-agent.yml            # GitHub Actions — daily 7am UK (BST/GMT aware)
│
├── agents/
│   ├── traffic_agent.py             # Traffic & Transport (tube + roads)
│   ├── weather_agent.py             # Weather & warnings
│   └── health_agent.py              # Samsung SmartThings / Galaxy Watch
│
├── graph/
│   └── supervisor_graph.py          # Supervisor — fan-out, merge, email, Alexa
│
└── tools/
    └── shared_tools.py              # All LangChain @tool definitions
```

---

## Features

- **Elizabeth line + all tube status** — real-time via TfL Unified API
- **Road traffic** — disruptions on A2, A207, A220, A221, A222
- **Weather** — current conditions, forecast, Met Office warnings
- **Galaxy Watch** — device status via Samsung SmartThings
- **HTML email** — styled briefing with colour-coded status badges
- **Alexa voice alert** — only speaks when there are disruptions
- **BST/GMT aware** — always runs at 7am UK time regardless of clock changes
- **Full tracing** — every run visible in LangSmith with tool calls and latency

---

## Setup

### 1. Clone & install

```bash
git clone https://github.com/atul911in/morning-agent.git
cd morning-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env`:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | GPT-4o-mini powers the agents |
| `LANGCHAIN_API_KEY` | From [smith.langchain.com](https://smith.langchain.com) |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | 16-char App Password ([instructions](https://myaccount.google.com/apppasswords)) |
| `TO_EMAIL` | Recipient email address |
| `SMARTTHINGS_TOKEN` | From [account.smartthings.com/tokens](https://account.smartthings.com/tokens) |
| `ALEXA_NOTIFY_CODE` | From "Notify Me" Alexa skill (say "Alexa, open Notify Me") |
| `TFL_API_KEY` | Optional — from [api-portal.tfl.gov.uk](https://api-portal.tfl.gov.uk) |

### 3. Test locally

```bash
python main.py
```

---

## Deployment (GitHub Actions)

The agent runs automatically via GitHub Actions at **7:00 AM UK time** every day.
It handles BST/GMT clock changes automatically.

### Setup GitHub Secrets

Go to **Settings → Secrets → Actions** in your repo and add:

- `OPENAI_API_KEY`
- `LANGCHAIN_API_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `TO_EMAIL`
- `SMARTTHINGS_TOKEN`
- `ALEXA_NOTIFY_CODE`

### Manual trigger

Go to **Actions** tab → **Morning Agent - Daily Briefing** → **Run workflow**

---

## Alexa Voice Notifications

Uses the free **"Notify Me"** Alexa skill by Thomptronics.

- Only announces **disrupted lines and road incidents**
- If all clear: "All tube lines and roads are running a good service"
- Always includes weather summary

Setup:
1. Enable "Notify Me" skill in Alexa app
2. Say "Alexa, open Notify Me" to activate
3. Check email for access code
4. Add to `.env` as `ALEXA_NOTIFY_CODE`

---

## Data Sources

| Source | Used for | API Key |
|---|---|---|
| [TfL Unified API](https://api.tfl.gov.uk) | Tube status, road disruptions, journey planning | Free (optional key for higher limits) |
| [Open-Meteo](https://open-meteo.com) | Weather conditions and forecast | None required |
| [Met Office DataPoint](https://datahub.metoffice.gov.uk) | Weather warnings | Free (optional) |
| [Samsung SmartThings](https://api.smartthings.com) | Galaxy Watch / wearable status | Free PAT |
| [Notify My Echo](https://api.notifymyecho.com) | Alexa voice notifications | Free (via skill) |

---

## LangSmith Tracing

Every run is traced end-to-end in LangSmith showing:
- Parallel agent execution
- Individual tool calls with inputs/outputs
- LLM reasoning steps
- Latency per node
- Total execution time (~15 seconds)

View at: [smith.langchain.com](https://smith.langchain.com) → project `morning-agent-da75sn`

---

## Customisation

- **Change location**: Update `LAT`, `LON`, `POSTCODE` in `.env`
- **Change roads**: Edit the `roads` parameter in `get_tfl_road_disruptions`
- **Change tube lines**: Modify the `line_id` in traffic agent prompt
- **Add agents**: Create in `agents/`, register in `supervisor_graph.py` and `langgraph.json`
- **Change LLM**: Set `ANTHROPIC_API_KEY` to use Claude instead of GPT-4o-mini

---

## License

MIT
