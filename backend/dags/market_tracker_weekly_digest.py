from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

from app.airflow_config import get_airflow_dag_settings
from app.airflow_runtime import (
    resolve_airflow_reference_date,
    run_weekly_digest_batch_task,
)

_SETTINGS = get_airflow_dag_settings()


def _run_weekly_digest(**context):
    reference_date = resolve_airflow_reference_date(context)
    return run_weekly_digest_batch_task(reference_date=reference_date)


if _SETTINGS.weekly_digest_enabled:
    with DAG(
        dag_id="market_tracker_weekly_digest",
        description="Generate weekly digests from tracking events.",
        schedule=_SETTINGS.weekly_digest_cron,
        start_date=datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,
        default_args={"owner": "market-tracker"},
        is_paused_upon_creation=True,
        tags=["market-tracker", "digest"],
    ) as dag:
        PythonOperator(
            task_id="generate_weekly_digests",
            python_callable=_run_weekly_digest,
        )
