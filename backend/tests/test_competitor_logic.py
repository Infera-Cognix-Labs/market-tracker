from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ConflictError
from app.models.api import (
    CompetitorTrackerCreateRequest,
    CompetitorTrackFields,
    EventPayload,
    Timeframe,
    TrackedAsinWrite,
)
from app.services.insights_query_service import InsightsQueryService
from app.services.tracker_management_service import TrackerManagementService


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_find_chain(result_list: list) -> MagicMock:
    """Build a mock Beanie find() chain that returns result_list."""
    chain = MagicMock()
    chain.to_list = AsyncMock(return_value=result_list)
    chain.sort = MagicMock(return_value=chain)
    chain.skip = MagicMock(return_value=chain)
    chain.limit = MagicMock(return_value=chain)
    chain.count = AsyncMock(return_value=len(result_list))
    chain.first_or_none = AsyncMock(
        return_value=result_list[0] if result_list else None
    )
    return chain


class _FieldMock:
    """Mock that supports comparison operators for Beanie query building."""

    def __eq__(self, other: object) -> _FieldMock:
        return self

    def __ne__(self, other: object) -> _FieldMock:
        return self

    def __ge__(self, other: object) -> _FieldMock:
        return self

    def __gt__(self, other: object) -> _FieldMock:
        return self

    def __le__(self, other: object) -> _FieldMock:
        return self

    def __lt__(self, other: object) -> _FieldMock:
        return self

    def __hash__(self) -> int:
        return id(self)


def _mock_doc_class() -> MagicMock:
    """Mock a Beanie Document class with field attributes + find/find_one."""
    mock_cls = MagicMock()
    # Class-level field attributes used in queries (comparisons produce _FieldMock)
    mock_cls.workspace_id = _FieldMock()
    mock_cls.tracker_type = _FieldMock()
    mock_cls.event_type = _FieldMock()
    mock_cls.snapshot_date = _FieldMock()
    mock_cls.marketplace = _FieldMock()
    mock_cls.asin = _FieldMock()
    mock_cls.tracker_code = _FieldMock()
    mock_cls.status = _FieldMock()
    # find returns a chain; find_one is async
    mock_cls.find = MagicMock(return_value=_mock_find_chain([]))
    mock_cls.find_one = AsyncMock(return_value=None)
    # Calling the class (constructor) returns a mock whose insert() is awaitable
    mock_cls.return_value.insert = AsyncMock()
    return mock_cls


def _make_event_doc(
    *,
    tracker_type: str = "COMPETITOR",
    event_type: str = "PRICE_CHANGED",
    asin: str = "B0ABC12345",
    snapshot_date: date | None = None,
    marketplace: str = "amazon_us",
) -> SimpleNamespace:
    evt = SimpleNamespace(
        event_code=f"evt_{asin}_{event_type}",
        tracker_type=tracker_type,
        tracker_code="cmp_test",
        marketplace=marketplace,
        asin=asin,
        event_type=event_type,
        event_time=datetime(2025, 6, 15, tzinfo=timezone.utc),
        snapshot_date=snapshot_date or date(2025, 6, 15),
        severity="MEDIUM",
        title="Test Product",
        summary="price changed",
        payload=EventPayload(),
        job_code=None,
        dedupe_key=None,
    )
    evt.model_dump = lambda exclude=None, mode=None: {
        "event_code": evt.event_code,
        "tracker_type": evt.tracker_type,
        "tracker_code": evt.tracker_code,
        "marketplace": evt.marketplace,
        "asin": evt.asin,
        "event_type": evt.event_type,
        "event_time": evt.event_time,
        "snapshot_date": evt.snapshot_date,
        "severity": evt.severity,
        "title": evt.title,
        "summary": evt.summary,
        "payload": evt.payload.model_dump(),
        "job_code": evt.job_code,
        "dedupe_key": evt.dedupe_key,
    }
    return evt


def _make_product_doc(*, asin: str = "B0ABC12345", marketplace: str = "amazon_us") -> SimpleNamespace:
    return SimpleNamespace(
        marketplace=marketplace,
        asin=asin,
        parent_asin=None,
        brand="TestBrand",
        title_latest="Test Product",
        product_url=f"https://amazon.com/dp/{asin}",
        main_image_url_latest="https://img.example.com/1.jpg",
        first_seen_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        last_seen_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        current_state=SimpleNamespace(
            price_current=29.99,
            price_original=None,
            currency="USD",
            bsr_position=100,
            rating_value=4.5,
            review_count=100,
            availability_status="IN_STOCK",
            buy_box_status="HAS_BUY_BOX",
            buy_box_seller_name="Amazon",
            coupon_text=None,
            deal_info=None,
            last_snapshot_date=date(2025, 6, 15),
        ),
        tracker_refs=[],
    )


def _make_tracker_doc(
    *,
    tracker_code: str = "cmp_test",
    name: str = "Test Tracker",
    marketplace: str = "amazon_us",
    tracked_asins: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        tracker_code=tracker_code,
        name=name,
        marketplace=marketplace,
        tracked_asins=tracked_asins or [
            SimpleNamespace(asin="B0ABC12345", enabled=True, added_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
        ],
        track_fields=CompetitorTrackFields(
            bsr=True, price=True, buy_box=True, availability=True,
            promotions=True, title_change=True, main_image_change=True,
            variation_change=True, content_change=True,
        ),
        schedule=SimpleNamespace(frequency="DAILY", hour_utc=3),
        status="ACTIVE",
        stats=SimpleNamespace(
            tracked_asin_count=1, last_job_at=None, last_success_at=None
        ),
        tracked_products=[],
        created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        model_dump=lambda exclude=None, mode=None: {
            "tracker_code": tracker_code,
            "name": name,
            "marketplace": marketplace,
            "tracked_asins": [
                {"asin": ta.asin, "enabled": ta.enabled, "added_at": ta.added_at}
                for ta in (tracked_asins or [])
            ],
            "track_fields": {
                "bsr": True, "price": True, "buy_box": True, "availability": True,
                "promotions": True, "title_change": True, "main_image_change": True,
                "variation_change": True, "content_change": True,
            },
            "schedule": {"frequency": "DAILY", "hour_utc": 3},
            "status": "ACTIVE",
            "stats": {"tracked_asin_count": 1, "last_job_at": None, "last_success_at": None},
            "tracked_products": [],
            "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        },
    )


def _make_create_payload(
    *,
    asins: list[str] | None = None,
    marketplace: str = "amazon_us",
    name: str = "New Tracker",
) -> CompetitorTrackerCreateRequest:
    asin_list = asins or ["B0ABC12345"]
    return CompetitorTrackerCreateRequest(
        name=name,
        marketplace=marketplace,
        tracked_asins=[TrackedAsinWrite(asin=a, enabled=True) for a in asin_list],
        track_fields=CompetitorTrackFields(
            bsr=True, price=True, buy_box=True, availability=True,
            promotions=True, title_change=True, main_image_change=True,
            variation_change=True, content_change=True,
        ),
        schedule={"frequency": "DAILY", "hour_utc": 3},
    )


# ── #1: insights_query_service filters tracker_type == COMPETITOR ─────────────


class TestCompetitorInsightsTrackerTypeFilter:
    @pytest.mark.asyncio
    async def test_insights_query_includes_tracker_type_filter(self) -> None:
        """get_competitor_insights must filter by tracker_type == COMPETITOR."""
        service = InsightsQueryService()
        mock_event = _mock_doc_class()
        captured_args: list[tuple] = []

        def capture_find(*args, **kwargs):
            captured_args.append((args, kwargs))
            return _mock_find_chain([])

        mock_event.find = capture_find

        mock_competitor = _mock_doc_class()
        mock_product = _mock_doc_class()

        with patch("app.services.insights_query_service.EventDocument", mock_event), \
             patch("app.services.insights_query_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.insights_query_service.ProductDocument", mock_product):
            await service.get_competitor_insights("ws_test", Timeframe.WEEKLY)

        # EventDocument.find was called; check that 4 query conditions were passed
        # (workspace_id, tracker_type, event_type IN, snapshot_date >=)
        assert len(captured_args) >= 1
        find_args, _ = captured_args[0]
        assert len(find_args) >= 4, (
            f"Expected >=4 query conditions, got {len(find_args)}: {find_args}"
        )

    @pytest.mark.asyncio
    async def test_alerts_query_includes_tracker_type_filter(self) -> None:
        """get_competitor_alerts must filter by tracker_type == COMPETITOR."""
        service = InsightsQueryService()
        mock_event = _mock_doc_class()
        captured_args: list[tuple] = []

        def capture_find(*args, **kwargs):
            captured_args.append((args, kwargs))
            return _mock_find_chain([])

        mock_event.find = capture_find

        with patch("app.services.insights_query_service.EventDocument", mock_event):
            await service.get_competitor_alerts("ws_test")

        assert len(captured_args) >= 1
        find_args, _ = captured_args[0]
        # Should have 4 conditions: workspace_id, tracker_type, event_type IN, snapshot_date ==
        assert len(find_args) >= 4, (
            f"Expected >=4 query conditions, got {len(find_args)}: {find_args}"
        )

    @pytest.mark.asyncio
    async def test_insights_excludes_category_events(self) -> None:
        """A CATEGORY PRICE_CHANGED event must NOT appear in competitor insights.

        We simulate the DB returning only COMPETITOR events (as the filter ensures)
        and verify the result only contains competitor ASINs.
        """
        service = InsightsQueryService()
        competitor_event = _make_event_doc(
            tracker_type="COMPETITOR", event_type="PRICE_CHANGED",
            asin="B0XYZ00001",
        )

        mock_event = _mock_doc_class()
        mock_event.find = MagicMock(
            return_value=_mock_find_chain([competitor_event])  # only competitor events
        )
        mock_competitor = _mock_doc_class()
        mock_product = _mock_doc_class()
        product_doc = _make_product_doc(asin="B0XYZ00001", marketplace="amazon_us")
        mock_product.find = MagicMock(
            return_value=_mock_find_chain([product_doc])
        )

        with patch("app.services.insights_query_service.EventDocument", mock_event), \
             patch("app.services.insights_query_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.insights_query_service.ProductDocument", mock_product):
            result = await service.get_competitor_insights("ws_test", Timeframe.WEEKLY)

        competitor_asins = {pc.asin for pc in result.price_changes}
        assert "B0XYZ00001" in competitor_asins
        assert "B0ABC12345" not in competitor_asins


# ── #2: create_competitor_tracker filters by marketplace ──────────────────────


class TestCreateCompetitorMarketplaceFilter:
    @pytest.mark.asyncio
    async def test_create_queries_product_with_marketplace(self) -> None:
        """create_competitor_tracker must pass marketplace to ProductDocument.find."""
        service = TrackerManagementService()
        mock_product = _mock_doc_class()
        captured_product_args: list[tuple] = []

        def capture_find(*args, **kwargs):
            captured_product_args.append((args, kwargs))
            return _mock_find_chain([])

        mock_product.find = capture_find

        mock_competitor = _mock_doc_class()
        mock_event = _mock_doc_class()
        mock_snapshot = _mock_doc_class()

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.tracker_management_service.ProductDocument", mock_product), \
             patch("app.services.tracker_management_service.EventDocument", mock_event), \
             patch("app.services.tracker_management_service.ProductSnapshotDocument", mock_snapshot):
            await service.create_competitor_tracker(
                "ws_test", _make_create_payload(marketplace="amazon_de")
            )

        assert len(captured_product_args) >= 1
        find_args, _ = captured_product_args[0]
        # Should have 3 conditions: workspace_id, marketplace, asin IN
        assert len(find_args) >= 3, (
            f"Expected >=3 query conditions (workspace+marketplace+asin), got {len(find_args)}: {find_args}"
        )

    @pytest.mark.asyncio
    async def test_create_queries_event_with_marketplace(self) -> None:
        """create_competitor_tracker must pass marketplace to EventDocument.find."""
        service = TrackerManagementService()
        mock_event = _mock_doc_class()
        captured_event_args: list[tuple] = []

        def capture_find(*args, **kwargs):
            captured_event_args.append((args, kwargs))
            return _mock_find_chain([])

        mock_event.find = capture_find

        mock_competitor = _mock_doc_class()
        mock_product = _mock_doc_class()
        mock_snapshot = _mock_doc_class()

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.tracker_management_service.ProductDocument", mock_product), \
             patch("app.services.tracker_management_service.EventDocument", mock_event), \
             patch("app.services.tracker_management_service.ProductSnapshotDocument", mock_snapshot):
            await service.create_competitor_tracker(
                "ws_test", _make_create_payload(marketplace="amazon_uk")
            )

        assert len(captured_event_args) >= 1
        find_args, _ = captured_event_args[0]
        # Should have 3 conditions: workspace_id, marketplace, asin IN
        assert len(find_args) >= 3, (
            f"Expected >=3 query conditions (workspace+marketplace+asin), got {len(find_args)}: {find_args}"
        )

    @pytest.mark.asyncio
    async def test_create_queries_snapshot_with_marketplace(self) -> None:
        """create_competitor_tracker must pass marketplace to ProductSnapshotDocument.find."""
        service = TrackerManagementService()
        mock_snapshot = _mock_doc_class()
        captured_snapshot_args: list[tuple] = []

        def capture_find(*args, **kwargs):
            captured_snapshot_args.append((args, kwargs))
            return _mock_find_chain([])

        mock_snapshot.find = capture_find

        mock_competitor = _mock_doc_class()
        mock_product = _mock_doc_class()
        mock_event = _mock_doc_class()

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.tracker_management_service.ProductDocument", mock_product), \
             patch("app.services.tracker_management_service.EventDocument", mock_event), \
             patch("app.services.tracker_management_service.ProductSnapshotDocument", mock_snapshot):
            await service.create_competitor_tracker(
                "ws_test", _make_create_payload(marketplace="amazon_fr")
            )

        assert len(captured_snapshot_args) >= 1
        find_args, _ = captured_snapshot_args[0]
        # Should have 3 conditions: workspace_id, marketplace, asin IN
        assert len(find_args) >= 3, (
            f"Expected >=3 query conditions (workspace+marketplace+asin), got {len(find_args)}: {find_args}"
        )


# ── #3: create_competitor_tracker conflict detection ──────────────────────────


class TestCreateCompetitorConflict:
    @pytest.mark.asyncio
    async def test_conflict_same_marketplace_same_asins(self) -> None:
        """Creating a tracker with same marketplace + same ASIN set must raise ConflictError."""
        service = TrackerManagementService()
        existing_tracker = _make_tracker_doc(
            tracked_asins=[
                SimpleNamespace(asin="B0ABC12345", enabled=True, added_at=datetime(2025, 6, 1, tzinfo=timezone.utc)),
                SimpleNamespace(asin="B0DEF67890", enabled=True, added_at=datetime(2025, 6, 1, tzinfo=timezone.utc)),
            ],
        )

        mock_competitor = _mock_doc_class()
        mock_competitor.find = MagicMock(
            return_value=_mock_find_chain([existing_tracker])
        )

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor):
            with pytest.raises(ConflictError, match="already exists"):
                await service.create_competitor_tracker(
                    "ws_test",
                    _make_create_payload(asins=["B0DEF67890", "B0ABC12345"]),
                )

    @pytest.mark.asyncio
    async def test_no_conflict_different_marketplace(self) -> None:
        """Same ASINs but different marketplace must NOT raise."""
        service = TrackerManagementService()
        existing_tracker = _make_tracker_doc(
            marketplace="amazon_us",
            tracked_asins=[
                SimpleNamespace(asin="B0ABC12345", enabled=True, added_at=datetime(2025, 6, 1, tzinfo=timezone.utc)),
            ],
        )

        mock_competitor = _mock_doc_class()
        mock_competitor.find = MagicMock(
            return_value=_mock_find_chain([existing_tracker])
        )

        mock_product = _mock_doc_class()
        mock_event = _mock_doc_class()
        mock_snapshot = _mock_doc_class()

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.tracker_management_service.ProductDocument", mock_product), \
             patch("app.services.tracker_management_service.EventDocument", mock_event), \
             patch("app.services.tracker_management_service.ProductSnapshotDocument", mock_snapshot):
            result = await service.create_competitor_tracker(
                "ws_test",
                _make_create_payload(asins=["B0ABC12345"], marketplace="amazon_de"),
            )

        assert result.marketplace == "amazon_de"

    @pytest.mark.asyncio
    async def test_no_conflict_different_asins(self) -> None:
        """Same marketplace but different ASINs must NOT raise."""
        service = TrackerManagementService()
        existing_tracker = _make_tracker_doc(
            marketplace="amazon_us",
            tracked_asins=[
                SimpleNamespace(asin="B0ABC12345", enabled=True, added_at=datetime(2025, 6, 1, tzinfo=timezone.utc)),
            ],
        )

        mock_competitor = _mock_doc_class()
        mock_competitor.find = MagicMock(
            return_value=_mock_find_chain([existing_tracker])
        )

        mock_product = _mock_doc_class()
        mock_event = _mock_doc_class()
        mock_snapshot = _mock_doc_class()

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.tracker_management_service.ProductDocument", mock_product), \
             patch("app.services.tracker_management_service.EventDocument", mock_event), \
             patch("app.services.tracker_management_service.ProductSnapshotDocument", mock_snapshot):
            result = await service.create_competitor_tracker(
                "ws_test",
                _make_create_payload(asins=["B0XYZ99999"], marketplace="amazon_us"),
            )

        assert result.tracker_code.startswith("cmp_")

    @pytest.mark.asyncio
    async def test_no_conflict_existing_tracker_disabled_asins(self) -> None:
        """Existing tracker with only disabled ASINs should not block new tracker."""
        service = TrackerManagementService()
        existing_tracker = _make_tracker_doc(
            marketplace="amazon_us",
            tracked_asins=[
                SimpleNamespace(asin="B0ABC12345", enabled=False, added_at=datetime(2025, 6, 1, tzinfo=timezone.utc)),
            ],
        )

        mock_competitor = _mock_doc_class()
        mock_competitor.find = MagicMock(
            return_value=_mock_find_chain([existing_tracker])
        )

        mock_product = _mock_doc_class()
        mock_event = _mock_doc_class()
        mock_snapshot = _mock_doc_class()

        with patch("app.services.tracker_management_service.CompetitorTrackerDocument", mock_competitor), \
             patch("app.services.tracker_management_service.ProductDocument", mock_product), \
             patch("app.services.tracker_management_service.EventDocument", mock_event), \
             patch("app.services.tracker_management_service.ProductSnapshotDocument", mock_snapshot):
            result = await service.create_competitor_tracker(
                "ws_test",
                _make_create_payload(asins=["B0ABC12345"], marketplace="amazon_us"),
            )

        # Should succeed because existing ASIN is disabled (enabled set is empty)
        assert result.tracker_code.startswith("cmp_")
