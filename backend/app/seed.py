from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.models.api import (
    CategorySnapshot,
    CategoryTracker,
    CompetitorTrackerDetail,
    DashboardOverview,
    Event,
    Job,
    ProductDetail,
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
    product_timelines: list[ProductTimelineResponse]
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
        products=[ProductDetail.model_validate(_load_json("product.detail.response.json"))],
        product_timelines=[ProductTimelineResponse.model_validate(timeline_payload)],
        jobs=[Job.model_validate(_load_json("job.detail.response.json"))],
        weekly_digests=[
            WeeklyDigest.model_validate(_load_json("weekly-digest.detail.response.json"))
        ],
    )
