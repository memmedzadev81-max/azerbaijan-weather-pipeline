"""EXTRACT -> BRONZE

Pulls hourly weather data from the Open-Meteo API and stores every response
untouched as a JSON file. The bronze layer is the raw, replayable copy of the
source: if a transformation bug is found later, silver and gold can be rebuilt
from these files without calling the API again.
"""
import json
import time
from datetime import date, datetime
from pathlib import Path

import requests

from . import config
from .sample_data import fake_api_response


def fetch_city(city: dict, start: date, end: date, retries: int = 3) -> dict:
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(config.HOURLY_VARIABLES),
        "timezone": config.TIMEZONE,
    }
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(config.API_URL, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            if "hourly" not in payload:
                raise ValueError(f"Unexpected API response: {str(payload)[:200]}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s
    raise RuntimeError(f"API call failed for {city['city_name']}: {last_error}")


def save_bronze(city: dict, start: date, end: date, payload: dict,
                bronze_dir: Path | None = None) -> Path:
    folder = Path(bronze_dir or config.BRONZE_DIR) / city["city_name"].lower()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{start.isoformat()}_{end.isoformat()}.json"
    record = {
        "_metadata": {
            "city_id": city["city_id"],
            "city_name": city["city_name"],
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "extracted_at": datetime.now().isoformat(timespec="seconds"),
            "source": config.API_URL,
        },
        "payload": payload,
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def extract(city: dict, start: date, end: date, sample: bool = False,
            bronze_dir: Path | None = None) -> Path:
    payload = fake_api_response(city, start, end) if sample else fetch_city(city, start, end)
    return save_bronze(city, start, end, payload, bronze_dir)
