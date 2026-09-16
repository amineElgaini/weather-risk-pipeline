import sys
from pathlib import Path
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

# Add project root directory to Python path to import custom modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import your modular scripts directly
from extraction.fetch_bronze import extract_bronze_data
from transformation.clean_silver import process_silver_data
from transformation.build_gold import generate_gold_metrics
from load.load_postgres import load_to_postgres

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="morocco_weather_logistics_pipeline",
    default_args=default_args,
    description="Orchestrates Bronze -> Silver -> Gold ETL pipeline and loads to PostgreSQL",
    schedule="0 6 * * *",  # Daily at 6:00 AM
    start_date=datetime(2026, 9, 1),
    catchup=False,
    tags=["logistics", "weather", "morocco"],
) as dag:

    t1_extract = PythonOperator(
        task_id="extract_bronze",
        python_callable=extract_bronze_data,
    )

    t2_transform_silver = PythonOperator(
        task_id="transform_silver",
        python_callable=process_silver_data,
    )

    t3_build_gold = PythonOperator(
        task_id="build_gold",
        python_callable=generate_gold_metrics,
    )

    t4_load_db = PythonOperator(
        task_id="load_postgres",
        python_callable=load_to_postgres,
    )

    # Clean task dependency flow
    t1_extract >> t2_transform_silver >> t3_build_gold >> t4_load_db