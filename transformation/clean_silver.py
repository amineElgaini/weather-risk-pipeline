import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "data" / "bronze" / "weather_raw.json"
OUTPUT_PATH = BASE_DIR / "data" / "silver" / "weather_silver.csv"


def process_silver_data():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    flatted_data = []

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for city in data:
        daily = city["api_response"]["daily"]
        for i in range(len(daily["time"])):
            flatted_data.append({
                "city": city["city"],
                "lat": city["lat"],
                "lng": city["lng"],
                "date": daily["time"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "precipitation_sum": daily["precipitation_sum"][i],
                "precip_prob_max": daily["precipitation_probability_max"][i],
                "wind_speed_max": daily["wind_speed_10m_max"][i],
                "wind_gusts_max": daily["wind_gusts_10m_max"][i],
                "weather_code": daily["weather_code"][i],
            })

    df = pd.DataFrame(flatted_data)

    df["city"] = df["city"].str.strip()
    df["date"] = pd.to_datetime(df["date"])

    df = df.dropna()
    df = df.drop_duplicates(subset=["city", "date"])
    df = df[df["temp_max"] >= df["temp_min"]]
    df = df[(df["precip_prob_max"] >= 0) & (df["precip_prob_max"] <= 100)]
    df = df[
        (df["precipitation_sum"] >= 0)
        & (df["wind_speed_max"] >= 0)
        & (df["wind_gusts_max"] >= 0)
    ]

    df.to_csv(OUTPUT_PATH, index=False)