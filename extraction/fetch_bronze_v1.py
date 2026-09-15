import requests
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

start = time.perf_counter()

file_path = Path(__file__).parent / "ma.csv"
output_path = Path(__file__).resolve().parent.parent / "data" / "weather_raw2.json"

data = pd.read_csv(
    file_path,
    usecols=["city", "lat", "lng"]
)

results = []

for row in data.itertuples(index=False):

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

    except Exception as e:
        print(f"Failed fetching '{row.city}': {e}")
        continue

    results.append({
        "city": row.city,
        "lat": row.lat,
        "lng": row.lng,
        "fetched_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "api_response": weather
    })

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

end = time.perf_counter()

print(f"Saved {len(results)} cities to {output_path}")
print(f"Execution time: {end - start:.2f} seconds")