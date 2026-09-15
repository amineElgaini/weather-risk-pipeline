DO $$ BEGIN
    CREATE TYPE risk_level_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS dim_cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) UNIQUE NOT NULL,
    latitude NUMERIC(8, 5) NOT NULL,
    longitude NUMERIC(8, 5) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_weather_daily (
    forecast_id SERIAL PRIMARY KEY,
    city_id INT NOT NULL REFERENCES dim_cities(city_id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    temp_max NUMERIC(4, 1),
    temp_min NUMERIC(4, 1),
    temp_range NUMERIC(4, 1),
    precipitation_sum NUMERIC(5, 1),
    precip_prob_max NUMERIC(4, 1),
    wind_speed_max NUMERIC(4, 1),
    wind_gusts_max NUMERIC(4, 1),
    is_high_wind INT,
    weather_code INT,
    risk_score NUMERIC(4, 1) NOT NULL,
    risk_level risk_level_enum NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_city_id_date UNIQUE (city_id, forecast_date)
);

CREATE TABLE IF NOT EXISTS aggregate_city_summary (
    summary_id SERIAL PRIMARY KEY,
    city_id INT UNIQUE NOT NULL REFERENCES dim_cities(city_id) ON DELETE CASCADE,
    avg_temp_max NUMERIC(4, 1),
    total_precip NUMERIC(5, 1),
    peak_wind_gust NUMERIC(4, 1),
    high_risk_days INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
