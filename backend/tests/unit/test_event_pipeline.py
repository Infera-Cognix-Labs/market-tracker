from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.models.api import AvailabilityStatus, BuyBoxStatus, EventType, TrackerType
from app.services.diff_service import DiffService
from app.services.event_engine import EventEngine


class FakeCursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self):
        return self.items


def test_diff_service_generates_category_and_product_candidates(run_async, monkeypatch):
    snapshot_date = date(2026, 4, 8)

    current_category_snapshot = SimpleNamespace(
        marketplace="amazon_us",
        captured_at=datetime(2026, 4, 8, 3, 0, tzinfo=UTC),
        products=[
            SimpleNamespace(asin="B0AAA11111", rank_position=9),
            SimpleNamespace(asin="B0BBB22222", rank_position=18),
        ],
    )
    previous_category_snapshot = SimpleNamespace(
        snapshot_date=date(2026, 4, 7),
        products=[
            SimpleNamespace(
                asin="B0AAA11111", rank_position=14,
                title="Old Product Title", brand="BrandA", image_url="https://example.com/old.jpg",
                price_current=34.99, price_original=44.99, currency="USD",
                rating_value=4.5, review_count=100, product_url="https://amazon.com/dp/B0AAA11111",
            ),
            SimpleNamespace(
                asin="B0CCC33333", rank_position=47,
                title="Exited Product", brand="BrandC", image_url="https://example.com/exited.jpg",
                price_current=19.99, price_original=None, currency="USD",
                rating_value=3.8, review_count=50, product_url="https://amazon.com/dp/B0CCC33333",
            ),
        ],
    )

    current_product_snapshot = SimpleNamespace(
        marketplace="amazon_us",
        asin="B0AAA11111",
        captured_at=datetime(2026, 4, 8, 3, 4, tzinfo=UTC),
        price_current=29.99,
        price_original=39.99,
        coupon_text="10% off",
        title_hash="title_new",
        title="New Product Title",
        main_image_hash="img_new",
        main_image_url="https://example.com/new.jpg",
        variation_count=5,
        availability_status=AvailabilityStatus.OUT_OF_STOCK,
        buy_box_status=BuyBoxStatus.NO_BUY_BOX,
        buy_box_seller_name=None,
        snapshot_date=snapshot_date,
    )
    previous_product_snapshot = SimpleNamespace(
        marketplace="amazon_us",
        asin="B0AAA11111",
        snapshot_date=date(2026, 4, 7),
        price_current=34.99,
        price_original=44.99,
        coupon_text=None,
        title_hash="title_old",
        title="Old Product Title",
        main_image_hash="img_old",
        main_image_url="https://example.com/old.jpg",
        variation_count=3,
        availability_status=AvailabilityStatus.IN_STOCK,
        buy_box_status=BuyBoxStatus.HAS_BUY_BOX,
        buy_box_seller_name="Amazon",
    )

    async def fake_category_find_one(*args, **kwargs):
        return current_category_snapshot

    def fake_category_find(*args, **kwargs):
        return FakeCursor([previous_category_snapshot])

    def fake_product_find(query):
        if "tracker_refs.tracker_code" in query:
            return FakeCursor([current_product_snapshot])
        return FakeCursor([previous_product_snapshot])

    monkeypatch.setattr(
        "app.services.diff_service.CategorySnapshotDocument",
        SimpleNamespace(
            find_one=fake_category_find_one,
            find=fake_category_find,
        ),
    )
    monkeypatch.setattr(
        "app.services.diff_service.ProductSnapshotDocument",
        SimpleNamespace(find=fake_product_find),
    )

    candidates = run_async(
        DiffService().build_candidates(
            workspace_id="ws_demo_us",
            tracker_type=TrackerType.CATEGORY,
            tracker_code="ct_demo",
            snapshot_date=snapshot_date,
        )
    )

    event_types = {item.event_type for item in candidates}
    assert EventType.NEW_ENTRANT_TOP50 in event_types
    assert EventType.ENTER_TOP10 in event_types
    assert EventType.EXIT_TOP50 in event_types
    assert EventType.PRICE_CHANGED in event_types
    assert EventType.PROMOTION_CHANGED in event_types
    assert EventType.TITLE_CHANGED in event_types
    assert EventType.MAIN_IMAGE_CHANGED in event_types
    assert EventType.VARIATIONS_ADDED in event_types
    assert EventType.AVAILABILITY_CHANGED in event_types
    assert EventType.BUY_BOX_CHANGED in event_types


def test_diff_service_dedupes_duplicate_products_in_category_snapshots(
    run_async, monkeypatch
):
    snapshot_date = date(2026, 4, 8)

    current_category_snapshot = SimpleNamespace(
        marketplace="amazon_us",
        captured_at=datetime(2026, 4, 8, 3, 0, tzinfo=UTC),
        products=[
            SimpleNamespace(asin="B0AAA11111", rank_position=9),
            SimpleNamespace(asin="B0AAA11111", rank_position=12),
            SimpleNamespace(asin="B0BBB22222", rank_position=18),
        ],
    )
    previous_category_snapshot = SimpleNamespace(
        snapshot_date=date(2026, 4, 7),
        products=[
            SimpleNamespace(
                asin="B0AAA11111", rank_position=14,
                title="Old Product Title", brand="BrandA", image_url="https://example.com/old.jpg",
                price_current=34.99, price_original=44.99, currency="USD",
                rating_value=4.5, review_count=100, product_url="https://amazon.com/dp/B0AAA11111",
            ),
            SimpleNamespace(
                asin="B0AAA11111", rank_position=21,
                title="Old Product Title 2", brand="BrandA", image_url="https://example.com/old2.jpg",
                price_current=34.99, price_original=44.99, currency="USD",
                rating_value=4.5, review_count=100, product_url="https://amazon.com/dp/B0AAA11111",
            ),
            SimpleNamespace(
                asin="B0CCC33333", rank_position=47,
                title="Exited Product", brand="BrandC", image_url="https://example.com/exited.jpg",
                price_current=19.99, price_original=None, currency="USD",
                rating_value=3.8, review_count=50, product_url="https://amazon.com/dp/B0CCC33333",
            ),
        ],
    )

    async def fake_category_find_one(*args, **kwargs):
        return current_category_snapshot

    def fake_category_find(*args, **kwargs):
        return FakeCursor([previous_category_snapshot])

    def fake_product_find(query):
        return FakeCursor([])

    monkeypatch.setattr(
        "app.services.diff_service.CategorySnapshotDocument",
        SimpleNamespace(
            find_one=fake_category_find_one,
            find=fake_category_find,
        ),
    )
    monkeypatch.setattr(
        "app.services.diff_service.ProductSnapshotDocument",
        SimpleNamespace(find=fake_product_find),
    )

    candidates = run_async(
        DiffService().build_candidates(
            workspace_id="ws_demo_us",
            tracker_type=TrackerType.CATEGORY,
            tracker_code="ct_demo",
            snapshot_date=snapshot_date,
        )
    )

    enter_top10_candidates = [
        item
        for item in candidates
        if item.event_type == EventType.ENTER_TOP10 and item.asin == "B0AAA11111"
    ]
    assert len(enter_top10_candidates) == 1
    assert enter_top10_candidates[0].metadata == {
        "previous_rank": 14,
        "current_rank": 9,
    }


def test_event_engine_deduplicates_and_inserts_new_events(run_async, monkeypatch):
    snapshot_date = date(2026, 4, 8)
    now = datetime(2026, 4, 8, 4, 0, tzinfo=UTC)

    class FakeDiffService:
        async def build_candidates(self, **kwargs):
            return [
                SimpleNamespace(
                    tracker_type=TrackerType.CATEGORY,
                    tracker_code="ct_demo",
                    marketplace="amazon_us",
                    asin="B0AAA11111",
                    event_type=EventType.ENTER_TOP10,
                    snapshot_date=snapshot_date,
                    event_time=now,
                    metadata={"previous_rank": 15, "current_rank": 8},
                ),
                SimpleNamespace(
                    tracker_type=TrackerType.COMPETITOR,
                    tracker_code="cmp_demo",
                    marketplace="amazon_us",
                    asin="B0BBB22222",
                    event_type=EventType.PRICE_CHANGED,
                    snapshot_date=snapshot_date,
                    event_time=now,
                    metadata={
                        "previous_price_current": 35.99,
                        "previous_price_original": 39.99,
                        "current_price_current": 29.99,
                        "current_price_original": 39.99,
                        "delta_abs": -6.0,
                        "delta_pct": -16.67,
                    },
                ),
            ]

    inserted_events: list[object] = []

    class FakeEventDocument:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        @staticmethod
        def find(query):
            # Pretend first candidate already exists by dedupe_key.
            return FakeCursor(
                [
                    SimpleNamespace(
                        dedupe_key="ENTER_TOP10|ct_demo|B0AAA11111|2026-04-08",
                    )
                ]
            )

        @staticmethod
        async def insert_many(events):
            inserted_events.extend(events)

    monkeypatch.setattr(
        "app.services.event_engine.EventDocument",
        FakeEventDocument,
    )

    engine = EventEngine(FakeDiffService())
    inserted_count = run_async(
        engine.generate_events_for_job(
            workspace_id="ws_demo_us",
            job_document=SimpleNamespace(
                job_code="job_cmp_20260408_001",
                tracker_type=TrackerType.COMPETITOR,
                tracker_code="cmp_demo",
                snapshot_date=snapshot_date,
            ),
        )
    )

    assert inserted_count == 1
    assert len(inserted_events) == 1
    assert inserted_events[0].event_type == EventType.PRICE_CHANGED
    assert (
        inserted_events[0].dedupe_key == "PRICE_CHANGED|amazon_us|B0BBB22222|2026-04-08"
    )
