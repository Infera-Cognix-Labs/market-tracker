from __future__ import annotations

from datetime import date

import pytest
from app.models.api import (
    Event,
    EventPayload,
    EventType,
    ProductTimelinePoint,
    Severity,
    Timeframe,
    TrackerStatus,
    TrackerType,
)
from app.store import (
    MongoStore,
    _aggregate_timeline_points,
    _build_dashboard_overview,
    _build_timeline_summary,
    _build_top_threats,
    _generate_job_code,
    _generate_tracker_code,
    _sort_events,
    _within_range,
    build_store,
)


def test_generate_tracker_code_and_job_code_increment_uniquely():
    tracker_code = _generate_tracker_code(
        "ct", "Bottle Warmer US", {"ct_bottle_warmer_us"}
    )
    job_code = _generate_job_code(
        snapshot_date=date(2026, 4, 3),
        tracker_type="CATEGORY",
        existing_codes={"job_cat_20260403_001", "job_cat_20260403_002"},
    )

    assert tracker_code == "ct_bottle_warmer_us_2"
    assert job_code == "job_cat_20260403_003"


def test_range_and_timeline_helpers(seed_data):
    timeline_points = [
        ProductTimelinePoint(
            snapshot_date=snapshot.snapshot_date,
            bsr_position=snapshot.bsr_position,
            price_current=snapshot.price_current,
            price_original=snapshot.price_original,
            coupon_text=snapshot.coupon_text,
            availability_status=snapshot.availability_status,
            buy_box_status=snapshot.buy_box_status,
            rating_value=snapshot.rating_value,
            review_count=snapshot.review_count,
            title_hash=snapshot.title_hash,
            main_image_hash=snapshot.main_image_hash,
            variation_count=snapshot.variation_count,
        )
        for snapshot in seed_data.product_snapshots
    ]
    timeline_events = [
        event
        for event in seed_data.events
        if event.asin == seed_data.products[0].asin
        and event.marketplace == seed_data.products[0].marketplace
    ]

    assert _within_range(date(2026, 4, 3), date(2026, 4, 1), date(2026, 4, 3)) is True
    assert _within_range(date(2026, 3, 31), date(2026, 4, 1), date(2026, 4, 3)) is False

    weekly_points = _aggregate_timeline_points(timeline_points, Timeframe.WEEKLY)
    monthly_points = _aggregate_timeline_points(timeline_points, Timeframe.MONTHLY)
    summary = _build_timeline_summary(timeline_events)

    assert len(weekly_points) == 2
    assert weekly_points[0].snapshot_date == date(2026, 3, 23)
    assert weekly_points[1].snapshot_date == date(2026, 3, 30)
    assert len(monthly_points) == 2
    assert monthly_points[0].snapshot_date == date(2026, 3, 1)
    assert monthly_points[1].snapshot_date == date(2026, 4, 1)
    assert summary.price_change_count == 1
    assert summary.listing_change_count == 1


def test_seed_data_builds_product_snapshots(seed_data):
    assert len(seed_data.product_snapshots) == 6
    assert seed_data.product_snapshots[-1].snapshot_date == date(2026, 4, 3)
    assert seed_data.product_snapshots[-1].title.endswith("Night Light")


def test_event_sorting_threats_and_dashboard_helpers(seed_data):
    category_trackers = seed_data.category_trackers
    competitor_trackers = seed_data.competitor_trackers
    events = seed_data.events

    sorted_events = _sort_events(events)
    overview = _build_dashboard_overview(
        timeframe=Timeframe.WEEKLY,
        category_trackers=category_trackers,
        competitor_trackers=competitor_trackers,
        events=events,
    )
    tracker_name_map = {
        tracker.tracker_code: tracker.name
        for tracker in [*category_trackers, *competitor_trackers]
    }
    threats = _build_top_threats(sorted_events, tracker_name_map)

    assert sorted_events[0].severity == Severity.HIGH
    assert sorted_events[0].event_type in {
        EventType.ENTER_TOP10,
        EventType.AVAILABILITY_CHANGED,
    }
    assert overview.summary.active_category_tracker_count == 1
    assert overview.summary.active_competitor_tracker_count == 1
    assert overview.summary.price_change_count >= 1
    assert overview.top_threats
    assert threats[0].tracker_refs


def test_build_top_threats_keeps_single_high_severity_signal(seed_data):
    tracker_name_map = {
        tracker.tracker_code: tracker.name
        for tracker in [*seed_data.category_trackers, *seed_data.competitor_trackers]
    }
    high_severity_only_event = Event(
        event_code="evt_high_only_001",
        tracker_type=TrackerType.CATEGORY,
        tracker_code=seed_data.category_trackers[0].tracker_code,
        marketplace="amazon_us",
        asin="B0HIGH00001",
        event_type=EventType.ENTER_TOP10,
        event_time=seed_data.events[0].event_time,
        snapshot_date=seed_data.events[0].snapshot_date,
        severity=Severity.HIGH,
        title="High severity event",
        summary="A standalone high severity event should still surface as a threat.",
        payload=EventPayload(current_rank=3, previous_rank=12),
    )

    threats = _build_top_threats([high_severity_only_event], tracker_name_map)

    assert len(threats) == 1
    assert threats[0].asin == "B0HIGH00001"
    assert (
        threats[0].tracker_refs[0].tracker_code
        == seed_data.category_trackers[0].tracker_code
    )


def test_dashboard_helper_ignores_inactive_trackers(seed_data):
    inactive_category = seed_data.category_trackers[0].model_copy(
        update={"status": TrackerStatus.ARCHIVED}
    )
    inactive_competitor = seed_data.competitor_trackers[0].model_copy(
        update={"status": TrackerStatus.PAUSED}
    )

    overview = _build_dashboard_overview(
        timeframe=Timeframe.DAILY,
        category_trackers=[inactive_category],
        competitor_trackers=[inactive_competitor],
        events=seed_data.events,
    )

    assert overview.summary.active_category_tracker_count == 0
    assert overview.summary.active_competitor_tracker_count == 0
    assert overview.category_highlights == []
    assert overview.competitor_highlights == []


@pytest.mark.skip(reason="Requires real MongoDB connection - infrastructure test")
def test_build_store_initializes_mongo_store(run_async, monkeypatch):
    captured: dict[str, object] = {}

    class DummyMongoClient:
        def __init__(self, dsn: str) -> None:
            self.dsn = dsn
            self.closed = False

        def __getitem__(self, database_name: str) -> str:
            captured["database_name"] = database_name
            return f"db::{database_name}"

        def close(self) -> None:
            self.closed = True

    async def fake_init_beanie(*, database, document_models) -> None:
        captured["database"] = database
        captured["document_models"] = document_models

    monkeypatch.setattr("app.store.AsyncMongoClient", DummyMongoClient)
    monkeypatch.setattr("app.store.init_beanie", fake_init_beanie)

    from app.config.config import Config

    settings = Config(seed_demo_data=False)
    store = run_async(build_store(settings))
    try:
        assert isinstance(store, MongoStore)
        assert store.client.dsn == settings.mongodb_config.dsn
        assert captured["database_name"] == settings.mongodb_config.database
        assert captured["database"] == f"db::{settings.mongodb_config.database}"
        assert captured["document_models"]
    finally:
        run_async(store.close())
