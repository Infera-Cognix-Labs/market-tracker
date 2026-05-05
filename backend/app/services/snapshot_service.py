from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import NotFoundError
from app.core.utils import utc_now
from app.models.api import (
    CategorySnapshotProduct,
    CategorySnapshotSummary,
    CategoryTrackerLatestSnapshotSummary,
    ProductCurrentState,
    TrackerRef,
    TrackerType,
)
from app.models.documents import (
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    JobDocument,
    ProductDocument,
    ProductSnapshotDocument,
)
from app.services.normalization_service import NormalizedProductRecord


@dataclass(frozen=True)
class SnapshotPersistResult:
    category_snapshot_written: bool
    product_snapshots_written: int


class SnapshotService:
    async def persist_snapshots(
        self,
        *,
        workspace_id: str,
        job_document: JobDocument,
        apify_run_id: str,
        dataset_id: str,
        records: list[NormalizedProductRecord],
    ) -> SnapshotPersistResult:
        tracker_type = TrackerType(job_document.tracker_type)
        tracker_document = await self._load_tracker_document(
            workspace_id=workspace_id,
            tracker_type=tracker_type,
            tracker_code=job_document.tracker_code,
        )
        tracker_ref = TrackerRef(
            tracker_type=tracker_type,
            tracker_code=job_document.tracker_code,
            tracker_name=tracker_document.name,
        )

        product_snapshots_written = 0
        for record in records:
            source_refs = {
                "provider": "APIFY",
                "apify_run_id": apify_run_id,
                "dataset_id": dataset_id,
                "batch_no": record.source_batch_no,
                "item_index": record.source_item_index,
            }
            inserted_snapshot = await self._upsert_product_snapshot(
                workspace_id=workspace_id,
                snapshot_date=job_document.snapshot_date,
                tracker_ref=tracker_ref,
                record=record,
                source_refs=source_refs,
            )
            if inserted_snapshot:
                product_snapshots_written += 1
            await self._upsert_product_registry(
                workspace_id=workspace_id,
                snapshot_date=job_document.snapshot_date,
                tracker_ref=tracker_ref,
                record=record,
            )

        category_snapshot_written = False
        if tracker_type == TrackerType.CATEGORY:
            category_snapshot_written = await self._upsert_category_snapshot(
                workspace_id=workspace_id,
                snapshot_date=job_document.snapshot_date,
                tracker_code=job_document.tracker_code,
                tracker_document=tracker_document,
                records=records,
                apify_run_id=apify_run_id,
                dataset_id=dataset_id,
            )

        return SnapshotPersistResult(
            category_snapshot_written=category_snapshot_written,
            product_snapshots_written=product_snapshots_written,
        )

    async def _load_tracker_document(
        self,
        *,
        workspace_id: str,
        tracker_type: TrackerType,
        tracker_code: str,
    ) -> CategoryTrackerDocument | CompetitorTrackerDocument:
        if tracker_type == TrackerType.CATEGORY:
            tracker_document = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == workspace_id,
                CategoryTrackerDocument.tracker_code == tracker_code,
            )
            if tracker_document is None:
                raise NotFoundError("Category tracker not found.")
            return tracker_document

        tracker_document = await CompetitorTrackerDocument.find_one(
            CompetitorTrackerDocument.workspace_id == workspace_id,
            CompetitorTrackerDocument.tracker_code == tracker_code,
        )
        if tracker_document is None:
            raise NotFoundError("Competitor tracker not found.")
        return tracker_document

    async def _upsert_product_snapshot(
        self,
        *,
        workspace_id: str,
        snapshot_date,
        tracker_ref: TrackerRef,
        record: NormalizedProductRecord,
        source_refs: dict[str, object],
    ) -> bool:
        existing = await ProductSnapshotDocument.find_one(
            ProductSnapshotDocument.workspace_id == workspace_id,
            ProductSnapshotDocument.marketplace == record.marketplace,
            ProductSnapshotDocument.asin == record.asin,
            ProductSnapshotDocument.snapshot_date == snapshot_date,
        )

        tracker_refs = (
            _merge_tracker_refs(existing.tracker_refs, tracker_ref)
            if existing is not None
            else [tracker_ref]
        )

        payload = {
            "marketplace": record.marketplace,
            "asin": record.asin,
            "snapshot_date": snapshot_date,
            "captured_at": record.captured_at,
            "tracker_refs": tracker_refs,
            "parent_asin": None,
            "brand": record.brand,
            "title": record.title,
            "title_hash": record.title_hash,
            "product_url": record.product_url,
            "main_image_url": record.main_image_url,
            "main_image_hash": record.main_image_hash,
            "bsr_position": record.bsr_position,
            "price_current": record.price_current,
            "price_original": record.price_original,
            "currency": record.currency,
            "coupon_text": record.coupon_text,
            "availability_status": record.availability_status,
            "buy_box_status": record.buy_box_status,
            "buy_box_seller_name": record.buy_box_seller_name,
            "rating_value": record.rating_value,
            "review_count": record.review_count,
            "variation_count": record.variation_count,
            "source_refs": source_refs,
            "created_at": existing.created_at if existing is not None else utc_now(),
        }

        if existing is None:
            await ProductSnapshotDocument(workspace_id=workspace_id, **payload).insert()
            return True

        merged_keys = {(ref.tracker_type, ref.tracker_code) for ref in tracker_refs}
        existing_keys = {
            (ref.tracker_type, ref.tracker_code) for ref in existing.tracker_refs
        }
        if merged_keys != existing_keys:
            existing.tracker_refs = tracker_refs
            await existing.save()
        return False

    async def _upsert_product_registry(
        self,
        *,
        workspace_id: str,
        snapshot_date,
        tracker_ref: TrackerRef,
        record: NormalizedProductRecord,
    ) -> None:
        existing = await ProductDocument.find_one(
            ProductDocument.workspace_id == workspace_id,
            ProductDocument.marketplace == record.marketplace,
            ProductDocument.asin == record.asin,
        )

        current_state = ProductCurrentState(
            price_current=record.price_current,
            price_original=record.price_original,
            currency=record.currency,
            bsr_position=record.bsr_position,
            availability_status=record.availability_status,
            buy_box_status=record.buy_box_status,
            buy_box_seller_name=record.buy_box_seller_name,
            coupon_text=record.coupon_text,
            last_snapshot_date=snapshot_date,
        )

        if existing is None:
            now = utc_now()
            await ProductDocument(
                workspace_id=workspace_id,
                marketplace=record.marketplace,
                asin=record.asin,
                parent_asin=None,
                brand=record.brand,
                title_latest=record.title,
                product_url=record.product_url,
                main_image_url_latest=record.main_image_url,
                first_seen_at=now,
                last_seen_at=record.captured_at,
                current_state=current_state,
                tracker_refs=[tracker_ref],
            ).insert()
            return

        existing.brand = record.brand
        existing.title_latest = record.title
        existing.product_url = record.product_url
        existing.main_image_url_latest = record.main_image_url
        existing.last_seen_at = record.captured_at
        existing.current_state = current_state
        existing.tracker_refs = _merge_tracker_refs(existing.tracker_refs, tracker_ref)
        await existing.save()

    async def _upsert_category_snapshot(
        self,
        *,
        workspace_id: str,
        snapshot_date,
        tracker_code: str,
        tracker_document: CategoryTrackerDocument | CompetitorTrackerDocument,
        records: list[NormalizedProductRecord],
        apify_run_id: str,
        dataset_id: str,
    ) -> bool:
        if not isinstance(tracker_document, CategoryTrackerDocument):
            return False

        sorted_records = sorted(
            records,
            key=lambda item: (
                item.rank_position if item.rank_position is not None else 10_000
            ),
        )
        top_n = tracker_document.tracking_config.top_n
        unique_top_records = _dedupe_category_records(
            sorted_records,
            limit=top_n,
        )
        products = [
            CategorySnapshotProduct(
                asin=record.asin,
                rank_position=index,
                title=record.title,
                brand=record.brand,
                product_url=record.product_url,
                price_current=record.price_current or 0.0,
                price_original=record.price_original,
                currency=record.currency or "USD",
                rating_value=record.rating_value or 0.0,
                review_count=record.review_count or 0,
                image_url=record.main_image_url,
                availability_status=record.availability_status,
                buy_box_status=record.buy_box_status,
                coupon_text=record.coupon_text,
            )
            for index, record in enumerate(unique_top_records, start=1)
        ]

        current_asins = {p.asin for p in products}
        current_top10_asins = {p.asin for p in products[:10]}

        previous_snapshot = await CategorySnapshotDocument.find(
            CategorySnapshotDocument.workspace_id == workspace_id,
            CategorySnapshotDocument.tracker_code == tracker_code,
            CategorySnapshotDocument.snapshot_date < snapshot_date,
        ).sort("snapshot_date", -1).first()
        previous_asins = set()
        previous_top10_asins = set()
        if previous_snapshot:
            previous_asins = {p.asin for p in previous_snapshot.products}
            previous_top10_asins = {p.asin for p in previous_snapshot.products[:10]}

        new_entrants = current_asins - previous_asins
        exits = previous_asins - current_asins

        enter_top10 = current_top10_asins - previous_top10_asins
        exit_top10 = previous_top10_asins - current_top10_asins

        payload = {
            "tracker_code": tracker_code,
            "marketplace": tracker_document.marketplace,
            "browse_node_id": (
                tracker_document.scope.browse_node_id
                or tracker_document.scope.browse_node_url
                or "unknown"
            ),
            "snapshot_date": snapshot_date,
            "captured_at": utc_now(),
            "top_n": top_n,
            "products": products,
            "summary": CategorySnapshotSummary(
                asin_count=len(products),
                new_entrant_count=len(new_entrants),
                returning_count=0,
                exit_count=len(exits),
                enter_top10_count=len(enter_top10),
                exit_top10_count=len(exit_top10),
            ),
            "source_refs": {
                "provider": "APIFY",
                "apify_run_id": apify_run_id,
                "dataset_id": dataset_id,
            },
        }
        latest_snapshot_summary = CategoryTrackerLatestSnapshotSummary(
            snapshot_date=snapshot_date,
            captured_at=payload["captured_at"],
            top10_asins=[item.asin for item in products[:10]],
        )
        tracker_document.latest_snapshot_summary = latest_snapshot_summary
        tracker_document.updated_at = utc_now()
        await tracker_document.save()

        existing = await CategorySnapshotDocument.find_one(
            CategorySnapshotDocument.workspace_id == workspace_id,
            CategorySnapshotDocument.tracker_code == tracker_code,
            CategorySnapshotDocument.snapshot_date == snapshot_date,
        )
        if existing is None:
            await CategorySnapshotDocument(
                workspace_id=workspace_id, **payload
            ).insert()
            return True

        return False


def _merge_tracker_refs(existing_refs, new_ref: TrackerRef) -> list[TrackerRef]:
    merged = {(ref.tracker_type, ref.tracker_code): ref for ref in existing_refs}
    merged[(new_ref.tracker_type, new_ref.tracker_code)] = new_ref
    return list(merged.values())


def _dedupe_category_records(
    records: list[NormalizedProductRecord],
    *,
    limit: int,
) -> list[NormalizedProductRecord]:
    unique_records: list[NormalizedProductRecord] = []
    seen_asins: set[str] = set()
    
    for record in records:
        if record.asin in seen_asins:
            continue
        seen_asins.add(record.asin)
        unique_records.append(record)

    return unique_records[:limit]
