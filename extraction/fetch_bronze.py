import requests
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# ---------Performance Tracking-----------
import time
start = time.perf_counter()
# --------------------

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(__file__).parent / "ma.csv"
OUTPUT_PATH = BASE_DIR / "data" / "bronze" / "weather_raw.json"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

data = pd.read_csv(CSV_PATH, usecols=["city", "lat", "lng"])

results = []

def fetch_weather(row):

    params = {
        "latitude": row.lat,
        "longitude": row.lng,

        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "weather_code"
        ]),

        "forecast_days": 7,
        "timezone": "Africa/Casablanca"
    }

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=10
        )

        response.raise_for_status()

        weather = response.json()

    except requests.exceptions.RequestException as e:
        print(f"Failed fetching '{row.city}': {e}")
        return None

    return {
        "city": row.city,
        "lat": row.lat,
        "lng": row.lng,
        "fetched_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "api_response": weather
    }

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(
        fetch_weather,
        data.itertuples(index=False)
    ))

results = [result for result in results if result is not None]
  
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved {len(results)} cities to {OUTPUT_PATH}")

# ----------Performance Tracking----------
end = time.perf_counter()
print(f"Execution time: {end - start:.2f} seconds")
# --------------------