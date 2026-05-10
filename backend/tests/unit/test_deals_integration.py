from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.config.config import Config
from app.integrations.apify_gateway import (
    ApifyDatasetBatch,
)
from app.models.api import (
    JobStatus,
    TrackerType,
)
from app.services.result_importer_service import _load_deals_dataset


class TestLoadDealsDataset:
    def test_loads_items_from_dataset(self, run_async, monkeypatch):
        mock_items = [
            {"asin": "B0TEST1", "deal_id": "deal_1"},
            {"asin": "B0TEST2", "deal_id": "deal_2"},
        ]

        response = ApifyDatasetBatch(
            dataset_id="dataset_123",
            offset=0,
            limit=200,
            count=2,
            total=2,
            items=mock_items,
        )

        async def fake_list_items(dataset_id, limit, offset):
            return response

        gateway = SimpleNamespace(list_dataset_items=fake_list_items)

        items, total = run_async(_load_deals_dataset(gateway, "dataset_123"))
        assert total == 2
        assert len(items) == 2
        assert items[0].payload["asin"] == "B0TEST1"

    def test_handles_empty_dataset(self, run_async, monkeypatch):
        response = ApifyDatasetBatch(
            dataset_id="dataset_123",
            offset=0,
            limit=200,
            count=0,
            total=0,
            items=[],
        )

        async def fake_list_items(dataset_id, limit, offset):
            return response

        gateway = SimpleNamespace(list_dataset_items=fake_list_items)

        items, total = run_async(_load_deals_dataset(gateway, "dataset_123"))
        assert total == 0
        assert len(items) == 0

    def test_handles_single_batch(self, run_async, monkeypatch):
        items_data = [{"asin": f"B0TEST{i}"} for i in range(1, 31)]

        async def fake_list_items(dataset_id, limit, offset):
            return ApifyDatasetBatch(
                dataset_id="dataset_123",
                offset=0,
                limit=200,
                count=30,
                total=30,
                items=items_data,
            )

        gateway = SimpleNamespace(list_dataset_items=fake_list_items)

        items, total = run_async(_load_deals_dataset(gateway, "dataset_123"))
        assert total == 30
        assert len(items) == 30

    def test_handles_pagination_with_total_greater_than_batch(self, run_async, monkeypatch):
        batch1_items = [{"asin": f"B0TEST{i:02d}", "deal_id": f"deal_{i}"} for i in range(1, 51)]

        async def fake_list_items(dataset_id, limit, offset):
            return ApifyDatasetBatch(
                dataset_id="dataset_123",
                offset=0,
                limit=200,
                count=50,
                total=50,
                items=batch1_items,
            )

        gateway = SimpleNamespace(list_dataset_items=fake_list_items)

        items, total = run_async(_load_deals_dataset(gateway, "dataset_123"))
        assert total == 50
        assert len(items) == 50


class TestTriggerDealsJobEarlyReturn:
    def test_returns_none_for_non_category_tracker(self, run_async):
        from app.services.result_importer_service import _trigger_deals_job_after_category

        config = Config().apify_config
        gateway = SimpleNamespace()
        job = SimpleNamespace(
            tracker_type=TrackerType.COMPETITOR.value,
        )

        result = run_async(_trigger_deals_job_after_category(job, config, gateway))
        assert result is None

    def test_returns_none_for_failed_job(self, run_async):
        from app.services.result_importer_service import _trigger_deals_job_after_category

        config = Config().apify_config
        gateway = SimpleNamespace()
        job = SimpleNamespace(
            tracker_type=TrackerType.CATEGORY.value,
            status=JobStatus.FAILED.value,
        )

        result = run_async(_trigger_deals_job_after_category(job, config, gateway))
        assert result is None

    def test_returns_none_for_partial_success(self, run_async):
        from app.services.result_importer_service import _trigger_deals_job_after_category

        config = Config().apify_config
        gateway = SimpleNamespace()
        job = SimpleNamespace(
            tracker_type=TrackerType.CATEGORY.value,
            status=JobStatus.FAILED.value,
        )

        result = run_async(_trigger_deals_job_after_category(job, config, gateway))
        assert result is None


class TestProcessDealsJob:
    def test_returns_success_for_non_deals_job(self, run_async):
        from app.services.result_importer_service import _process_deals_job

        config = Config().apify_config
        gateway = SimpleNamespace()

        job = SimpleNamespace(job_code="job_cat_001")
        result = run_async(_process_deals_job(job, gateway, config))
        assert result == JobStatus.SUCCESS


class TestExtractDealInfoEdgeCases:
    def test_handles_null_values(self, run_async):
        from app.services.normalization_service import _extract_deal_info

        captured_at = datetime(2026, 5, 10, tzinfo=UTC)
        payload = {
            "deal_id": "abc123",
            "deal_type": "BEST_DEAL",
            "deal_state": None,
            "deal_price": {"amount": None, "currency": None},
            "list_price": None,
        }

        deal_info = _extract_deal_info(payload, captured_at)
        assert deal_info is not None
        assert deal_info.deal_id == "abc123"
        assert deal_info.deal_state is None
        assert deal_info.deal_price is None

    def test_handles_string_amount_in_deal_price(self, run_async):
        from app.services.normalization_service import _extract_deal_info

        captured_at = datetime(2026, 5, 10, tzinfo=UTC)
        payload = {
            "deal_price": {"amount": "15.99", "currency": "USD"},
            "list_price": {"amount": "19.99", "currency": "USD"},
        }

        deal_info = _extract_deal_info(payload, captured_at)
        assert deal_info is not None
        assert deal_info.deal_price == 15.99
        assert deal_info.list_price == 19.99

    def test_handles_missing_deal_fields(self, run_async):
        from app.services.normalization_service import _extract_deal_info

        captured_at = datetime(2026, 5, 10, tzinfo=UTC)
        payload = {
            "asin": "B0TEST12345",
            "title": "Test Product",
            "price_current": 29.99,
        }

        deal_info = _extract_deal_info(payload, captured_at)
        assert deal_info is None


class TestDealsBindingConfig:
    def test_deals_binding_resolved_correctly(self, run_async):
        from app.integrations.apify_gateway import ApifyGateway

        config = Config()
        gateway = ApifyGateway(config.apify_config)

        target = gateway.resolve_binding("bind_deals_v1")
        assert target.binding_code == "bind_deals_v1"
        assert target.actor_id == "hJNp8X1wuz14Wc5wU"

    def test_deals_config_has_max_results(self, run_async):

        config = Config()
        assert config.apify_config.deals_max_results >= 30

    def test_deals_config_has_actor_id(self, run_async):

        config = Config()
        assert config.apify_config.deals_actor_id is not None


class TestJobStatusDeals:
    def test_deals_importing_status_exists(self, run_async):
        assert hasattr(JobStatus, "DEALS_IMPORTING")
        assert JobStatus.DEALS_IMPORTING.value == "DEALS_IMPORTING"

    def test_deals_processing_status_exists(self, run_async):
        assert hasattr(JobStatus, "DEALS_PROCESSING")
        assert JobStatus.DEALS_PROCESSING.value == "DEALS_PROCESSING"


class TestNormalizeItemsWithDeals:
    def test_normalize_items_with_deal_data(self, run_async):
        from app.services.normalization_service import NormalizationService, RawImportedItem

        service = NormalizationService()
        raw_items = [
            RawImportedItem(
                batch_no=1,
                item_index=0,
                payload={
                    "asin": "B0TEST123AB",
                    "title": "Test Product",
                    "deal_id": "deal_123",
                    "deal_type": "BEST_DEAL",
                    "deal_state": "AVAILABLE",
                    "deal_price": {"amount": 15.99, "currency": "USD"},
                    "list_price": {"amount": 19.99, "currency": "USD"},
                    "savings_percentage": 20,
                    "scrapedAt": "2026-05-10T00:00:00Z",
                },
            )
        ]

        result = service.normalize_items(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_us",
            raw_items=raw_items,
        )

        assert len(result.records) == 1
        record = result.records[0]
        assert record.asin == "B0TEST123AB"
        assert record.deal_info is not None
        assert record.deal_info.deal_id == "deal_123"
        assert record.deal_info.deal_price == 15.99
        assert record.deal_info.savings_percentage == 20

    def test_normalize_items_without_deal_data(self, run_async):
        from app.services.normalization_service import NormalizationService, RawImportedItem

        service = NormalizationService()
        raw_items = [
            RawImportedItem(
                batch_no=1,
                item_index=0,
                payload={
                    "asin": "B0NORMAL1AB",
                    "title": "Normal Product",
                    "price": 29.99,
                    "scrapedAt": "2026-05-10T00:00:00Z",
                },
            )
        ]

        result = service.normalize_items(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_us",
            raw_items=raw_items,
        )

        assert len(result.records) == 1
        record = result.records[0]
        assert record.deal_info is None
        assert record.price_current == 29.99

    def test_normalize_deals_uses_deal_price_for_price_current(self, run_async):
        from app.services.normalization_service import NormalizationService, RawImportedItem

        service = NormalizationService()
        raw_items = [
            RawImportedItem(
                batch_no=1,
                item_index=0,
                payload={
                    "asin": "B0DEAL123AB",
                    "title": "Deal Product",
                    "deal_price": {"amount": 14.99, "currency": "USD"},
                    "list_price": {"amount": 19.99, "currency": "USD"},
                    "scrapedAt": "2026-05-10T00:00:00Z",
                },
            )
        ]

        result = service.normalize_items(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_us",
            raw_items=raw_items,
        )

        assert len(result.records) == 1
        record = result.records[0]
        assert record.price_current == 14.99
        assert record.price_original == 19.99
        assert record.deal_info is not None

    def test_normalize_items_extracts_nested_savings_amount(self, run_async):
        from app.services.normalization_service import NormalizationService, RawImportedItem

        service = NormalizationService()
        raw_items = [
            RawImportedItem(
                batch_no=1,
                item_index=0,
                payload={
                    "asin": "B0SAVE12345B",
                    "title": "Savings Product",
                    "deal_price": {"amount": 10.0, "currency": "USD"},
                    "savings_amount": {"amount": 5.0, "currency": "USD"},
                    "savings_percentage": 33,
                    "scrapedAt": "2026-05-10T00:00:00Z",
                },
            )
        ]

        result = service.normalize_items(
            tracker_type=TrackerType.CATEGORY,
            marketplace="amazon_us",
            raw_items=raw_items,
        )

        assert len(result.records) == 1
        record = result.records[0]
        assert record.deal_info is not None
        assert record.deal_info.savings_amount == 5.0
        assert record.deal_info.savings_percentage == 33