from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return raw_value.strip()


@dataclass(frozen=True)
class AirflowDagSettings:
    schedule_reconcile_enabled: bool
    schedule_reconcile_cron: str
    apify_poller_enabled: bool
    apify_poller_cron: str
    importer_enabled: bool
    importer_cron: str
    weekly_digest_enabled: bool
    weekly_digest_cron: str


def get_airflow_dag_settings() -> AirflowDagSettings:
    return AirflowDagSettings(
        schedule_reconcile_enabled=_env_bool(
            "AIRFLOW_MARKET_TRACKER_SCHEDULE_RECONCILE_ENABLED",
            True,
        ),
        schedule_reconcile_cron=_env_str(
            "AIRFLOW_MARKET_TRACKER_SCHEDULE_RECONCILE_CRON",
            "0 0 * * *",
        ),
        apify_poller_enabled=_env_bool(
            "AIRFLOW_MARKET_TRACKER_APIFY_POLLER_ENABLED",
            True,
        ),
        apify_poller_cron=_env_str(
            "AIRFLOW_MARKET_TRACKER_APIFY_POLLER_CRON",
            "* * * * *",
        ),
        importer_enabled=_env_bool(
            "AIRFLOW_MARKET_TRACKER_IMPORTER_ENABLED",
            True,
        ),
        importer_cron=_env_str(
            "AIRFLOW_MARKET_TRACKER_IMPORTER_CRON",
            "* * * * *",
        ),
        weekly_digest_enabled=_env_bool(
            "AIRFLOW_MARKET_TRACKER_WEEKLY_DIGEST_ENABLED",
            True,
        ),
        weekly_digest_cron=_env_str(
            "AIRFLOW_MARKET_TRACKER_WEEKLY_DIGEST_CRON",
            "0 0 * * 1",
        ),
    )
