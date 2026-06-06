"""
AQI Intelligence Platform — Unified Data Pipeline
Fetches real-time AQI (WAQI) + Weather (OpenWeatherMap) data for 5 Indian cities.
Outputs:
  - data/raw/aqi_raw.csv          → raw AQI data
  - data/raw/weather_raw.csv      → raw weather data
  - data/processed/aqi_weather_merged.csv → cleaned, merged dataset
"""

from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import requests
import pandas as pd
import schedule
import time

load_dotenv()

# ── API keys ─────────────────────────────────────────────────────────────────
WAQI_TOKEN = os.getenv("WAQI_TOKEN")
OWM_API_KEY = os.getenv("OWM_API_KEY")

# ── City config ───────────────────────────────────────────────────────────────
# waqi_id  : WAQI station identifier (use station ID where city name gives stale data)
# owm_city : OpenWeatherMap city string (city,country-code)
CITIES = [
    {"name": "Mumbai",  "waqi_id": "mumbai",  "owm_city": "Mumbai,IN"},
    {"name": "Delhi",   "waqi_id": "delhi",   "owm_city": "Delhi,IN"},
    {"name": "Pune",    "waqi_id": "@7567",   "owm_city": "Pune,IN"},
    {"name": "Chennai", "waqi_id": "chennai", "owm_city": "Chennai,IN"},
    {"name": "Kolkata", "waqi_id": "kolkata", "owm_city": "Kolkata,IN"},
]

STALE_THRESHOLD_HOURS = 24  # Mark data older than this as stale


# ── CSV append helper ─────────────────────────────────────────────────────────
def append_csv(df: pd.DataFrame, filepath: str):
    """
    Append new rows to a CSV file. Writes header only on first run.
    This builds up historical data across every pipeline run instead of
    overwriting — critical for time-series forecasting in Phase 3.
    """
    file_exists = os.path.isfile(filepath)
    df.to_csv(filepath, mode="a", header=not file_exists, index=False)


# ── AQI fetcher ───────────────────────────────────────────────────────────────
def get_aqi_data(city: dict) -> dict | None:
    """Fetch real-time AQI data from WAQI for a given city."""
    url = f"https://api.waqi.info/feed/{city['waqi_id']}/?token={WAQI_TOKEN}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  [AQI] Network error for {city['name']}: {e}")
        return None

    if data.get("status") != "ok":
        print(f"  [AQI] Bad response for {city['name']}: {data.get('data', 'unknown error')}")
        return None

    d = data["data"]
    recorded_at = d["time"]["s"]  # Original station timestamp (WAQI local time string)
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Staleness check: compare recorded year/date loosely
    try:
        recorded_dt = datetime.strptime(recorded_at, "%Y-%m-%d %H:%M:%S")
        age_hours = (datetime.now() - recorded_dt).total_seconds() / 3600
        is_stale = age_hours > STALE_THRESHOLD_HOURS
    except ValueError:
        is_stale = True  # Can't parse → treat as stale

    # Individual pollutant concentrations (if available)
    iaqi = d.get("iaqi", {})

    return {
        "city":               city["name"],
        "aqi":                d["aqi"],
        "dominant_pollutant": d.get("dominentpol", "unknown"),
        "pm25":               iaqi.get("pm25", {}).get("v"),
        "pm10":               iaqi.get("pm10", {}).get("v"),
        "no2":                iaqi.get("no2", {}).get("v"),
        "o3":                 iaqi.get("o3", {}).get("v"),
        "co":                 iaqi.get("co", {}).get("v"),
        "so2":                iaqi.get("so2", {}).get("v"),
        "recorded_at":        recorded_at,
        "fetched_at":         fetched_at,
        "is_stale":           is_stale,
    }


# ── Weather fetcher ────────────────────────────────────────────────────────────
def get_weather_data(city: dict) -> dict | None:
    """
    Fetch current weather from OpenWeatherMap for a given city.
    Fields collected (research-backed for AQI correlation):
      - temperature, humidity         → thermal inversions trap pollutants
      - wind_speed, wind_direction    → disperses or concentrates particulates
      - pressure                      → low pressure = pollutants stay grounded
      - weather_condition             → rain washes PM2.5; fog amplifies it
      - visibility                    → direct proxy for particulate density
      - dew_point (derived)           → indicates moisture that affects PM formation
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q":     city["owm_city"],
        "appid": OWM_API_KEY,
        "units": "metric",   # Celsius, m/s
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  [Weather] Network error for {city['name']}: {e}")
        return None

    if data.get("cod") != 200:
        print(f"  [Weather] Bad response for {city['name']}: {data.get('message', 'unknown')}")
        return None

    main    = data.get("main", {})
    wind    = data.get("wind", {})
    weather = data.get("weather", [{}])[0]
    sys     = data.get("sys", {})

    temp_c    = main.get("temp")
    humidity  = main.get("humidity")

    # Dew point approximation (Magnus formula) — useful for PM2.5 hygroscopic growth
    dew_point = None
    if temp_c is not None and humidity is not None:
        a, b = 17.27, 237.7
        alpha    = (a * temp_c / (b + temp_c)) + (humidity / 100.0) ** 0.5 / a
        # Simpler reliable formula:
        dew_point = round(temp_c - ((100 - humidity) / 5), 2)

    return {
        "city":              city["name"],
        "temp_c":            temp_c,
        "feels_like_c":      main.get("feels_like"),
        "humidity_pct":      humidity,
        "dew_point_c":       dew_point,
        "pressure_hpa":      main.get("pressure"),
        "wind_speed_ms":     wind.get("speed"),
        "wind_direction_deg":wind.get("deg"),
        "wind_gust_ms":      wind.get("gust"),
        "visibility_m":      data.get("visibility"),
        "weather_main":      weather.get("main"),        # e.g. "Rain", "Fog", "Clear"
        "weather_desc":      weather.get("description"), # e.g. "light rain"
        "cloud_cover_pct":   data.get("clouds", {}).get("all"),
        "sunrise_utc":       pd.to_datetime(sys.get("sunrise"), unit="s", utc=True),
        "sunset_utc":        pd.to_datetime(sys.get("sunset"),  unit="s", utc=True),
        "weather_fetched_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── AQI category helper ────────────────────────────────────────────────────────
def aqi_category(aqi: int) -> str:
    """Map AQI value to WHO/US-EPA category label."""
    if aqi is None:
        return "Unknown"
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Moderate"
    if aqi <= 150:  return "Unhealthy for Sensitive Groups"
    if aqi <= 200:  return "Unhealthy"
    if aqi <= 300:  return "Very Unhealthy"
    return "Hazardous"


# ── Main pipeline ─────────────────────────────────────────────────────────────
def run_pipeline():
    print("=" * 55)
    print("  AQI Intelligence Platform — Data Pipeline")
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    aqi_records     = []
    weather_records = []

    for city in CITIES:
        print(f"\n→ {city['name']}")

        # AQI
        aqi_data = get_aqi_data(city)
        if aqi_data:
            aqi_records.append(aqi_data)
            stale_flag = " [STALE]" if aqi_data["is_stale"] else ""
            print(f"  [AQI]     AQI={aqi_data['aqi']} | "
                  f"Pollutant={aqi_data['dominant_pollutant']} | "
                  f"Recorded={aqi_data['recorded_at']}{stale_flag}")
        else:
            print(f"  [AQI]     FAILED")

        # Weather
        weather_data = get_weather_data(city)
        if weather_data:
            weather_records.append(weather_data)
            print(f"  [Weather] {weather_data['temp_c']}°C | "
                  f"Humidity={weather_data['humidity_pct']}% | "
                  f"Wind={weather_data['wind_speed_ms']}m/s | "
                  f"Condition={weather_data['weather_main']}")
        else:
            print(f"  [Weather] FAILED")

    # ── Build DataFrames ──────────────────────────────────────────────────────
    aqi_df     = pd.DataFrame(aqi_records)
    weather_df = pd.DataFrame(weather_records)

    # ── Save raw files ────────────────────────────────────────────────────────
    os.makedirs("data/raw",       exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)

    append_csv(aqi_df,     "data/raw/aqi_raw.csv")
    append_csv(weather_df, "data/raw/weather_raw.csv")
    print(f"\n✔  Appended → data/raw/aqi_raw.csv")
    print(f"✔  Appended → data/raw/weather_raw.csv")

    # ── Merge on city ─────────────────────────────────────────────────────────
    merged_df = pd.merge(aqi_df, weather_df, on="city", how="inner")

    # ── Enrich merged data ────────────────────────────────────────────────────
    merged_df["aqi_category"] = merged_df["aqi"].apply(aqi_category)

    # Wind direction: degrees → cardinal (N/NE/E/SE/S/SW/W/NW)
    def deg_to_cardinal(deg):
        if deg is None or pd.isna(deg):
            return None
        directions = ["N","NE","E","SE","S","SW","W","NW"]
        return directions[int((deg + 22.5) / 45) % 8]

    merged_df["wind_cardinal"] = merged_df["wind_direction_deg"].apply(deg_to_cardinal)

    # Visibility: metres → kilometres (rounded)
    merged_df["visibility_km"] = (merged_df["visibility_m"] / 1000).round(2)

    # Reorder columns for readability
    col_order = [
        "city", "recorded_at", "fetched_at", "is_stale",
        "aqi", "aqi_category", "dominant_pollutant",
        "pm25", "pm10", "no2", "o3", "co", "so2",
        "temp_c", "feels_like_c", "humidity_pct", "dew_point_c",
        "pressure_hpa", "wind_speed_ms", "wind_direction_deg",
        "wind_cardinal", "wind_gust_ms",
        "visibility_m", "visibility_km",
        "weather_main", "weather_desc", "cloud_cover_pct",
        "sunrise_utc", "sunset_utc", "weather_fetched_at",
    ]
    # Only keep columns that exist (some OWM fields may be absent)
    col_order = [c for c in col_order if c in merged_df.columns]
    merged_df = merged_df[col_order]

    append_csv(merged_df, "data/processed/aqi_weather_merged.csv")
    print(f"✔  Appended → data/processed/aqi_weather_merged.csv")

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    summary_cols = ["city", "aqi", "aqi_category", "dominant_pollutant",
                    "temp_c", "humidity_pct", "wind_speed_ms", "weather_main"]
    summary_cols = [c for c in summary_cols if c in merged_df.columns]
    print(merged_df[summary_cols].to_string(index=False))
    print("=" * 55)

    return merged_df


if __name__ == "__main__":
    print("Starting AQI Intelligence Platform pipeline...")
    print("Scheduled to run every 6 hours. Press Ctrl+C to stop.\n")

    run_pipeline()                        # Run once immediately on start

    schedule.every(6).hours.do(run_pipeline)

    while True:
        schedule.run_pending()
        time.sleep(60)                    # Check every minute if a job is due