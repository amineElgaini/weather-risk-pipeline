# 🌤️ Morocco Weather & Logistics ETL Pipeline

A data engineering pipeline built with **Python**, **Apache Airflow**, and **PostgreSQL** to extract, transform, and analyze weather data across Moroccan cities for logistics risk assessment.

---

## 🛠️ Tech Stack

* **Orchestration:** Apache Airflow
* **Processing:** Python (Pandas, Requests)
* **Storage:** PostgreSQL (Silver & Gold Layers)
* **Containerization:** Docker & Docker Compose

---

## 🏗️ Architecture

1. **Extract (Bronze):** Fetches raw weather data for target Moroccan cities via API.
2. **Transform (Silver):** Cleans, validates, and normalizes raw JSON data into structured tabular formats.
3. **Build Risk Metrics (Gold):** Computes custom logistics risk scores based on precipitation, wind, and temperature thresholds.
4. **Load:** Persists processed Silver and Gold datasets into PostgreSQL for reporting and downstream usage.

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/your-username/weather_logistics.git
cd weather_logistics

```

### 2. Configure Environment

Create an `.env` file in the root directory:

```bash
AIRFLOW_UID=50000
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow

```

### 3. Run with Docker Compose

```bash
# Initialize Airflow database and admin user
docker compose up airflow-init

# Start all services
docker compose up -d

```

Access the Airflow Web UI at **`http://localhost:8080`** (Credentials: `admin` / `admin`).

---

## 📁 Project Structure

```text
weather_logistics/
├── dags/                  # Airflow DAG definitions
├── config/                # Environment and app configs
├── logs/                  # Airflow execution logs
├── plugins/               # Custom Airflow operators/hooks
├── docker-compose.yml     # Container stack specification
└── README.md

```
