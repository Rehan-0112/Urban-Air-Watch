# 🌫️ Urban Air Watch

> Tracks real-time AQI and weather across Indian cities, with machine learning forecasts and an interactive dashboard for pollution analysis.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.0-150458?style=flat-square&logo=pandas)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square&logo=streamlit)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-ML-F7931E?style=flat-square&logo=scikit-learn)
![Prophet](https://img.shields.io/badge/Prophet-Forecasting-0072C6?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)

---

## 📌 What This Does

This platform automatically collects real-time AQI and weather data for **Mumbai, Delhi, Pune, Chennai, and Kolkata** every 6 hours, merges it into a structured dataset, and feeds it into machine learning models that forecast pollution levels 24 hours ahead and classify health risk in real time.

The interactive dashboard lets users explore city-level trends, view anomaly spikes, and simulate how changing weather conditions affect air quality — all without touching a line of code.

---

## 🔴 Live Demo
> Coming soon — deploying to Hugging Face Spaces in Phase 5

---

## 📊 Key Insights from Real Data *(April–June 2026)*

- **PM2.5 is the dominant pollutant in 83% of all readings** across all cities
- **Mumbai has the highest average AQI at 122.6** — consistently in the Unhealthy range
- **Delhi peaked at AQI 157 (Unhealthy)** on June 3, 2026 at 11 PM
- **Mumbai peaked at AQI 160 (Unhealthy)** — recorded during haze conditions
- **Haze correlates with higher pollution** — average AQI of 104.7 during haze vs 90.4 on clear/cloudy days
- **Wind speed shows negative correlation with AQI (r = -0.31)** — higher winds disperse pollutants
- **Humidity shows negative correlation with AQI (r = -0.27)** — drier conditions trend toward worse pollution
- **Chennai and Kolkata are comparatively cleaner** — averaging AQI 70.8 and 69.8 respectively

---

## 🗺️ Cities Covered

| City | Avg AQI | Peak AQI | Dominant Pollutant | Data Status |
|------|---------|----------|--------------------|-------------|
| Mumbai | 122.6 | 160 | PM2.5 | ✅ Live |
| Delhi | 101.5 | 157 | PM2.5 / PM10 | ✅ Live |
| Chennai | 70.8 | 80 | PM2.5 | ✅ Live |
| Kolkata | 69.8 | 103 | PM2.5 | ✅ Live |
| Pune | — | — | — | ⚠️ Stale — see note below |

> **Data quality note:** Pune's WAQI monitoring station was found to be returning data timestamped January 2021 — over 5 years old. This was caught automatically by the pipeline's `is_stale` flag which marks any reading older than 24 hours. Pune rows are excluded from all analysis and ML training. The city will be replaced with Bengaluru once a reliable station ID is confirmed.

---

## 🧱 Project Structure

```
aqi-project/
├── data/
│   ├── raw/
│   │   ├── aqi_raw.csv               ← raw AQI data (appended every run)
│   │   └── weather_raw.csv           ← raw weather data (appended every run)
│   └── processed/
│       ├── aqi_weather_merged.csv    ← merged dataset (growing daily)
│       └── aqi_clean.csv             ← outliers removed, features engineered
├── notebooks/
│   ├── eda.ipynb                     ← exploratory data analysis
│   └── model_experiments.ipynb      ← model comparison and evaluation
├── src/
│   ├── data_pipeline.py             ← fetches AQI + weather, merges, saves
│   ├── clean_data.py                ← handles nulls, outliers, feature engineering
│   ├── train_model.py               ← baseline LR + Prophet + Random Forest
│   └── anomaly_detection.py        ← Isolation Forest spike detection
├── dashboard/
│   └── app.py                       ← Streamlit interactive dashboard
├── models/
│   ├── baseline_lr.pkl
│   ├── health_risk_rf.pkl
│   └── anomaly_detector.pkl
├── images/
│   └── [EDA charts + dashboard screenshots]
├── tests/
│   └── test_pipeline.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ How to Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/Rehan-0112/urban-air-watch.git
cd urban-air-watch
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up API keys
```bash
cp .env.example .env
```
Open `.env` and add your keys:
```
WAQI_TOKEN=your_waqi_key_here
OWM_API_KEY=your_openweathermap_key_here
```
Get free keys from:
- WAQI: https://aqicn.org/data-platform/token/
- OpenWeatherMap: https://openweathermap.org/api

### 5. Run the data pipeline
```bash
python src/data_pipeline.py
```
Fetches live AQI + weather for all cities and appends to `data/raw/` and `data/processed/`.
Press `Ctrl+C` after the summary table appears to stop the scheduler.

### 6. Launch the dashboard *(Phase 4)*
```bash
streamlit run dashboard/app.py
```

---

## 🔁 Data Pipeline Architecture

```
WAQI API ──────────┐
                   ├──► data_pipeline.py ──► aqi_weather_merged.csv ──► clean_data.py ──► ML Models
OpenWeatherMap ────┘
```

- Runs every 6 hours automatically via `schedule`
- **Appends** new rows — never overwrites historical data
- Flags stale data (`recorded_at` > 24 hours ago) automatically
- Collects 13 weather features per city including dew point, wind cardinal direction, and visibility
- Derives `aqi_category` (Good → Hazardous) and `wind_cardinal` (N/NE/E...) on the fly

---

## 🤖 Machine Learning Models

| Model | Purpose | Metric | Status |
|-------|---------|--------|--------|
| Linear Regression | AQI baseline forecast | RMSE, R² | 🔜 Phase 3 |
| Facebook Prophet | 24-hour AQI forecasting | RMSE, MAE | 🔜 Phase 3 |
| Random Forest Classifier | Health risk classification | Accuracy, F1 | 🔜 Phase 3 |
| Isolation Forest | Anomaly / spike detection | Precision | 🔜 Phase 3 |

---

## 📈 Dashboard Pages *(Phase 4)*

- **Live Overview** — AQI cards for all cities, colour-coded by severity (green → maroon)
- **City Deep Dive** — AQI trends over time, pollutant breakdown, weather correlations
- **24-Hour Forecast** — Prophet prediction chart with uncertainty band
- **Anomaly Explorer** — historical pollution spikes highlighted on a timeline
- **What-If Simulator** — adjust temperature, humidity, wind sliders → Random Forest predicts AQI category in real time

---

## 🛠️ Tech Stack

| Layer | Tools |
|-------|-------|
| Data Collection | Python, Requests, WAQI API, OpenWeatherMap API |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn, Prophet, XGBoost |
| Dashboard | Streamlit, Plotly |
| Deployment | Hugging Face Spaces |
| Version Control | Git, GitHub |

---

## 🔐 Environment Variables

Create a `.env` file in the project root. See `.env.example` for the template.

```
WAQI_TOKEN=        # from aqicn.org
OWM_API_KEY=       # from openweathermap.org
```

Never commit your `.env` file — it is listed in `.gitignore`.

---

## 📅 Development Roadmap

- ✅ Phase 1 — Automated data pipeline (AQI + weather, 6-hourly, historical append)
- 🔜 Phase 2 — Data cleaning and EDA (6 visualisations)
- 🔜 Phase 3 — ML models (forecasting, classification, anomaly detection)
- 🔜 Phase 4 — Streamlit dashboard (5 pages)
- 🔜 Phase 5 — Hugging Face deployment and GitHub polish

---

## 👤 Author

**Rehan Shaikh**
2nd Year Engineering Student | Aspiring Data & Sustainability Analyst
[GitHub](https://github.com/Rehan-0112) · [LinkedIn](https://www.linkedin.com/in/rehan-shaikh-16618023b)

---

## 📄 License
MIT License — free to use, modify, and distribute with attribution.
