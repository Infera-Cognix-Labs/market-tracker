from __future__ import annotations

import argparse
import asyncio

from app.config.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.store import build_store

logger = get_logger(__name__)


async def run(*, once: bool) -> None:
    settings = get_settings()
    store = await build_store(settings)
    try:
        while True:
            result = await store.process_notifications()
            logger.info(
                "Completed notification worker batch.",
                extra={"context": result.model_dump()},
            )
            if once:
                return
            await asyncio.sleep(settings.worker_config.notification_interval_secs)
    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Slack notification worker.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one notification batch and exit.",
    )
    args = parser.parse_args()

    configure_logging()
    asyncio.run(run(once=args.once))


if __name__ == "__main__":
    main()
