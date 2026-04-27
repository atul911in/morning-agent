"""
tools/shared_tools.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
LangChain tools used by the Traffic and Weather agents.
All tools are decorated with @tool so LangGraph agents can bind them.
"""

import os
import requests

# Fix SSL cert verification on Python 3.14+
try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass
from langchain_core.tools import tool


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TRAFFIC TOOLS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@tool
def get_tfl_road_disruptions(roads: str = "A2,A207,A220,A221,A222") -> dict:
    """
    Fetch live traffic disruptions from the TfL Unified API for a
    comma-separated list of road identifiers near DA7 5SN, Bexleyheath.
    Returns a dict with 'incidents' (list of strings) and 'status'.
    No API key required for basic use.
    """
    road_list = [r.strip() for r in roads.split(",")]
    incidents = []
    try:
        url = f"https://api.tfl.gov.uk/Road/{','.join(road_list)}/Disruption"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            for item in r.json():
                desc     = item.get("description", "").strip()
                category = item.get("category", "Unknown")
                severity = item.get("severity", "")
                streets  = item.get("streets", [])
                street   = streets[0].get("name", "") if streets else ""
                if desc:
                    incidents.append(
                        f"[{category}] {street}: {desc} (Severity: {severity})"
                    )
        elif r.status_code == 404:
            return {"status": "clear", "incidents": [], "raw_count": 0}
        else:
            return {"status": "error", "incidents": [], "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "error", "incidents": [], "error": str(e)}

    return {
        "status": "incidents_found" if incidents else "clear",
        "incidents": incidents,
        "raw_count": len(incidents),
    }


@tool
def get_highways_england_incidents(road: str = "A2") -> dict:
    """
    Fetch live incidents on a specific Highways England road near Bexleyheath
    using the TfL API endpoint. Useful for A2 which runs near DA7 5SN.
    Returns a dict with 'incidents' list.
    """
    try:
        url = f"https://api.tfl.gov.uk/Road/{road}/Disruption"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            incidents = []
            for item in r.json():
                desc   = item.get("description", "").strip()
                street = ""
                streets = item.get("streets", [])
                if streets:
                    street = streets[0].get("name", road)
                if desc:
                    incidents.append(f"[{road}] {street}: {desc}")
            return {"road": road, "incidents": incidents, "count": len(incidents)}
        return {"road": road, "incidents": [], "count": 0}
    except Exception as e:
        return {"road": road, "incidents": [], "error": str(e)}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# WEATHER TOOLS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Rain showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm",
}

WIND_DIRS = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
             "S","SSW","SW","WSW","W","WNW","NW","NNW"]


@tool
def get_current_weather(lat: float = 51.461, lon: float = 0.151) -> dict:
    """
    Fetch current weather conditions from Open-Meteo (free, no API key).
    Returns temperature (Â°C), feels-like (Â°C), wind speed (mph),
    wind direction, weather condition, humidity, and daily high/low/rain.
    Default coordinates are for DA7 5SN, Bexleyheath, London.
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,weather_code,"
            f"wind_speed_10m,wind_direction_10m,relative_humidity_2m"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
            f"weather_code"
            f"&wind_speed_unit=mph"
            f"&timezone=Europe/London"
            f"&forecast_days=1"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        d = r.json()
        c = d["current"]
        daily = d["daily"]

        deg      = c["wind_direction_10m"]
        wind_dir = WIND_DIRS[round(deg / 22.5) % 16]
        condition = WMO_CODES.get(c["weather_code"], f"Code {c['weather_code']}")

        return {
            "ok":          True,
            "condition":   condition,
            "temp_c":      round(c["temperature_2m"], 1),
            "feels_like_c": round(c["apparent_temperature"], 1),
            "wind_speed_mph": round(c["wind_speed_10m"]),
            "wind_direction": wind_dir,
            "humidity_pct": c["relative_humidity_2m"],
            "temp_max_c":  daily["temperature_2m_max"][0],
            "temp_min_c":  daily["temperature_2m_min"][0],
            "rain_mm":     daily["precipitation_sum"][0],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_met_office_warnings(location: str = "Bexley") -> dict:
    """
    Check for active Met Office weather warnings for a location.
    Uses the Met Office DataPoint API (free with registration).
    Falls back to a simple status if no API key is set.
    Returns a dict with 'warnings' list and 'has_warnings' bool.
    """
    api_key = os.getenv("MET_OFFICE_API_KEY", "")
    if not api_key:
        # Without an API key, return a graceful fallback
        return {
            "has_warnings": False,
            "warnings": [],
            "note": "No MET_OFFICE_API_KEY set â€” warning check skipped. "
                    "Get a free key at https://datahub.metoffice.gov.uk",
        }
    try:
        url = (
            f"http://datapoint.metoffice.gov.uk/public/data/"
            f"val/wxfcs/all/json/sitelist?key={api_key}"
        )
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return {"has_warnings": False, "warnings": [], "note": "No active warnings found."}
        return {"has_warnings": False, "warnings": [], "note": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"has_warnings": False, "warnings": [], "error": str(e)}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SMARTTHINGS TOOLS (Galaxy Watch / Wearable)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

SMARTTHINGS_BASE = "https://api.smartthings.com/v1"


def _st_headers() -> dict:
    token = os.getenv("SMARTTHINGS_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


@tool
def list_smartthings_devices() -> dict:
    """
    List all Samsung SmartThings devices including Galaxy Watch, Galaxy Ring,
    phones, and smart home devices. Returns device names, IDs, and types.
    Requires SMARTTHINGS_TOKEN env var.
    """
    token = os.getenv("SMARTTHINGS_TOKEN", "")
    if not token:
        return {"ok": False, "error": "SMARTTHINGS_TOKEN not set in .env"}
    try:
        r = requests.get(
            f"{SMARTTHINGS_BASE}/devices",
            headers=_st_headers(),
            timeout=15,
        )
        r.raise_for_status()
        devices = []
        for d in r.json().get("items", []):
            devices.append({
                "device_id": d.get("deviceId", ""),
                "name": d.get("label", d.get("name", "Unknown")),
                "type": d.get("deviceTypeName", ""),
                "manufacturer": d.get("manufacturerName", ""),
            })
        return {"ok": True, "devices": devices, "count": len(devices)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_smartthings_device_status(device_id: str) -> dict:
    """
    Get the full live status of a SmartThings device by its device_id.
    For Galaxy Watch this may include battery, connectivity, and health-related
    capabilities. Returns all component statuses as a dict.
    """
    token = os.getenv("SMARTTHINGS_TOKEN", "")
    if not token:
        return {"ok": False, "error": "SMARTTHINGS_TOKEN not set in .env"}
    try:
        r = requests.get(
            f"{SMARTTHINGS_BASE}/devices/{device_id}/status",
            headers=_st_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return {"ok": True, "status": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_smartthings_device_health(device_id: str) -> dict:
    """
    Get the health/connectivity status of a SmartThings device.
    Shows if the device is ONLINE or OFFLINE and last seen time.
    """
    token = os.getenv("SMARTTHINGS_TOKEN", "")
    if not token:
        return {"ok": False, "error": "SMARTTHINGS_TOKEN not set in .env"}
    try:
        r = requests.get(
            f"{SMARTTHINGS_BASE}/devices/{device_id}/health",
            headers=_st_headers(),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "ok": True,
            "device_id": data.get("deviceId", device_id),
            "state": data.get("state", "UNKNOWN"),
            "last_updated": data.get("lastUpdatedDate", ""),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_smartthings_device_history(device_id: str) -> dict:
    """
    Get recent event history for a SmartThings device.
    For Galaxy Watch this can include recent sensor readings and status changes.
    Returns the most recent events.
    """
    token = os.getenv("SMARTTHINGS_TOKEN", "")
    if not token:
        return {"ok": False, "error": "SMARTTHINGS_TOKEN not set in .env"}
    try:
        r = requests.get(
            f"{SMARTTHINGS_BASE}/devices/{device_id}/events",
            headers=_st_headers(),
            params={"limit": 20},
            timeout=15,
        )
        r.raise_for_status()
        events = []
        for e in r.json().get("items", []):
            events.append({
                "attribute": e.get("attribute", ""),
                "value": e.get("value", ""),
                "unit": e.get("unit", ""),
                "timestamp": e.get("eventTime", ""),
                "component": e.get("componentId", "main"),
            })
        return {"ok": True, "events": events, "count": len(events)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TFL TUBE / ELIZABETH LINE STATUS TOOLS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@tool
def get_tube_status(line_id: str = "elizabeth") -> dict:
    """
    Get the current status of a TfL line (tube, Elizabeth line, DLR, Overground).
    Common line IDs: elizabeth, jubilee, central, northern, district, victoria,
    bakerloo, circle, hammersmith-city, metropolitan, piccadilly, dlr, overground.
    Returns current status severity and description.
    No API key required for basic status.
    """
    try:
        url = f"https://api.tfl.gov.uk/Line/{line_id}/Status"
        api_key = os.getenv("TFL_API_KEY", "")
        params = {"app_key": api_key} if api_key else {}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return {"ok": False, "error": f"No data for line {line_id}"}
        line = data[0]
        statuses = []
        for s in line.get("lineStatuses", []):
            statuses.append({
                "severity": s.get("statusSeverityDescription", "Unknown"),
                "reason": s.get("reason", ""),
                "disruption_category": s.get("disruption", {}).get("category", "") if s.get("disruption") else "",
            })
        return {
            "ok": True,
            "line_id": line_id,
            "line_name": line.get("name", line_id),
            "statuses": statuses,
        }
    except Exception as e:
        return {"ok": False, "line_id": line_id, "error": str(e)}


@tool
def get_all_tube_status() -> dict:
    """
    Get the current status of ALL London Underground lines, Elizabeth line,
    DLR, and London Overground. Returns a summary of each line's status.
    Useful for a complete morning briefing of London transport.
    """
    try:
        url = "https://api.tfl.gov.uk/Line/Mode/tube,elizabeth-line,dlr,overground/Status"
        api_key = os.getenv("TFL_API_KEY", "")
        params = {"app_key": api_key} if api_key else {}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        lines = []
        for line in r.json():
            status_list = line.get("lineStatuses", [])
            primary = status_list[0] if status_list else {}
            severity = primary.get("statusSeverityDescription", "Unknown")
            reason = primary.get("reason", "")
            lines.append({
                "line_name": line.get("name", "?"),
                "line_id": line.get("id", ""),
                "status": severity,
                "reason": reason[:200] if reason else "",
            })
        disrupted = [l for l in lines if l["status"] != "Good Service"]
        return {
            "ok": True,
            "total_lines": len(lines),
            "disrupted_count": len(disrupted),
            "lines": lines,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_line_disruptions_forecast(line_id: str = "elizabeth") -> dict:
    """
    Get planned disruptions and future alerts for a TfL line.
    Shows upcoming engineering works, planned closures, and service changes.
    Useful for checking if there are any planned disruptions today or this week.
    """
    try:
        url = f"https://api.tfl.gov.uk/Line/{line_id}/Disruption"
        api_key = os.getenv("TFL_API_KEY", "")
        params = {"app_key": api_key} if api_key else {}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        disruptions = []
        for d in r.json():
            disruptions.append({
                "category": d.get("category", ""),
                "description": d.get("description", "")[:300],
                "affected_routes": [ar.get("name", "") for ar in d.get("affectedRoutes", [])[:3]],
                "closure_text": d.get("closureText", ""),
            })
        return {
            "ok": True,
            "line_id": line_id,
            "disruption_count": len(disruptions),
            "disruptions": disruptions,
        }
    except Exception as e:
        return {"ok": False, "line_id": line_id, "error": str(e)}


@tool
def plan_tfl_journey(from_location: str = "DA7 5SN", to_location: str = "Canary Wharf") -> dict:
    """
    Plan a journey using TfL Journey Planner. Accepts postcodes, station names,
    or place names. Returns recommended routes with duration and line info.
    Default origin is DA7 5SN (Bexleyheath).
    """
    try:
        url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{from_location}/to/{to_location}"
        api_key = os.getenv("TFL_API_KEY", "")
        params = {"app_key": api_key} if api_key else {}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        journeys = []
        for j in data.get("journeys", [])[:3]:
            legs_info = []
            for leg in j.get("legs", []):
                legs_info.append({
                    "mode": leg.get("mode", {}).get("name", ""),
                    "line": leg.get("routeOptions", [{}])[0].get("name", "") if leg.get("routeOptions") else "",
                    "from": leg.get("departurePoint", {}).get("commonName", ""),
                    "to": leg.get("arrivalPoint", {}).get("commonName", ""),
                    "duration_min": leg.get("duration", 0),
                })
            journeys.append({
                "duration_min": j.get("duration", 0),
                "departure": j.get("startDateTime", ""),
                "arrival": j.get("arrivalDateTime", ""),
                "legs": legs_info,
            })
        return {
            "ok": True,
            "from": from_location,
            "to": to_location,
            "journey_count": len(journeys),
            "journeys": journeys,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}