import os
import pandas as pd
import matplotlib.pyplot as plt
import pydeck as pdk
import streamlit as st
from sqlalchemy import create_engine

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & DB CONNECTION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Moroccan Weather Logistics Control Tower",
    page_icon="🚚",
    layout="wide",
)

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "weather_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

WEATHER_CODE_LABELS = {
    0: "☀️ Clear", 1: "🌤️ Mostly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
    45: "🌫️ Fog", 48: "🌫️ Fog",
    51: "🌦️ Light drizzle", 53: "🌦️ Drizzle", 55: "🌦️ Dense drizzle",
    61: "🌧️ Light rain", 63: "🌧️ Rain", 65: "🌧️ Heavy rain",
    71: "🌨️ Light snow", 73: "🌨️ Snow", 75: "🌨️ Heavy snow",
    80: "🌧️ Showers", 81: "🌧️ Showers", 82: "🌧️ Violent showers",
    95: "⛈️ Thunderstorm", 96: "⛈️ Thunderstorm+hail", 99: "⛈️ Thunderstorm+hail",
}


def weather_label(code):
    return WEATHER_CODE_LABELS.get(int(code), f"Code {int(code)}") if pd.notna(code) else "—"


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Full fact table joined to cities. At ~120 cities x a few forecast days
    this is a small dataset, so we load it once and filter in pandas."""
    query = """
        SELECT c.city_name, c.latitude, c.longitude,
               f.forecast_date, f.temp_max, f.temp_min, f.temp_range,
               f.precipitation_sum, f.precip_prob_max,
               f.wind_speed_max, f.wind_gusts_max, f.is_high_wind,
               f.weather_code, f.risk_score, f.risk_level
        FROM fact_weather_daily f
        JOIN dim_cities c ON f.city_id = c.city_id
        ORDER BY f.forecast_date ASC;
    """
    df = pd.read_sql_query(query, get_engine())
    df["forecast_date"] = pd.to_datetime(df["forecast_date"])
    df["risk_level"] = pd.Categorical(df["risk_level"], categories=["LOW", "MEDIUM", "HIGH"], ordered=True)
    df["weather_desc"] = df["weather_code"].apply(weather_label)
    return df


try:
    df = load_data()
except Exception as e:
    st.error(f"⚠️ Failed to connect to PostgreSQL. Make sure it's running.\nError: {e}")
    st.stop()

if df.empty:
    st.warning("No data available yet.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. SIDEBAR FILTERS — ville, date, période, niveau de risque
# -----------------------------------------------------------------------------
st.sidebar.title("🚚 Filtres")

search = st.sidebar.text_input("Rechercher une ville", "")
city_options = sorted(df["city_name"].unique())
if search:
    city_options = [c for c in city_options if search.lower() in c.lower()]
city_choice = st.sidebar.selectbox("Ville", ["-- Toutes les villes --"] + city_options)

min_date, max_date = df["forecast_date"].min().date(), df["forecast_date"].max().date()
date_range = st.sidebar.date_input(
    "Période (plage de dates)", (min_date, max_date), min_value=min_date, max_value=max_date
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

risk_levels = st.sidebar.multiselect(
    "Niveau de risque", ["LOW", "MEDIUM", "HIGH"], default=["LOW", "MEDIUM", "HIGH"]
)

# Apply all filters
mask = (
    df["forecast_date"].dt.date.between(start_date, end_date)
    & df["risk_level"].isin(risk_levels)
)
if city_choice != "-- Toutes les villes --":
    mask &= df["city_name"] == city_choice
filtered_df = df[mask]

# -----------------------------------------------------------------------------
# 3. REQUIRED KPIs
# -----------------------------------------------------------------------------
st.title("🇲🇦 Moroccan Weather Logistics Control Tower")
st.caption("Bronze → Silver → Gold · Open-Meteo Ingestion · PostgreSQL Warehouse")
st.markdown("---")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Nombre de villes", filtered_df["city_name"].nunique())
k2.metric("Température max.", f"{filtered_df['temp_max'].max():.1f} °C" if not filtered_df.empty else "—")
k3.metric("Précipitations max.", f"{filtered_df['precipitation_sum'].max():.1f} mm" if not filtered_df.empty else "—")
k4.metric("Périodes à risque (HIGH)", int((filtered_df["risk_level"] == "HIGH").sum()))

if not filtered_df.empty:
    top_row = filtered_df.loc[filtered_df["risk_score"].idxmax()]
    k5.metric("Ville la + à risque", top_row["city_name"], f"score {top_row['risk_score']:.0f}")
else:
    k5.metric("Ville la + à risque", "—")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. ALERTS — directly answers "où et quand être vigilant"
# -----------------------------------------------------------------------------
st.subheader("🚨 Alertes à surveiller")
alerts = (
    filtered_df[filtered_df["risk_level"].isin(["HIGH", "MEDIUM"])]
    .sort_values("risk_score", ascending=False)
    .head(10)
)
if alerts.empty:
    st.info("Aucune période à risque pour la sélection actuelle.")
else:
    st.dataframe(
        alerts[["city_name", "forecast_date", "risk_level", "risk_score", "weather_desc",
                "temp_max", "wind_gusts_max", "precipitation_sum"]]
        .rename(columns={
            "city_name": "Ville", "forecast_date": "Date", "risk_level": "Niveau",
            "risk_score": "Score", "weather_desc": "Météo", "temp_max": "Temp. max (°C)",
            "wind_gusts_max": "Rafales (km/h)", "precipitation_sum": "Précip. (mm)",
        }),
        use_container_width=True, hide_index=True,
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. MAP — one dot per city, reflects the active filters
# -----------------------------------------------------------------------------
st.subheader("🗺️ Vue réseau")
map_data = (
    filtered_df.groupby(["city_name", "latitude", "longitude"], as_index=False)
    .agg(max_risk=("risk_score", "max"), high_risk_days=("risk_level", lambda x: (x == "HIGH").sum()))
)
if map_data.empty:
    st.info("Aucune donnée pour la sélection actuelle.")
else:
    max_risk_overall = max(map_data["max_risk"].max(), 1)
    map_data["color_r"] = (map_data["max_risk"] / max_risk_overall * 255).astype(int)
    map_data["color_g"] = 255 - map_data["color_r"]

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="[longitude, latitude]",
        get_fill_color="[color_r, color_g, 40, 180]",
        get_radius=8000,
        pickable=True,
    )
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=31.5, longitude=-7.5, zoom=5),
        tooltip={"text": "{city_name}\nRisque max: {max_risk}\nJours HIGH: {high_risk_days}"},
    ))
    st.caption("Vert = risque faible · Rouge = risque élevé (selon les filtres actifs)")

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. CITY DETAIL — full engineered columns, only when one city is selected
# -----------------------------------------------------------------------------
if city_choice != "-- Toutes les villes --":
    st.subheader(f"📈 Détail — {city_choice}")
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(filtered_df["forecast_date"], filtered_df["risk_score"], marker="o", color="crimson")
    ax.set_title(f"Évolution du risque — {city_choice}")
    ax.set_ylabel("Risk Score (0-100)")
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=45)
    fig.tight_layout()
    st.pyplot(fig)

    st.dataframe(
        filtered_df[["forecast_date", "temp_max", "temp_min", "temp_range", "precipitation_sum",
                     "precip_prob_max", "wind_speed_max", "wind_gusts_max", "is_high_wind",
                     "weather_desc", "risk_score", "risk_level"]]
        .rename(columns={
            "forecast_date": "Date", "temp_max": "Temp max", "temp_min": "Temp min",
            "temp_range": "Amplitude", "precipitation_sum": "Précip.", "precip_prob_max": "Prob. précip. (%)",
            "wind_speed_max": "Vent max", "wind_gusts_max": "Rafales max", "is_high_wind": "Vent fort",
            "weather_desc": "Météo", "risk_score": "Score", "risk_level": "Niveau",
        }),
        use_container_width=True, hide_index=True,
    )
else:
    st.subheader("📋 Détail par ville et par jour")
    st.dataframe(
        filtered_df[["city_name", "forecast_date", "temp_max", "precipitation_sum",
                     "wind_gusts_max", "weather_desc", "risk_score", "risk_level"]]
        .sort_values("risk_score", ascending=False)
        .rename(columns={
            "city_name": "Ville", "forecast_date": "Date", "temp_max": "Temp max",
            "precipitation_sum": "Précip.", "wind_gusts_max": "Rafales", "weather_desc": "Météo",
            "risk_score": "Score", "risk_level": "Niveau",
        }),
        use_container_width=True, hide_index=True,
    )

# -----------------------------------------------------------------------------
# 7. EXPORT
# -----------------------------------------------------------------------------
csv_data = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Exporter la sélection (CSV)", csv_data, "weather_filtered.csv", "text/csv")