"""Apache Airflow DAG: runs the pipeline every day at 06:00 Baku time.

Task graph:   extract  >>  transform_load_check

Place this repository inside your Airflow environment (or add it to
PYTHONPATH) and copy this file into the Airflow `dags/` folder.
Note: Airflow does not run natively on Windows; use WSL2 or Docker.
"""
import sys
from pathlib import Path

import pendulum

# Make the `pipeline` package importable when the DAG file is copied elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:  # Airflow 3.x
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2.x
    from airflow.decorators import dag, task


@dag(
    dag_id="azerbaijan_weather_pipeline",
    schedule="0 6 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Baku"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=10)},
    tags=["weather", "medallion", "portfolio"],
)
def azerbaijan_weather_pipeline():

    @task
    def extract() -> list[dict]:
        from pipeline.run import extract_step
        return extract_step()  # list of bronze files, passed on via XCom

    @task
    def transform_load_check(items: list[dict]) -> dict:
        from pipeline.run import process_step
        return process_step(items, mode="api")

    transform_load_check(extract())


azerbaijan_weather_pipeline()
