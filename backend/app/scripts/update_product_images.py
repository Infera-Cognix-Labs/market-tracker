#!/usr/bin/env python3
"""
One-time script: refresh main_image_url_latest for all products by querying
the Junglee ASINs Scraper actor on Apify.

Usage:
    cd backend
    uv run python -m app.scripts.update_product_images [--dry-run] [--batch-size 50]

Reads MONGO_URI and APIFY_TOKEN from .env (via app.config.config).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import defaultdict

from apify_client import ApifyClient
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config.config import get_settings
from app.models.documents import DOCUMENT_MODELS, ProductDocument

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MARKETPLACE_TO_DOMAIN: dict[str, str] = {
    "amazon_us": "amazon.com",
    "amazon_uk": "amazon.co.uk",
    "amazon_de": "amazon.de",
    "amazon_fr": "amazon.fr",
    "amazon_es": "amazon.es",
    "amazon_it": "amazon.it",
    "amazon_ca": "amazon.ca",
    "amazon_jp": "amazon.co.jp",
    "amazon_au": "amazon.com.au",
    "amazon_in": "amazon.in",
    "amazon_mx": "amazon.com.mx",
}

ACTOR_ID = "junglee/amazon-asins-scraper"


def _extract_image(item: dict) -> str:
    for key in ("thumbnailImage", "main_image_url", "image_url", "image"):
        val = item.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    for key in ("galleryThumbnails", "highResolutionImages"):
        gallery = item.get(key)
        if isinstance(gallery, list) and gallery:
            for url in gallery:
                if isinstance(url, str) and url.startswith("http"):
                    return url
    return ""


async def _init_db() -> AsyncMongoClient:
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb_config.dsn)
    await init_beanie(
        database=client[settings.mongodb_config.database],
        document_models=DOCUMENT_MODELS,
    )
    log.info("Connected to MongoDB: %s", settings.mongodb_config.database)
    return client


def _fetch_images_from_apify(
    api_token: str,
    asins: list[str],
    amazon_domain: str,
) -> dict[str, str]:
    client = ApifyClient(api_token)
    run_input = {
        "asins": asins,
        "amazonDomain": amazon_domain,
        "language": "en",
        "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
        "useCaptchaSolver": False,
    }
    log.info("Calling %s for %d ASINs on %s", ACTOR_ID, len(asins), amazon_domain)
    run = client.actor(ACTOR_ID).call(run_input=run_input, timeout_secs=300)

    if run.get("status") != "SUCCEEDED":
        log.warning("Actor run did not succeed (status=%s), skipping batch", run.get("status"))
        return {}

    dataset_id = run["defaultDatasetId"]
    items = client.dataset(dataset_id).list_items().items
    log.info("Got %d items from Apify", len(items))

    result: dict[str, str] = {}
    for item in items:
        asin = (item.get("asin") or item.get("originalAsin") or "").upper().strip()
        image = _extract_image(item)
        if asin and image:
            result[asin] = image
    return result


async def main(dry_run: bool, batch_size: int, marketplaces: list[str] | None, skip_marketplaces: list[str]) -> None:
    client = await _init_db()
    try:
        settings = get_settings()
        api_token = settings.apify_config.token
        if not api_token:
            log.error("APIFY_TOKEN is not set in .env")
            sys.exit(1)

        products = await ProductDocument.find_all().to_list()
        log.info("Found %d total products in database", len(products))

        # Group by marketplace
        by_marketplace: dict[str, list[ProductDocument]] = defaultdict(list)
        for p in products:
            by_marketplace[p.marketplace].append(p)

        marketplaces_to_process = sorted(by_marketplace.keys())
        if marketplaces:
            marketplaces_to_process = [m for m in marketplaces_to_process if m in marketplaces]
        if skip_marketplaces:
            marketplaces_to_process = [m for m in marketplaces_to_process if m not in skip_marketplaces]
        log.info("Marketplaces to process: %s", marketplaces_to_process)

        total_updated = 0
        total_skipped = 0

        for marketplace in marketplaces_to_process:
            mkt_products = by_marketplace[marketplace]
            amazon_domain = MARKETPLACE_TO_DOMAIN.get(marketplace, "www.amazon.com")
            asins = [p.asin for p in mkt_products]
            log.info(
                "Marketplace %s: %d products, domain=%s",
                marketplace,
                len(asins),
                amazon_domain,
            )

            # Process in batches
            for i in range(0, len(asins), batch_size):
                batch_asins = asins[i : i + batch_size]
                asin_to_image = _fetch_images_from_apify(
                    api_token, batch_asins, amazon_domain
                )

                for p in mkt_products:
                    if p.asin not in asin_to_image:
                        total_skipped += 1
                        continue
                    new_image = asin_to_image[p.asin]
                    if p.main_image_url_latest == new_image:
                        total_skipped += 1
                        continue
                    log.info(
                        "  %s/%s: image %s -> %s",
                        p.marketplace,
                        p.asin,
                        p.main_image_url_latest[:60],
                        new_image[:60],
                    )
                    if not dry_run:
                        p.main_image_url_latest = new_image
                        await p.save()
                    total_updated += 1

        log.info("Done. Updated=%d, Skipped=%d", total_updated, total_skipped)
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh product image URLs from Apify")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes without writing to database",
    )
    parser.add_argument(
        "--marketplace",
        action="append",
        dest="marketplaces",
        help="Only process this marketplace (can be repeated). If omitted, all are processed.",
    )
    parser.add_argument(
        "--skip-marketplace",
        action="append",
        dest="skip_marketplaces",
        default=[],
        help="Skip this marketplace (can be repeated).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of ASINs per Apify actor call (default: 50)",
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, batch_size=args.batch_size, marketplaces=args.marketplaces, skip_marketplaces=args.skip_marketplaces or []))
