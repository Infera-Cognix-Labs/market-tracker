from __future__ import annotations

import argparse
import asyncio

from app.config.config import Config, get_settings
from app.core.logging import configure_logging, get_logger
from app.store import BaseStore, build_store

logger = get_logger(__name__)

_WORKER_NAMES = {"scheduler", "poller", "importer", "digest"}


async def _run_scheduler_loop(store: BaseStore, settings: Config) -> None:
    while True:
        result = await store.schedule_jobs()
        logger.info(
            "Completed scheduler worker batch from pool.",
            extra={"context": result.model_dump()},
        )
        await asyncio.sleep(settings.worker_config.scheduler_interval_secs)


async def _run_poller_loop(store: BaseStore, settings: Config) -> None:
    while True:
        result = await store.poll_apify_runs()
        logger.info(
            "Completed poller worker batch from pool.",
            extra={"context": result.model_dump()},
        )
        await asyncio.sleep(settings.apify_config.poll_interval_secs)


async def _run_importer_loop(store: BaseStore, settings: Config) -> None:
    while True:
        result = await store.process_import_jobs()
        logger.info(
            "Completed importer worker batch from pool.",
            extra={"context": result.model_dump()},
        )
        await asyncio.sleep(settings.apify_config.import_worker_interval_secs)


async def _run_digest_loop(store: BaseStore, settings: Config) -> None:
    while True:
        result = await store.process_digest_jobs()
        logger.info(
            "Completed digest worker batch from pool.",
            extra={"context": result.model_dump()},
        )
        await asyncio.sleep(settings.worker_config.digest_interval_secs)


async def _run_once(store: BaseStore, workers: set[str]) -> None:
    if "scheduler" in workers:
        result = await store.schedule_jobs()
        logger.info(
            "Completed scheduler worker batch from pool.",
            extra={"context": result.model_dump()},
        )

    if "poller" in workers:
        result = await store.poll_apify_runs()
        logger.info(
            "Completed poller worker batch from pool.",
            extra={"context": result.model_dump()},
        )

    if "importer" in workers:
        result = await store.process_import_jobs()
        logger.info(
            "Completed importer worker batch from pool.",
            extra={"context": result.model_dump()},
        )

    if "digest" in workers:
        result = await store.process_digest_jobs()
        logger.info(
            "Completed digest worker batch from pool.",
            extra={"context": result.model_dump()},
        )


async def run_pool(*, workers: set[str], once: bool) -> None:
    settings = get_settings()
    store = await build_store(settings)
    try:
        if once:
            await _run_once(store, workers)
            return

        tasks: list[asyncio.Task[None]] = []
        if "scheduler" in workers:
            tasks.append(asyncio.create_task(_run_scheduler_loop(store, settings)))
        if "poller" in workers:
            tasks.append(asyncio.create_task(_run_poller_loop(store, settings)))
        if "importer" in workers:
            tasks.append(asyncio.create_task(_run_importer_loop(store, settings)))
        if "digest" in workers:
            tasks.append(asyncio.create_task(_run_digest_loop(store, settings)))

        await asyncio.gather(*tasks)
    finally:
        await store.close()


def _parse_workers(raw_workers: str) -> set[str]:
    workers = {item.strip().lower() for item in raw_workers.split(",") if item.strip()}
    unknown = sorted(workers - _WORKER_NAMES)
    if unknown:
        raise ValueError(
            f"Unsupported workers: {', '.join(unknown)}. Supported: {', '.join(sorted(_WORKER_NAMES))}."
        )
    if not workers:
        return set(_WORKER_NAMES)
    return workers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run scheduler/poller/importer/digest workers in one process.",
    )
    parser.add_argument(
        "--workers",
        default="scheduler,poller,importer,digest",
        help="Comma-separated worker names: scheduler,poller,importer,digest.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one batch for each selected worker and exit.",
    )
    args = parser.parse_args()

    workers = _parse_workers(args.workers)
    configure_logging()
    asyncio.run(run_pool(workers=workers, once=args.once))


if __name__ == "__main__":
    main()
