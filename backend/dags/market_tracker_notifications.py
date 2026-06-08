from __future__ import annotations

from datetime import datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

from app.airflow_config import get_airflow_dag_settings
from app.airflow_runtime import run_notification_batch_task

_SETTINGS = get_airflow_dag_settings()


if _SETTINGS.notifications_enabled:
    with DAG(
        dag_id="market_tracker_notifications",
        description="Deliver matching tracking events to enabled Slack notification rules.",
        schedule=_SETTINGS.notifications_cron,
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,
        default_args={"owner": "market-tracker"},
        is_paused_upon_creation=False,
        tags=["market-tracker", "notifications", "slack"],
    ) as dag:
        PythonOperator(
            task_id="deliver_slack_notifications",
            python_callable=run_notification_batch_task,
        )
