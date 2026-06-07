"""
Test Apify actors pay-per-result / pay-per-usage

How to use:
    export APIFY_TOKEN='apify_api_xxx'
    python test_apify_price_per_result.py --actor saswave
    python test_apify_price_per_result.py --actor radeance
    python test_apify_price_per_result.py --actor piotrv_deals
    python test_apify_price_per_result.py --actor junglee_reviews
    python test_apify_price_per_result.py --actor intelscrape
    python test_apify_price_per_result.py --actor all

Notes:
- Script uses a small test payload to minimize costs.
- Results will be saved to the ./outputs/<actor_key>.json directory.
- You should replace the test ASIN / URL with your own products before running.
"""

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ActorSpec:
    key: str
    actor_id: str
    description: str
    sample_input: Dict[str, Any]
    notes: str = ""


ACTORS: Dict[str, ActorSpec] = {
    "saswave": ActorSpec(
        key="saswave",
        actor_id="saswave/amazon-product-scraper",
        description="Scrape product detail by ASIN or search_url",
        sample_input={
            "asins": ["B06X9NQ8GX"],
            "amazon_domain": "www.amazon.com",
        },
        notes=(
            "Can be replaced with search_url + max_pages if you want to test search results."
        ),
    ),
    "radeance": ActorSpec(
        key="radeance",
        actor_id="radeance/amazon-price-history-api",
        description="Get current price + price history + buy box by ASIN or product URL",
        sample_input={
            "identifiers": [
                "B0BN72FYFG",
                "https://www.amazon.com/dp/B0BN72FYFG",
            ]
        },
    ),
    "piotrv_deals": ActorSpec(
        key="piotrv_deals",
        actor_id="piotrv1001/amazon-todays-deals-scraper",
        description="Get Amazon Today’s Deals",
        sample_input={
            "limit": 10,
        },
    ),
    "junglee_reviews": ActorSpec(
        key="junglee_reviews",
        actor_id="junglee/amazon-reviews-scraper",
        description="Get reviews by product URL",
        sample_input={
            "productUrls": [
                "https://www.amazon.com/dp/B0BN72FYFG",
            ],
            "maxReviews": 10,
            "sort": "helpful",
            "filterByRatings": ["allStars"],
            "scrapeProductDetails": True,
        },
        notes=" This Actor is currently showing under maintenance status on Apify Store.",
    ),
    "intelscrape": ActorSpec(
        key="intelscrape",
        actor_id="intelscrape/amazon-product-review-scraper",
        description="Get product data + optional reviews + BSR + seller info",
        sample_input={
            "asinList": ["B0BN72FYFG"],
            "scrapeReviews": True,
            "maxReviewPages": 1,
            "countryCode": "US",
            "onlyInStock": False,
        },
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test all actor Apify pay-per-result")
    parser.add_argument(
        "--actor",
        required=True,
        choices=[*ACTORS.keys(), "all"],
        help="Actor to test or 'all' to run all",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory to save JSON results",
    )
    parser.add_argument(
        "--timeout-secs",
        type=int,
        default=300,
        help="Timeout waiting for actor to complete",
    )
    parser.add_argument(
        "--memory-mbytes",
        type=int,
        default=None,
        help="Memory for actor run if needed",
    )
    parser.add_argument(
        "--build",
        default=None,
        help="Build tag/version if needed to override, e.g., 'latest'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print test payload, do not call API",
    )
    return parser.parse_args()


def pretty_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def run_actor(
    client: ApifyClient,
    spec: ActorSpec,
    output_dir: Path,
    timeout_secs: int,
    memory_mbytes: int | None,
    build: str | None,
) -> None:
    print("=" * 100)
    print(f"Actor      : {spec.actor_id}")
    print(f"Description: {spec.description}")
    if spec.notes:
        print(f"Notes      : {spec.notes}")
    print("Payload test:")
    print(pretty_json(spec.sample_input))

    call_kwargs: Dict[str, Any] = {
        "run_input": spec.sample_input,
        "timeout_secs": timeout_secs,
    }
    if memory_mbytes is not None:
        call_kwargs["memory_mbytes"] = memory_mbytes
    if build is not None:
        call_kwargs["build"] = build

    try:
        run = client.actor(spec.actor_id).call(**call_kwargs)
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] Run failed with actor {spec.actor_id}: {exc}")
        return

    if run is None:
        print(f"[WARN] Actor {spec.actor_id} returned None")
        return
    dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None)
    if not dataset_id:
        print(f"[WARN] Actor {spec.actor_id} did not return a defaultDatasetId")
        print("Run metadata:")
        print(pretty_json(run))
        return

    dataset_client = client.dataset(dataset_id)
    items_resp = dataset_client.list_items()
    items: List[Dict[str, Any]] = items_resp.items

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{spec.key}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[OK] dataset_id : {dataset_id}")
    print(f"[OK] num items   : {len(items)}")
    print(f"[OK] output     : {output_path.resolve()}")
    if items:
        print("[OK] first item:")
        print(pretty_json(items[0]))
    else:
        print("[INFO] Dataset is empty.")


def dry_run(selected: List[ActorSpec]) -> None:
    for spec in selected:
        print("=" * 100)
        print(f"Actor: {spec.actor_id}")
        print(pretty_json(spec.sample_input))
        if spec.notes:
            print(f"Notes: {spec.notes}")


def main() -> None:
    args = parse_args()

    selected = list(ACTORS.values()) if args.actor == "all" else [ACTORS[args.actor]]

    if args.dry_run:
        dry_run(selected)
        return

    token = os.getenv("APIFY_TOKEN")
    client = ApifyClient(token)
    output_dir = Path(args.output_dir)

    for spec in selected:
        run_actor(
            client=client,
            spec=spec,
            output_dir=output_dir,
            timeout_secs=args.timeout_secs,
            memory_mbytes=args.memory_mbytes,
            build=args.build,
        )


if __name__ == "__main__":
    main()
