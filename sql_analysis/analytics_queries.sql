-- =============================================================================
-- MOROCCAN WEATHER LOGISTICS PIPELINE - STEP 4: ANALYTICAL QUERIES
-- Database: PostgreSQL
-- Schema: dim_cities, fact_weather_daily, aggregate_city_summary
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: Critical Dispatch Alerts (High-Risk Hubs)
-- Business Goal: Identify immediate logistics hazards where trucks need 
-- rerouting or specialized weather-delayed window handling.
-- -----------------------------------------------------------------------------
SELECT 
    c.city_name,
    f.forecast_date,
    f.risk_score,
    f.risk_level,
    f.wind_gusts_max,
    f.precipitation_sum,
    f.weather_code
FROM fact_weather_daily f
JOIN dim_cities c ON f.city_id = c.city_id
WHERE f.risk_level = 'HIGH'
ORDER BY f.forecast_date ASC, f.risk_score DESC;


-- -----------------------------------------------------------------------------
-- QUERY 2: 7-Day Moving Average Risk Score Trajectory (Window Function)
-- Business Goal: Smoothen daily weather spikes to observe regional weather 
-- trends across key transport corridors.
-- -----------------------------------------------------------------------------
SELECT 
    c.city_name,
    f.forecast_date,
    f.risk_score,
    ROUND(
        AVG(f.risk_score) OVER (
            PARTITION BY f.city_id 
            ORDER BY f.forecast_date 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 1
    ) AS rolling_3day_avg_risk
FROM fact_weather_daily f
JOIN dim_cities c ON f.city_id = c.city_id
ORDER BY c.city_name, f.forecast_date;


-- -----------------------------------------------------------------------------
-- QUERY 3: Worst Single Forecast Day Per City (CTE + Window Ranking)
-- Business Goal: Pinpoint the single highest-risk dispatch day for every city 
-- to assist regional fleet managers in resource allocation.
-- -----------------------------------------------------------------------------
WITH RankedForecasts AS (
    SELECT 
        c.city_name,
        f.forecast_date,
        f.risk_score,
        f.risk_level,
        f.wind_gusts_max,
        f.precipitation_sum,
        RANK() OVER (
            PARTITION BY f.city_id 
            ORDER BY f.risk_score DESC, f.forecast_date ASC
        ) AS risk_rank
    FROM fact_weather_daily f
    JOIN dim_cities c ON f.city_id = c.city_id
)
SELECT 
    city_name,
    forecast_date AS peak_risk_date,
    risk_score AS max_risk_score,
    risk_level,
    wind_gusts_max,
    precipitation_sum
FROM RankedForecasts
WHERE risk_rank = 1
ORDER BY max_risk_score DESC;


-- -----------------------------------------------------------------------------
-- QUERY 4: Precipitation Anomaly Detection (Subquery / Scalar Comparison)
-- Business Goal: Detect specific days where rainfall exceeds the city's overall
-- average rainfall by a factor of 1.5x (Unusual localized flooding risk).
-- -----------------------------------------------------------------------------
SELECT 
    c.city_name,
    f.forecast_date,
    f.precipitation_sum,
    s.total_precip AS city_total_period_precip,
    f.risk_score
FROM fact_weather_daily f
JOIN dim_cities c ON f.city_id = c.city_id
JOIN aggregate_city_summary s ON f.city_id = s.city_id
WHERE f.precipitation_sum > (
    SELECT AVG(precipitation_sum) * 1.5 
    FROM fact_weather_daily 
    WHERE precipitation_sum > 0
)
ORDER BY f.precipitation_sum DESC;


-- -----------------------------------------------------------------------------
-- QUERY 5: National Logistics Risk Scorecard (Aggregations & Ratios)
-- Business Goal: Executive-level summary showing overall network safety metrics 
-- across all monitored hubs in Morocco.
-- -----------------------------------------------------------------------------
SELECT 
    c.city_name,
    COUNT(f.forecast_id) AS total_forecast_days,
    ROUND(AVG(f.risk_score), 1) AS avg_national_risk_score,
    COUNT(CASE WHEN f.risk_level = 'HIGH' THEN 1 END) AS high_risk_days_count,
    COUNT(CASE WHEN f.risk_level = 'MEDIUM' THEN 1 END) AS medium_risk_days_count,
    COUNT(CASE WHEN f.risk_level = 'LOW' THEN 1 END) AS low_risk_days_count,
    MAX(f.wind_gusts_max) AS max_wind_gust_kmh,
    SUM(f.precipitation_sum) AS total_rainfall_mm
FROM fact_weather_daily f
JOIN dim_cities c ON f.city_id = c.city_id
GROUP BY c.city_id, c.city_name
ORDER BY high_risk_days_count DESC, avg_national_risk_score DESC;