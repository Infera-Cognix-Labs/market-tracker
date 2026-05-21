from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

from app.airflow_config import get_airflow_dag_settings
from app.airflow_runtime import (
    resolve_airflow_reference_time,
    run_schedule_batch_task,
)

_SETTINGS = get_airflow_dag_settings()


def _run_schedule_reconcile(**context):
    reference_time = resolve_airflow_reference_time(context)
    return run_schedule_batch_task(reference_time=reference_time)


if _SETTINGS.schedule_reconcile_enabled:
    with DAG(
        dag_id="market_tracker_schedule_reconcile",
        description="Reconcile tracker schedules and dispatch due jobs.",
        schedule=_SETTINGS.schedule_reconcile_cron,
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,
        default_args={"owner": "market-tracker"},
        is_paused_upon_creation=True,
        tags=["market-tracker", "scheduler"],
    ) as dag:
        PythonOperator(
            task_id="reconcile_schedules",
            python_callable=_run_schedule_reconcile,
        )
