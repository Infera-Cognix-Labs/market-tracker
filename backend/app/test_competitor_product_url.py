"""Quick test: junglee actor → adapter → normalization → product_url check."""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main():
    from app.config.config import get_settings
    from app.integrations.apify_gateway import ApifyGateway
    from app.integrations.adapters import JungleeAsinsAdapter
    from app.services.normalization_service import NormalizationService, RawImportedItem
    from app.models.api import TrackerType

    settings = get_settings()
    gateway = ApifyGateway(settings.apify_config)

    test_asins = ["B09X7MPX8L", "B0BN72FYFG"]

    print(f"=== Testing junglee actor with ASINs: {test_asins} ===\n")

    run_input = {
        "asins": test_asins,
        "amazonDomain": "amazon.com",
        "language": "en",
        "proxyCountry": "AUTO_SELECT_PROXY_COUNTRY",
        "useCaptchaSolver": False,
    }

    print("1. Starting Apify run...")
    launch = await gateway.start_run("competitor:0", run_input, webhooks=None)
    print(f"   Run ID:    {launch.provider_run_id}")
    print(f"   Status:    {launch.status}")
    print(f"   Dataset ID: {launch.default_dataset_id}")

    if launch.status not in ("SUCCEEDED",):
        print("   Waiting for run to complete...")
        for _ in range(60):
            time.sleep(5)
            state = await gateway.get_run(launch.provider_run_id)
            print(f"   Status: {state.status}")
            if state.status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                break
        if state.status != "SUCCEEDED":
            print(f"\n❌ Run failed with status: {state.status}")
            return

    print("\n2. Fetching dataset items...")
    items: list[dict] = []
    offset = 0
    limit = 200
    while True:
        batch = await gateway.list_dataset_items(
            launch.default_dataset_id, limit=limit, offset=offset
        )
        items.extend(batch.items)
        if not batch.items or len(items) >= (batch.total or 0):
            break
        offset += len(batch.items)
    print(f"   Got {len(items)} items")

    if not items:
        print("❌ No items returned from actor")
        return

    print("\n3. Raw output sample:")
    for i, item in enumerate(items):
        print(f"\n   --- Item {i + 1} ---")
        print(f"   asin:  {item.get('asin')}")
        print(f"   url:   {item.get('url')}")
        print(f"   title: {str(item.get('title', ''))[:60]}...")

    print("\n4. Testing adapter (JungleeAsinsAdapter)...")
    adapter = JungleeAsinsAdapter()
    for i, item in enumerate(items):
        contract = adapter.to_standard_contract(item, "amazon_us")
        if contract:
            print(
                f"   Item {i + 1}: asin={contract.asin}, product_url={contract.product_url}"
            )
        else:
            print(f"   Item {i + 1}: adapter returned None")

    print("\n5. Testing normalization service...")
    normalizer = NormalizationService()
    raw_items = [
        RawImportedItem(batch_no=1, item_index=i, payload=item)
        for i, item in enumerate(items)
    ]
    result = normalizer.normalize_items(
        tracker_type=TrackerType.COMPETITOR,
        marketplace="amazon_us",
        raw_items=raw_items,
    )
    print(
        f"   Normalized: {len(result.records)} records, {result.invalid_count} invalid"
    )
    for i, record in enumerate(result.records):
        print(
            f"   Record {i + 1}: asin={record.asin}, product_url={record.product_url}"
        )

    print("\n=== Result ===")
    all_have_url = all(r.product_url for r in result.records)
    if all_have_url:
        print("✅ All records have product_url populated!")
    else:
        missing = [r.asin for r in result.records if not r.product_url]
        print(f"❌ Missing product_url for ASINs: {missing}")


if __name__ == "__main__":
    asyncio.run(main())
