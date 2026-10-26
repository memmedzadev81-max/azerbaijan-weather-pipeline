"""Central configuration for the pipeline."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
WAREHOUSE_PATH = DATA_DIR / "warehouse.db"
SQL_DIR = PROJECT_ROOT / "sql"

# Source: Open-Meteo Historical Weather API (free, no API key required)
API_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]
TIMEZONE = "Asia/Baku"

# The archive API publishes data with a delay of a few days.
ARCHIVE_LAG_DAYS = 5
# Used on the very first run when no watermark exists yet.
DEFAULT_START_DATE = "2026-01-01"

CITIES = [
    {"city_id": 1, "city_name": "Baku", "latitude": 40.4093, "longitude": 49.8671},
    {"city_id": 2, "city_name": "Ganja", "latitude": 40.6828, "longitude": 46.3606},
    {"city_id": 3, "city_name": "Sumgait", "latitude": 40.5897, "longitude": 49.6686},
    {"city_id": 4, "city_name": "Lankaran", "latitude": 38.7543, "longitude": 48.8506},
    {"city_id": 5, "city_name": "Shaki", "latitude": 41.1975, "longitude": 47.1706},
]

# Plausible value ranges used by the data quality checks.
VALID_RANGES = {
    "temperature_c": (-40.0, 55.0),
    "relative_humidity_pct": (0.0, 100.0),
    "precipitation_mm": (0.0, 300.0),
    "wind_speed_kmh": (0.0, 250.0),
}
