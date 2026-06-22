#!/usr/bin/env python3
"""
Refresh category product images via junglee/amazon-bestsellers actor.
Queries each category tracker's browse_node_url, extracts thumbnails,
updates ProductDocument.main_image_url_latest + latest snapshot's main_image_url.
"""

from __future__ import annotations

import asyncio
import logging
import re

from apify_client import ApifyClient
from app.config.config import get_settings
from app.models.documents import (
    DOCUMENT_MODELS,
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    ProductDocument,
    ProductSnapshotDocument,
)
from beanie import init_beanie
from pymongo import AsyncMongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ACTOR_ID = "junglee/amazon-bestsellers"
_ASIN_IN_URL = re.compile(r"/dp/([A-Z0-9]{10,12})")


def _extract_asin(item: dict) -> str:
    asin = (item.get("asin") or "").upper().strip()
    if asin:
        return asin
    url = item.get("url", "")
    m = _ASIN_IN_URL.search(url)
    return m.group(1).upper() if m else ""


def _fetch_category_items(api_token: str, category_url: str, top_n: int) -> list[dict]:
    client = ApifyClient(api_token)
    run = client.actor(ACTOR_ID).call(
        run_input={
            "categoryUrls": [category_url],
            "maxItemsPerStartUrl": top_n,
            "depthOfCrawl": 1,
            "language": "en",
            "detailedInformation": False,
            "useCaptchaSolver": False,
        },
        timeout_secs=300,
    )
    if run.get("status") != "SUCCEEDED":
        log.warning(
            "Actor run failed (status=%s) for %s", run.get("status"), category_url
        )
        return []
    return client.dataset(run["defaultDatasetId"]).list_items().items


async def main() -> None:
    settings = get_settings()
    api_token = settings.apify_config.token
    if not api_token:
        log.error("APIFY_TOKEN not set")
        return

    client = AsyncMongoClient(settings.mongodb_config.dsn)
    await init_beanie(
        database=client[settings.mongodb_config.database],
        document_models=DOCUMENT_MODELS,
    )

    try:
        # 1. Load category trackers
        trackers = await CategoryTrackerDocument.find_all().to_list()
        log.info("Found %d category trackers", len(trackers))

        # 2. Load latest category snapshots
        cat_snapshots = await CategorySnapshotDocument.find_all().to_list()
        # Group by tracker_code, keep latest per tracker
        latest_cat_snap: dict[str, CategorySnapshotDocument] = {}
        for cs in cat_snapshots:
            if (
                cs.tracker_code not in latest_cat_snap
                or cs.snapshot_date > latest_cat_snap[cs.tracker_code].snapshot_date
            ):
                latest_cat_snap[cs.tracker_code] = cs

        # 3. Load latest snapshot per product
        all_snapshots = await ProductSnapshotDocument.find_all().to_list()
        latest_snap: dict[tuple[str, str], ProductSnapshotDocument] = {}
        for s in all_snapshots:
            key = (s.marketplace, s.asin)
            if (
                key not in latest_snap
                or s.snapshot_date > latest_snap[key].snapshot_date
            ):
                latest_snap[key] = s

        # 3. Build product lookup (by marketplace+asin, ignore workspace_id)
        all_products = await ProductDocument.find_all().to_list()
        product_map: dict[tuple[str, str], ProductDocument] = {}
        for p in all_products:
            product_map[(p.marketplace, p.asin)] = p

        # 4. Process each tracker
        total_updated = 0
        for tracker in trackers:
            url = tracker.scope.browse_node_url
            top_n = tracker.tracking_config.top_n
            marketplace = tracker.marketplace

            log.info(
                "[%s] %s -> %s (top %d)", tracker.tracker_code, marketplace, url, top_n
            )
            items = _fetch_category_items(api_token, url, top_n)
            log.info("[%s] Got %d items from Apify", tracker.tracker_code, len(items))

            for item in items:
                asin = _extract_asin(item)
                image = item.get("thumbnailUrl") or item.get("thumbnail") or ""
                if not asin or not image or not image.startswith("http"):
                    continue

                key = (marketplace, asin)
                product = product_map.get(key)
                if not product:
                    continue

                changed = False
                if product.main_image_url_latest != image:
                    product.main_image_url_latest = image
                    await product.save()
                    changed = True

                snap = latest_snap.get(key)
                if snap and snap.main_image_url != image:
                    snap.main_image_url = image
                    await snap.save()
                    changed = True

                # Update category snapshot product
                cat_snap = latest_cat_snap.get(tracker.tracker_code)
                if cat_snap:
                    for cp in cat_snap.products:
                        if cp.asin == asin and cp.image_url != image:
                            cp.image_url = image
                            changed = True
                    if any(cp.asin == asin for cp in cat_snap.products):
                        await cat_snap.save()

                if changed:
                    total_updated += 1
                    log.info("  %s/%s -> %s", marketplace, asin, image[:80])

        log.info("=== DONE. Updated %d products ===", total_updated)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
