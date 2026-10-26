"""Deterministic fake API responses.

Lets you run and test the whole pipeline without internet access. The output
has exactly the same shape as a real Open-Meteo response, including a few
deliberately "dirty" values (nulls) so the cleaning step has work to do.
"""
import math
import random
from datetime import date, datetime, timedelta


def fake_api_response(city: dict, start: date, end: date) -> dict:
    rng = random.Random(f"{city['city_id']}-{start}-{end}")
    times, temp, hum, precip, wind = [], [], [], [], []
    day = start
    while day <= end:
        doy = day.timetuple().tm_yday
        seasonal = 15 + 12 * math.sin((doy - 105) / 365 * 2 * math.pi)
        for hour in range(24):
            ts = datetime(day.year, day.month, day.day, hour)
            times.append(ts.strftime("%Y-%m-%dT%H:%M"))
            daily = 4 * math.sin((hour - 9) / 24 * 2 * math.pi)
            temp.append(round(seasonal + daily + rng.uniform(-2, 2) - city["city_id"] * 0.3, 1))
            hum.append(round(min(100, max(10, 65 - daily * 3 + rng.uniform(-10, 10))), 0))
            precip.append(round(rng.choice([0, 0, 0, 0, 0, 0, 0.2, 0.5, 1.4]), 1))
            wind.append(round(abs(rng.gauss(14, 6)), 1))
        day += timedelta(days=1)

    # Inject some missing values like real sensor data has.
    for series in (temp, hum, precip, wind):
        for _ in range(max(1, len(series) // 200)):
            series[rng.randrange(len(series))] = None
    # ...and a few impossible sensor readings that the cleaning step must catch.
    for _ in range(max(1, len(temp) // 500)):
        temp[rng.randrange(len(temp))] = 999.0
        hum[rng.randrange(len(hum))] = -5.0

    return {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "timezone": "Asia/Baku",
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": times,
            "temperature_2m": temp,
            "relative_humidity_2m": hum,
            "precipitation": precip,
            "wind_speed_10m": wind,
        },
    }
