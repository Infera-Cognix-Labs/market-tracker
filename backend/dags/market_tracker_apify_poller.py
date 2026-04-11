from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

from app.airflow_config import get_airflow_dag_settings
from app.airflow_runtime import run_apify_poller_batch_task

_SETTINGS = get_airflow_dag_settings()


if _SETTINGS.apify_poller_enabled:
    with DAG(
        dag_id="market_tracker_apify_poller",
        description="Poll Apify runs and advance job state transitions.",
        schedule=_SETTINGS.apify_poller_cron,
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,
        default_args={"owner": "market-tracker"},
        is_paused_upon_creation=True,
        tags=["market-tracker", "apify"],
    ) as dag:
        PythonOperator(
            task_id="poll_apify_runs",
            python_callable=run_apify_poller_batch_task,
        )
