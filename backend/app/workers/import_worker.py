from __future__ import annotations

import argparse
import asyncio

from app.config.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.store import build_store

logger = get_logger(__name__)


async def import_once() -> None:
    settings = get_settings()
    store = await build_store(settings)
    try:
        result = await store.process_import_jobs()
        logger.info(
            "Completed import worker batch.", extra={"context": result.model_dump()}
        )
    finally:
        await store.close()


async def run_import_worker() -> None:
    settings = get_settings()
    interval_secs = settings.apify_config.import_worker_interval_secs
    store = await build_store(settings)
    try:
        while True:
            result = await store.process_import_jobs()
            logger.info(
                "Completed import worker batch.",
                extra={"context": result.model_dump()},
            )
            await asyncio.sleep(interval_secs)
    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process IMPORTING jobs into raw batches and snapshots."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single importer batch and exit.",
    )
    args = parser.parse_args()

    configure_logging()
    if args.once:
        asyncio.run(import_once())
        return
    asyncio.run(run_import_worker())


if __name__ == "__main__":
    main()
