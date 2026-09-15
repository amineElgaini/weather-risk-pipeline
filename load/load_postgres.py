import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_DIR = BASE_DIR / "data" / "gold"
SCHEMA_PATH = BASE_DIR / "load" / "schema.sql"

# Connection Settings
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "weather_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def load_to_postgres():
    engine = create_engine(DATABASE_URL)

    # 1. Initialize DB Schema
    print("Initializing PostgreSQL schema with surrogate keys and indexes...")
    with engine.connect() as conn:
        with open(SCHEMA_PATH, "r") as f:
            conn.execute(text(f.read()))
        conn.commit()
    print("✔ Database schema ready.")

    # 2. Read Gold Data
    daily_df = pd.read_csv(GOLD_DIR / "weather_daily_risk.csv")
    summary_df = pd.read_csv(GOLD_DIR / "weather_city_summary.csv")

    with engine.connect() as conn:
        # Step A: Insert/Upsert Cities into dim_cities
        print("Upserting dim_cities...")
        cities_df = daily_df[["city", "lat", "lng"]].drop_duplicates()
        for _, row in cities_df.iterrows():
            conn.execute(
                text("""
                INSERT INTO dim_cities (city_name, latitude, longitude)
                VALUES (:city, :lat, :lng)
                ON CONFLICT (city_name) DO UPDATE 
                SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude;
            """),
                {"city": row["city"], "lat": row["lat"], "lng": row["lng"]},
            )
        conn.commit()

        # Step B: Retrieve City Name -> City ID Mapping
        city_map = dict(
            conn.execute(
                text("SELECT city_name, city_id FROM dim_cities")
            ).fetchall()
        )

        # Map integer city_id to dataframes
        daily_df["city_id"] = daily_df["city"].map(city_map)
        summary_df["city_id"] = summary_df["city"].map(city_map)

        # Step C: Upsert fact_weather_daily using city_id
        print("Upserting fact_weather_daily with Integer FKs...")
        for _, row in daily_df.iterrows():
            conn.execute(
                text("""
                INSERT INTO fact_weather_daily (
                    city_id, forecast_date, temp_max, temp_min, temp_range,
                    precipitation_sum, precip_prob_max, wind_speed_max, wind_gusts_max,
                    is_high_wind, weather_code, risk_score, risk_level, updated_at
                ) VALUES (
                    :city_id, :date, :temp_max, :temp_min, :temp_range,
                    :precipitation_sum, :precip_prob_max, :wind_speed_max, :wind_gusts_max,
                    :is_high_wind, :weather_code, :risk_score, :risk_level, CURRENT_TIMESTAMP
                )
                ON CONFLICT (city_id, forecast_date) DO UPDATE SET
                    temp_max = EXCLUDED.temp_max,
                    temp_min = EXCLUDED.temp_min,
                    temp_range = EXCLUDED.temp_range,
                    precipitation_sum = EXCLUDED.precipitation_sum,
                    precip_prob_max = EXCLUDED.precip_prob_max,
                    wind_speed_max = EXCLUDED.wind_speed_max,
                    wind_gusts_max = EXCLUDED.wind_gusts_max,
                    is_high_wind = EXCLUDED.is_high_wind,
                    weather_code = EXCLUDED.weather_code,
                    risk_score = EXCLUDED.risk_score,
                    risk_level = EXCLUDED.risk_level,
                    updated_at = CURRENT_TIMESTAMP;
            """),
                row.to_dict(),
            )

        # Step D: Upsert aggregate_city_summary using city_id
        print("Upserting aggregate_city_summary with Integer FKs...")
        for _, row in summary_df.iterrows():
            conn.execute(
                text("""
                INSERT INTO aggregate_city_summary (
                    city_id, avg_temp_max, total_precip, peak_wind_gust, high_risk_days, updated_at
                ) VALUES (
                    :city_id, :avg_temp_max, :total_precip, :peak_wind_gust, :high_risk_days, CURRENT_TIMESTAMP
                )
                ON CONFLICT (city_id) DO UPDATE SET
                    avg_temp_max = EXCLUDED.avg_temp_max,
                    total_precip = EXCLUDED.total_precip,
                    peak_wind_gust = EXCLUDED.peak_wind_gust,
                    high_risk_days = EXCLUDED.high_risk_days,
                    updated_at = CURRENT_TIMESTAMP;
            """),
                row.to_dict(),
            )

        conn.commit()
    print("✔ All Gold data successfully loaded into PostgreSQL!")


if __name__ == "__main__":
    load_to_postgres()