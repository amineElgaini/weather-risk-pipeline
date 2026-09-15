import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "silver" / "weather_silver.csv"

WEATHER_DAILY_RISK_PATH = BASE_DIR / "data" / "gold" / "weather_daily_risk.csv"
WEATHER_DAILY_SUMMARY_PATH = BASE_DIR / "data" / "gold" / "weather_city_summary.csv"

WEATHER_DAILY_RISK_PATH.parent.mkdir(parents=True, exist_ok=True)
WEATHER_DAILY_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)

# def compute_risk_score(row):
#     precip_score = min(35, (row["precipitation_sum"] / 20.0) * 35)

#     wind_score = min(35, (row["wind_gusts_max"] / 70.0) * 35)

#     temp_score = 0
#     if row["temp_max"] >= 40 or row["temp_min"] <= 2:
#         temp_score = 15
#     elif row["temp_max"] >= 35 or row["temp_min"] <= 5:
#         temp_score = 8

#     code_score = 15 if row["weather_code"] >= 80 else 0

#     total_score = round(precip_score + wind_score + temp_score + code_score, 1)
#     return min(100.0, total_score)


def compute_risk_score(row):
    # 1. Precipitation Score (capped at 35)
    precip_score = min(35.0, (row["precipitation_sum"] / 20.0) * 35.0)

    # 2. Wind Score (capped at 35)
    wind_score = min(35.0, (row["wind_gusts_max"] / 70.0) * 35.0)

    # 3. Dynamic Temperature Score (Scales continuously up to a cap)
    heat_score = max(0.0, (row["temp_max"] - 30.0) / (50.0 - 30.0) * 20.0)
    cold_score = max(0.0, (5.0 - row["temp_min"]) / (5.0 - (-5.0)) * 20.0)

    # Take the worse extreme (heat or cold) or cap their combined effect
    temp_score = min(30.0, heat_score + cold_score)

    # 4. Weather Code Hazard Score
    code_score = 15.0 if row["weather_code"] >= 80 else 0.0

    # 5. Total Score (capped at 100.0)
    total_score = round(precip_score + wind_score + temp_score + code_score, 1)
    return min(100.0, total_score)

df["risk_score"] = df.apply(compute_risk_score, axis=1)
df["risk_level"] = pd.cut(
    df["risk_score"],
    bins=[-1, 30, 60, 100],
    labels=["LOW", "MEDIUM", "HIGH"],
)

df["temp_range"] = (df["temp_max"] - df["temp_min"]).round(1)
df["is_high_wind"] = (df["wind_speed_max"] > 30).astype(int)

city_summary = df.groupby("city").agg(
    avg_temp_max=("temp_max", lambda x: round(x.mean(), 1)),
    total_precip=("precipitation_sum", lambda x: round(x.sum(), 1)),
    peak_wind_gust=("wind_gusts_max", "max"),
    high_risk_days=("risk_level", lambda x: (x == "HIGH").sum())
).reset_index()

df.to_csv(WEATHER_DAILY_RISK_PATH, index=False)
city_summary.to_csv(WEATHER_DAILY_SUMMARY_PATH, index=False)