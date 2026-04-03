from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path

from app.models.api import (
    CategorySnapshot,
    CategoryTracker,
    CompetitorTrackerDetail,
    DashboardOverview,
    Event,
    Job,
    ProductDetail,
    ProductSnapshot,
    ProductTimelineResponse,
    WeeklyDigest,
)

MOCK_DIR = Path(__file__).resolve().parents[1] / "docs" / "api" / "mock"


@dataclass(frozen=True)
class SeedData:
    workspace_id: str
    dashboard_overview: DashboardOverview
    category_trackers: list[CategoryTracker]
    category_snapshots: list[CategorySnapshot]
    competitor_trackers: list[CompetitorTrackerDetail]
    events: list[Event]
    products: list[ProductDetail]
    product_snapshots: list[ProductSnapshot]
    jobs: list[Job]
    weekly_digests: list[WeeklyDigest]


def _load_json(filename: str) -> dict:
    with (MOCK_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_demo_seed() -> SeedData:
    manifest = _load_json("manifest.json")

    event_items = {
        item["event_code"]: item for item in _load_json("events.list.response.json")["items"]
    }
    timeline_payload = _load_json("product.timeline.response.json")
    for item in timeline_payload["events"]:
        event_items[item["event_code"]] = item
    product_detail = ProductDetail.model_validate(_load_json("product.detail.response.json"))
    product_timeline = ProductTimelineResponse.model_validate(timeline_payload)

    return SeedData(
        workspace_id=manifest["workspace_id"],
        dashboard_overview=DashboardOverview.model_validate(
            _load_json("dashboard-overview.response.json")
        ),
        category_trackers=[
            CategoryTracker.model_validate(item)
            for item in _load_json("category-trackers.list.response.json")["items"]
        ],
        category_snapshots=[
            CategorySnapshot.model_validate(
                _load_json("category-tracker.latest-snapshot.response.json")
            )
        ],
        competitor_trackers=[
            CompetitorTrackerDetail.model_validate(
                _load_json("competitor-tracker.detail.response.json")
            )
        ],
        events=[Event.model_validate(item) for item in event_items.values()],
        products=[product_detail],
        product_snapshots=_build_product_snapshots(product_detail, product_timeline),
        jobs=[Job.model_validate(_load_json("job.detail.response.json"))],
        weekly_digests=[
            WeeklyDigest.model_validate(_load_json("weekly-digest.detail.response.json"))
        ],
    )


def _build_product_snapshots(
    product_detail: ProductDetail,
    timeline: ProductTimelineResponse,
) -> list[ProductSnapshot]:
    snapshots: list[ProductSnapshot] = []
    historical_title = "MellowNest Fast Bottle Warmer"
    for point in timeline.points:
        snapshots.append(
            ProductSnapshot(
                marketplace=timeline.marketplace,
                asin=timeline.asin,
                snapshot_date=point.snapshot_date,
                captured_at=_snapshot_captured_at(product_detail, point.snapshot_date),
                tracker_refs=product_detail.tracker_refs,
                parent_asin=product_detail.parent_asin,
                brand=product_detail.brand,
                title=(
                    product_detail.title_latest
                    if point.title_hash == timeline.points[-1].title_hash
                    else historical_title
                ),
                title_hash=point.title_hash,
                product_url=product_detail.product_url,
                main_image_url=product_detail.main_image_url_latest,
                main_image_hash=point.main_image_hash,
                bsr_position=point.bsr_position,
                price_current=point.price_current,
                price_original=point.price_original,
                currency=product_detail.current_state.currency,
                coupon_text=point.coupon_text,
                availability_status=point.availability_status,
                buy_box_status=point.buy_box_status,
                buy_box_seller_name=product_detail.current_state.buy_box_seller_name,
                rating_value=point.rating_value,
                review_count=point.review_count,
                variation_count=point.variation_count,
                source_refs={
                    "provider": "APIFY",
                    "snapshot_seed": True,
                },
            )
        )
    return snapshots


def _snapshot_captured_at(product_detail: ProductDetail, snapshot_date) -> datetime:
    if snapshot_date == product_detail.current_state.last_snapshot_date:
        return product_detail.last_seen_at
    return datetime.combine(snapshot_date, time(hour=3, tzinfo=UTC))
