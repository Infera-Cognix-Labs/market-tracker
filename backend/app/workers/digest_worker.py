from __future__ import annotations

import argparse
import asyncio

from app.config.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.store import build_store

logger = get_logger(__name__)


async def digest_once() -> None:
    settings = get_settings()
    store = await build_store(settings)
    try:
        result = await store.process_digest_jobs()
        logger.info(
            "Completed digest worker batch.",
            extra={"context": result.model_dump()},
        )
    finally:
        await store.close()


async def run_digest_worker() -> None:
    settings = get_settings()
    interval_secs = settings.worker_config.digest_interval_secs
    store = await build_store(settings)
    try:
        while True:
            result = await store.process_digest_jobs()
            logger.info(
                "Completed digest worker batch.",
                extra={"context": result.model_dump()},
            )
            await asyncio.sleep(interval_secs)
    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate weekly digest read models from tracking events."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single digest batch and exit.",
    )
    args = parser.parse_args()

    configure_logging()
    if args.once:
        asyncio.run(digest_once())
        return
    asyncio.run(run_digest_worker())


if __name__ == "__main__":
    main()
