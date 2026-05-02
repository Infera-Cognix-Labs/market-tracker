from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from app.services.tracker_management_service import TrackerManagementService


class FakeCursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self):
        return self.items

    def sort(self, *args, **kwargs):
        return self


class FakeDocument:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._saved = False

    def model_dump(self, exclude=None, mode=None):
        exclude = set(exclude or [])
        return {
            key: value
            for key, value in self.__dict__.items()
            if key not in exclude and not key.startswith("_") and not callable(value)
        }

    async def save(self, *args, **kwargs):
        self._saved = True
        return None


def test_get_competitor_tracker_hydrates_tracked_products_from_products(
    run_async, monkeypatch, seed_data
):
    tracker = seed_data.competitor_trackers[0].model_copy(
        update={"tracked_products": []}, deep=True
    )
    tracker_doc = FakeDocument(
        workspace_id=seed_data.workspace_id,
        **tracker.model_dump(mode="python"),
    )
    tracked_asins = [item.asin for item in tracker.tracked_asins]

    all_product_docs = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **product.model_dump(mode="python"),
        )
        for product in seed_data.products
        if product.marketplace == tracker.marketplace and product.asin in tracked_asins
    ]

    all_event_docs = [
        FakeDocument(
            workspace_id=seed_data.workspace_id,
            **event.model_dump(mode="python"),
        )
        for event in seed_data.events
        if event.marketplace == tracker.marketplace
        and event.asin in tracked_asins
    ]
    product_asins = {doc.asin for doc in all_product_docs}

    async def fake_find_one(*args, **kwargs):
        return tracker_doc

    def make_product_find(*args, **kwargs):
        return FakeCursor(all_product_docs)

    def make_event_find(*args, **kwargs):
        return FakeCursor(all_event_docs)

    monkeypatch.setattr(
        "app.services.tracker_management_service.CompetitorTrackerDocument",
        SimpleNamespace(
            find_one=fake_find_one,
            workspace_id="workspace_id",
            tracker_code="tracker_code",
        ),
    )
    monkeypatch.setattr(
        "app.services.tracker_management_service.ProductDocument",
        SimpleNamespace(
            find=make_product_find,
            workspace_id="workspace_id",
            marketplace="marketplace",
            asin="asin",
        ),
    )
    monkeypatch.setattr(
        "app.services.tracker_management_service.EventDocument",
        SimpleNamespace(
            find=make_event_find,
            workspace_id="workspace_id",
            marketplace="marketplace",
            asin="asin",
            snapshot_date="snapshot_date",
        ),
    )

    result = run_async(
        TrackerManagementService().get_competitor_tracker(
            seed_data.workspace_id,
            tracker.tracker_code,
        )
    )

    assert result.tracked_products
    assert {item.asin for item in result.tracked_products} == product_asins
    assert tracker_doc._saved is True
