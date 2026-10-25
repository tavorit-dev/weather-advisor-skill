#!/usr/bin/env python3
"""Fetch weather evidence from Open-Meteo for the weather-advisor skill.

The demo uses only the Python standard library and requires no API key. It
converts a city name into a skill-ready input envelope: location context plus
normalized hourly evidence that matches references/evidence-contract.md.

Air quality is optional and comes from a second Open-Meteo endpoint. It is
included by default because particulate levels often decide whether strenuous
outdoor activity is advisable; pass --no-air-quality to skip it. Air-quality
values are modelled forecasts, not ground-station measurements.

Usage:
    python demo/weather_demo.py Tokyo
    python demo/weather_demo.py "New York" --days 2
    python demo/weather_demo.py Tokyo --offline
    python demo/weather_demo.py Tokyo --no-air-quality
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ATTRIBUTION = "Weather data by Open-Meteo.com"
AIR_QUALITY_ATTRIBUTION = "Air quality data by Open-Meteo.com (CAMS)"
DATA_LICENSE = "CC BY 4.0"
USER_AGENT = (
    "weather-advisor-skill-demo/0.1 "
    "(+https://github.com/tavorit-dev/weather-advisor-skill)"
)
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

INTENTS = {
    "weather_lookup",
    "clothing_advice",
    "commute_advice",
    "outdoor_activity",
    "travel_planning",
    "general_weather_advice",
}

# Open-Meteo hourly field -> (evidence type, unit)
HOURLY_FIELDS = [
    ("temperature_2m", "temperature", "°C"),
    ("apparent_temperature", "apparent_temperature", "°C"),
    ("precipitation_probability", "precipitation_probability", "%"),
    ("precipitation", "precipitation_amount", "mm"),
    ("wind_speed_10m", "wind_speed", "km/h"),
    ("wind_gusts_10m", "wind_gust", "km/h"),
]

# Open-Meteo air-quality field -> (evidence type, unit).
# The contract requires an air-quality index to state its scale, so both the
# US and European scales are carried and named in the evidence description.
AIR_QUALITY_FIELDS = [
    ("pm2_5", "particulate_matter_2_5", "μg/m³"),
    ("pm10", "particulate_matter_10", "μg/m³"),
    ("us_aqi", "air_quality_index", "USAQI"),
    ("european_aqi", "air_quality_index", "EAQI"),
]
AIR_QUALITY_SCALES = {
    "us_aqi": "US AQI scale",
    "european_aqi": "European AQI scale",
}
PARTICULATE_DESCRIPTIONS = {
    "pm2_5": "Fine particulate matter (PM2.5), modelled hourly forecast.",
    "pm10": "Coarse particulate matter (PM10), modelled hourly forecast.",
}
AIR_QUALITY_SOURCE = "Open-Meteo Air Quality (CAMS)"


class DemoError(Exception):
    """A user-facing failure that should not produce a traceback."""


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DemoError(f"Cannot read fixture {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DemoError(f"Fixture {path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DemoError(f"Fixture {path} must contain a JSON object")
    return payload


def _request_json(
    url: str, params: dict[str, Any], timeout: float = 20.0
) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise DemoError(f"Open-Meteo returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DemoError(f"Could not reach Open-Meteo: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise DemoError("Open-Meteo returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DemoError("Open-Meteo returned an unexpected response shape")
    return payload


def geocode(city: str, *, offline: bool = False) -> dict[str, Any]:
    """Resolve a city name to coordinates, country, and timezone."""
    city = city.strip()
    if not city:
        raise DemoError("City name is empty")

    if offline:
        if city.lower() not in {"tokyo", "东京"}:
            raise DemoError(
                "Offline mode bundles only a Tokyo fixture; "
                "omit --offline to query another city"
            )
        payload = _load_fixture("geocoding-tokyo.json")
    else:
        payload = _request_json(
            GEOCODING_URL,
            {
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
        )

    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise DemoError(f"No location found for {city!r}")

    place = results[0]
    if not isinstance(place, dict):
        raise DemoError("Geocoding response is malformed")

    name = place.get("name")
    latitude = place.get("latitude")
    longitude = place.get("longitude")
    if not isinstance(name, str) or latitude is None or longitude is None:
        raise DemoError("Geocoding result is missing a name or coordinates")

    timezone = place.get("timezone") or "UTC"
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        timezone = "UTC"

    return {
        "name": name,
        "country": place.get("country"),
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    }


def fetch_forecast(
    location: dict[str, Any], days: int = 3, *, offline: bool = False
) -> dict[str, Any]:
    """Fetch the raw hourly forecast payload."""
    if offline:
        payload = _load_fixture("forecast-tokyo.json")
    else:
        if not 1 <= days <= 7:
            raise DemoError("days must be between 1 and 7")
        payload = _request_json(
            FORECAST_URL,
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "hourly": ",".join(field for field, _, _ in HOURLY_FIELDS),
                "forecast_days": days,
                "timezone": location["timezone"],
                "temperature_unit": "celsius",
                "precipitation_unit": "mm",
                "wind_speed_unit": "kmh",
            },
        )

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise DemoError("Forecast response is missing hourly data")
    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        raise DemoError("Forecast response contains no hourly timestamps")
    return payload


def fetch_air_quality(
    location: dict[str, Any], days: int = 3, *, offline: bool = False
) -> dict[str, Any]:
    """Fetch the raw hourly air-quality payload."""
    if offline:
        payload = _load_fixture("air-quality-tokyo.json")
    else:
        if not 1 <= days <= 7:
            raise DemoError("days must be between 1 and 7")
        payload = _request_json(
            AIR_QUALITY_URL,
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "hourly": ",".join(field for field, _, _ in AIR_QUALITY_FIELDS),
                "forecast_days": days,
                "timezone": location["timezone"],
            },
        )

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise DemoError("Air-quality response is missing hourly data")
    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        raise DemoError("Air-quality response contains no hourly timestamps")
    return payload


def build_evidence(
    location: dict[str, Any],
    forecast: dict[str, Any],
    retrieved_at: str,
    air_quality: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Convert Open-Meteo hourly arrays into evidence items.

    Weather and air quality are separate upstream payloads, so they are merged
    onto the same hourly timeline here.
    """
    timezone = _zone(location["timezone"])
    hourly = forecast["hourly"]
    times = hourly.get("time", [])
    evidence: list[dict[str, Any]] = []

    for index, timestamp in enumerate(times):
        try:
            start = datetime.fromisoformat(timestamp)
        except (TypeError, ValueError) as exc:
            raise DemoError(f"Invalid hourly timestamp: {timestamp!r}") from exc
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone)
        end = start + timedelta(hours=1)

        for api_field, evidence_type, unit in HOURLY_FIELDS:
            values = hourly.get(api_field)
            if not isinstance(values, list) or index >= len(values):
                continue
            value = values[index]
            if value is None:
                continue
            evidence.append(
                {
                    "id": f"ev-{index:03d}-{api_field}",
                    "type": evidence_type,
                    "value": value,
                    "unit": unit,
                    "valid_from": start.isoformat(),
                    "valid_to": end.isoformat(),
                    "source": "Open-Meteo",
                    "observed_at": retrieved_at,
                }
            )

        if air_quality is None:
            continue
        air_hourly = air_quality["hourly"]
        air_index = air_hourly.get("time", []).index(timestamp) if timestamp in (
            air_hourly.get("time") or []
        ) else None
        if air_index is None:
            continue

        for api_field, evidence_type, unit in AIR_QUALITY_FIELDS:
            values = air_hourly.get(api_field)
            if not isinstance(values, list) or air_index >= len(values):
                continue
            value = values[air_index]
            if value is None:
                continue
            item: dict[str, Any] = {
                "id": f"ev-aq-{index:03d}-{api_field}",
                "type": evidence_type,
                "value": value,
                "unit": unit,
                "valid_from": start.isoformat(),
                "valid_to": end.isoformat(),
                "source": AIR_QUALITY_SOURCE,
                "observed_at": retrieved_at,
            }
            if api_field in AIR_QUALITY_SCALES:
                item["description"] = (
                    "Air quality index on the "
                    f"{AIR_QUALITY_SCALES[api_field]}; modelled hourly forecast. "
                    "Scales are not directly comparable to each other."
                )
            else:
                item["description"] = PARTICULATE_DESCRIPTIONS[api_field]
            evidence.append(item)

    return evidence


def build_document(
    city: str,
    *,
    days: int = 3,
    query: str = "",
    intent: str = "weather_lookup",
    offline: bool = False,
    air_quality: bool = True,
) -> dict[str, Any]:
    """Build a skill-ready input envelope from live or offline weather data."""
    if intent not in INTENTS:
        raise DemoError(f"Unknown intent: {intent!r}")

    location = geocode(city, offline=offline)
    forecast = fetch_forecast(location, days=days, offline=offline)

    air_payload = None
    if air_quality:
        air_payload = fetch_air_quality(location, days=days, offline=offline)

    timezone = _zone(location["timezone"])
    retrieved_at = datetime.now(timezone).isoformat(timespec="seconds")
    evidence = build_evidence(location, forecast, retrieved_at, air_payload)
    if not evidence:
        raise DemoError("No usable weather values were returned")

    source_urls = [GEOCODING_URL, FORECAST_URL]
    attributions = [ATTRIBUTION]
    if air_payload is not None:
        source_urls.append(AIR_QUALITY_URL)
        attributions.append(AIR_QUALITY_ATTRIBUTION)

    data_note = (
        "Bundled fixtures with synthetic values for offline testing. "
        "Not a real forecast and not real air quality."
        if offline
        else "Live forecast data; values change over time and are not "
        "guaranteed."
    )
    if air_payload is not None:
        data_note += (
            " Air-quality values are modelled forecasts (CAMS), not "
            "ground-station measurements, and do not replace official "
            "air-quality bulletins."
        )

    return {
        "user_query": query or f"What will the weather be like in {location['name']}?",
        "intent": intent,
        "context": {
            "location": location,
            "start": min(item["valid_from"] for item in evidence),
            "end": max(item["valid_to"] for item in evidence),
        },
        "weather_evidence": evidence,
        "attribution": " | ".join(attributions),
        "metadata": {
            "provider": "Open-Meteo",
            "mode": "offline" if offline else "live",
            "retrieved_at": retrieved_at,
            "data_license": DATA_LICENSE,
            "source_urls": source_urls,
            "data_note": data_note,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Open-Meteo weather evidence for the weather-advisor skill."
    )
    parser.add_argument(
        "city",
        nargs="*",
        help="City name, for example Tokyo or 'New York'",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        choices=range(1, 8),
        metavar="1-7",
        help="Forecast days for live mode (default: 3)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the bundled Tokyo fixture; no network access",
    )
    parser.add_argument(
        "--no-air-quality",
        dest="air_quality",
        action="store_false",
        help="Skip the Open-Meteo air-quality endpoint (weather evidence only)",
    )
    parser.add_argument(
        "--query",
        default="",
        help="user_query value to place in the output envelope",
    )
    parser.add_argument(
        "--intent",
        default="weather_lookup",
        choices=sorted(INTENTS),
        help="intent value to place in the output envelope",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this file instead of stdout",
    )
    args = parser.parse_args(argv)

    city = " ".join(args.city).strip() or "Tokyo"

    try:
        document = build_document(
            city,
            days=args.days,
            query=args.query,
            intent=args.intent,
            offline=args.offline,
            air_quality=args.air_quality,
        )
    except DemoError as exc:
        print(f"Weather demo failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(document, ensure_ascii=False, indent=2)

    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            print(
                f"Weather demo failed: cannot write {args.output}: {exc}",
                file=sys.stderr,
            )
            return 1
        count = len(document["weather_evidence"])
        print(f"Wrote {count} evidence items to {args.output}", file=sys.stderr)
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
