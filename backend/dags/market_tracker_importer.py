from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

from app.airflow_config import get_airflow_dag_settings
from app.airflow_runtime import run_importer_batch_task

_SETTINGS = get_airflow_dag_settings()


if _SETTINGS.importer_enabled:
    with DAG(
        dag_id="market_tracker_importer",
        description="Import completed Apify datasets into snapshots and events.",
        schedule=_SETTINGS.importer_cron,
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,
        default_args={"owner": "market-tracker"},
        is_paused_upon_creation=True,
        tags=["market-tracker", "importer"],
    ) as dag:
        PythonOperator(
            task_id="import_ready_jobs",
            python_callable=run_importer_batch_task,
        )
