import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "silver" / "weather_silver.csv"

WEATHER_DAILY_RISK_PATH = BASE_DIR / "data" / "bronze" / "weather_daily_risk.csv"
WEATHER_DAILY_SUMMARY_PATH = BASE_DIR / "data" / "bronze" / "weather_city_summary.csv"

WEATHER_DAILY_RISK_PATH.parent.mkdir(parents=True, exist_ok=True)
WEATHER_DAILY_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)
weather_daily_risk = []
weather_daily_summary = []

def categorize_risk(row):
    if (
        row["precipitation_sum"] > 10
        or row["wind_gusts_max"] > 50
        or row["weather_code"] >= 85
    ):
        return "HIGH"

    if (
        row["precipitation_sum"] > 5
        or row["wind_gusts_max"] > 35
        or row["precip_prob_max"] > 70
    ):
        return "MEDIUM"

    return "LOW"


df["risk_level"] = df.apply(categorize_risk, axis=1)
df["temp_range"] = (df["temp_max"] - df["temp_min"]).round(1)
df["is_high_wind"] = (df["wind_speed_max"] > 30).astype(int)

city_summary = df.groupby("city").agg(
    avg_temp_max=("temp_max", lambda x: round(x.mean(), 1)),
    total_precip=("precipitation_sum", lambda x: round(x.sum(), 1)),
    peak_wind_gust=("wind_gusts_max", "max"),
    high_risk_days=("risk_level", lambda x: (x == "HIGH").sum())
).reset_index()

df.to_csv(GOLD_DIR / "weather_daily_risk.csv", index=False)

city_summary.to_csv(GOLD_DIR / "weather_city_summary.csv", index=False)