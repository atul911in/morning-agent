#!/usr/bin/env python3
"""
main.py — Morning Agent entry point
────────────────────────────────────
Run manually:
    python main.py

Schedule at 7am (cron):
    0 7 * * * cd /path/to/morning_agent && python main.py >> logs/agent.log 2>&1

Schedule at 7am (Windows Task Scheduler):
    Program: python.exe
    Arguments: C:\\path\\to\\morning_agent\\main.py
    Start in: C:\\path\\to\\morning_agent
"""

import os
import sys

# Add project root to path so imports resolve cleanly
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from graph.supervisor_graph import run_morning_agent

if __name__ == "__main__":
    run_morning_agent()
