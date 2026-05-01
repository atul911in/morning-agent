"""
config.py
─────────
Central configuration for the Morning Agent.
All user-configurable settings are read from environment variables.
To customise for your location, edit .env — no code changes needed.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# --- Location ---
POSTCODE = os.getenv("POSTCODE", "DA75SN")
DISPLAY_POSTCODE = os.getenv("DISPLAY_POSTCODE", "DA7 5SN")
LOCATION = os.getenv("LOCATION", "Bexleyheath, London")
LAT = float(os.getenv("LAT", "51.461"))
LON = float(os.getenv("LON", "0.151"))

# --- Traffic ---
TRAFFIC_RADIUS_MILES = int(os.getenv("TRAFFIC_RADIUS_MILES", "2"))
ROADS = os.getenv("ROADS", "A2,A207,A220,A221,A222")
NEAREST_TUBE_LINE = os.getenv("NEAREST_TUBE_LINE", "elizabeth")

# --- Email ---
TO_EMAIL = os.getenv("TO_EMAIL", "")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# --- Alexa ---
ALEXA_NOTIFY_CODE = os.getenv("ALEXA_NOTIFY_CODE", "")

# --- SmartThings ---
SMARTTHINGS_TOKEN = os.getenv("SMARTTHINGS_TOKEN", "")

# --- LLM ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")