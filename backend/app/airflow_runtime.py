from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import date, datetime
from typing import Any, TypeVar

from app.config.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.store import BaseStore, build_store

logger = get_logger(__name__)

BatchResult = TypeVar("BatchResult")


def resolve_airflow_reference_time(context: Mapping[str, Any]) -> datetime | None:
    candidate = context.get("data_interval_end")
    if isinstance(candidate, datetime):
        return candidate

    dag_run = context.get("dag_run")
    logical_date = getattr(dag_run, "logical_date", None)
    if isinstance(logical_date, datetime):
        return logical_date
    return None


def resolve_airflow_reference_date(context: Mapping[str, Any]) -> date | None:
    reference_time = resolve_airflow_reference_time(context)
    if reference_time is None:
        return None
    return reference_time.date()


def _serialize_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        payload = result.model_dump()
        if isinstance(payload, dict):
            return payload
    if isinstance(result, dict):
        return result
    return {"result": result}


async def _run_batch(
    *,
    batch_name: str,
    runner: Callable[[BaseStore], Awaitable[BatchResult]],
) -> dict[str, Any]:
    configure_logging()
    settings = get_settings()
    store = await build_store(settings)
    try:
        result = await runner(store)
        payload = _serialize_result(result)
        logger.info(
            "Completed Airflow worker batch.",
            extra={"context": {"batch_name": batch_name, **payload}},
        )
        return payload
    finally:
        await store.close()


async def run_schedule_batch(
    *, reference_time: datetime | None = None
) -> dict[str, Any]:
    return await _run_batch(
        batch_name="market_tracker_schedule_reconcile",
        runner=lambda store: store.schedule_jobs(reference_time=reference_time),
    )


def run_schedule_batch_task(
    *, reference_time: datetime | None = None
) -> dict[str, Any]:
    return asyncio.run(run_schedule_batch(reference_time=reference_time))


async def run_apify_poller_batch() -> dict[str, Any]:
    return await _run_batch(
        batch_name="market_tracker_apify_poller",
        runner=lambda store: store.poll_apify_runs(),
    )


def run_apify_poller_batch_task() -> dict[str, Any]:
    return asyncio.run(run_apify_poller_batch())


async def run_importer_batch() -> dict[str, Any]:
    return await _run_batch(
        batch_name="market_tracker_importer",
        runner=lambda store: store.process_import_jobs(),
    )


def run_importer_batch_task() -> dict[str, Any]:
    return asyncio.run(run_importer_batch())


async def run_notification_batch() -> dict[str, Any]:
    return await _run_batch(
        batch_name="market_tracker_notifications",
        runner=lambda store: store.process_notifications(),
    )


def run_notification_batch_task() -> dict[str, Any]:
    return asyncio.run(run_notification_batch())


async def run_weekly_digest_batch(
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    return await _run_batch(
        batch_name="market_tracker_weekly_digest",
        runner=lambda store: store.process_digest_jobs(reference_date=reference_date),
    )


def run_weekly_digest_batch_task(
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    return asyncio.run(run_weekly_digest_batch(reference_date=reference_date))
