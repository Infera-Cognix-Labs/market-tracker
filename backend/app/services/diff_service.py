from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.models.api import EventType, TrackerType
from app.models.documents import CategorySnapshotDocument, KeywordSnapshotDocument, ProductSnapshotDocument


@dataclass(frozen=True)
class DiffCandidate:
    tracker_type: TrackerType
    tracker_code: str
    marketplace: str
    asin: str
    event_type: EventType
    snapshot_date: date
    event_time: datetime
    metadata: dict[str, object] = field(default_factory=dict)


class DiffService:
    async def build_candidates(
        self,
        *,
        workspace_id: str,
        tracker_type: TrackerType,
        tracker_code: str,
        snapshot_date: date,
    ) -> list[DiffCandidate]:
        candidates: list[DiffCandidate] = []
        if tracker_type == TrackerType.CATEGORY:
            candidates.extend(
                await self._build_category_movement_candidates(
                    workspace_id=workspace_id,
                    tracker_code=tracker_code,
                    snapshot_date=snapshot_date,
                )
            )
        elif tracker_type == TrackerType.KEYWORD:
            candidates.extend(
                await self._build_keyword_movement_candidates(
                    workspace_id=workspace_id,
                    tracker_code=tracker_code,
                    snapshot_date=snapshot_date,
                )
            )

        candidates.extend(
            await self._build_product_change_candidates(
                workspace_id=workspace_id,
                tracker_type=tracker_type,
                tracker_code=tracker_code,
                snapshot_date=snapshot_date,
            )
        )
        return candidates

    async def _build_category_movement_candidates(
        self,
        *,
        workspace_id: str,
        tracker_code: str,
        snapshot_date: date,
    ) -> list[DiffCandidate]:
        current_snapshot = await CategorySnapshotDocument.find_one(
            {
                "workspace_id": workspace_id,
                "tracker_code": tracker_code,
                "snapshot_date": snapshot_date,
            }
        )
        if current_snapshot is None:
            return []

        # Get the most recent previous snapshot (single query instead of loading all)
        previous_snapshot = await CategorySnapshotDocument.find_one(
            {
                "workspace_id": workspace_id,
                "tracker_code": tracker_code,
                "snapshot_date": {"$lt": snapshot_date},
            },
            sort=[("snapshot_date", -1)],
        )
        # Get all older snapshots for historical_last_seen tracking
        history_snapshots = await CategorySnapshotDocument.find(
            {
                "workspace_id": workspace_id,
                "tracker_code": tracker_code,
                "snapshot_date": {"$lt": snapshot_date},
            }
        ).to_list()
        current_products = _dedupe_category_snapshot_products(current_snapshot.products)
        previous_products = (
            _dedupe_category_snapshot_products(previous_snapshot.products)
            if previous_snapshot is not None
            else []
        )

        current_rank_map = {
            product.asin: product.rank_position for product in current_products
        }
        current_product_map = {
            product.asin: product for product in current_products
        }
        previous_rank_map = (
            {product.asin: product.rank_position for product in previous_products}
            if previous_snapshot is not None
            else {}
        )
        previous_product_map = {
            product.asin: product for product in previous_products
        }

        # Keep the most recent observed date for each ASIN in historical snapshots.
        historical_last_seen: dict[str, date] = {}
        for snapshot in history_snapshots:
            for product in _dedupe_category_snapshot_products(snapshot.products):
                last_seen = historical_last_seen.get(product.asin)
                if last_seen is None or snapshot.snapshot_date > last_seen:
                    historical_last_seen[product.asin] = snapshot.snapshot_date

        candidates: list[DiffCandidate] = []
        event_time = current_snapshot.captured_at
        marketplace = current_snapshot.marketplace

        for asin, current_rank in current_rank_map.items():
            previous_rank = previous_rank_map.get(asin)
            if previous_rank is None:
                last_seen_date = historical_last_seen.get(asin)
                if last_seen_date is None:
                    candidates.append(
                        DiffCandidate(
                            tracker_type=TrackerType.CATEGORY,
                            tracker_code=tracker_code,
                            marketplace=marketplace,
                            asin=asin,
                            event_type=EventType.NEW_ENTRANT_TOP50,
                            snapshot_date=snapshot_date,
                            event_time=event_time,
                            metadata={
                                "rank_today": current_rank,
                                "first_seen_in_tracker": True,
                            },
                        )
                    )
                else:
                    candidates.append(
                        DiffCandidate(
                            tracker_type=TrackerType.CATEGORY,
                            tracker_code=tracker_code,
                            marketplace=marketplace,
                            asin=asin,
                            event_type=EventType.RETURNING_TOP50,
                            snapshot_date=snapshot_date,
                            event_time=event_time,
                            metadata={
                                "rank_today": current_rank,
                                "last_seen_date": last_seen_date,
                                "days_absent": max(
                                    0,
                                    (snapshot_date - last_seen_date).days - 1,
                                ),
                            },
                        )
                    )

            if current_rank <= 10 and (previous_rank is None or previous_rank > 10):
                candidates.append(
                    DiffCandidate(
                        tracker_type=TrackerType.CATEGORY,
                        tracker_code=tracker_code,
                        marketplace=marketplace,
                        asin=asin,
                        event_type=EventType.ENTER_TOP10,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_rank": previous_rank,
                            "current_rank": current_rank,
                        },
                    )
                )
            if previous_rank is not None and previous_rank <= 10 and current_rank > 10:
                prev_product = previous_product_map.get(asin)
                cur_product = current_product_map.get(asin)
                candidates.append(
                    DiffCandidate(
                        tracker_type=TrackerType.CATEGORY,
                        tracker_code=tracker_code,
                        marketplace=marketplace,
                        asin=asin,
                        event_type=EventType.EXIT_TOP10,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_rank": previous_rank,
                            "current_rank": current_rank,
                            "previous_title": prev_product.title if prev_product else None,
                            "previous_brand": prev_product.brand if prev_product else None,
                            "previous_image_url": prev_product.image_url if prev_product else None,
                            "previous_price_current": prev_product.price_current if prev_product else None,
                            "previous_price_original": prev_product.price_original if prev_product else None,
                            "previous_currency": prev_product.currency if prev_product else None,
                            "previous_coupon_text": prev_product.coupon_text if prev_product else None,
                            "previous_deal_info": prev_product.deal_info.model_dump() if prev_product and prev_product.deal_info else None,
                            "previous_rating_value": prev_product.rating_value if prev_product else None,
                            "previous_review_count": prev_product.review_count if prev_product else None,
                            "previous_product_url": prev_product.product_url if prev_product else None,
                            "previous_availability_status": prev_product.availability_status if prev_product else None,
                            "previous_buy_box_status": prev_product.buy_box_status if prev_product else None,
                            "current_title": cur_product.title if cur_product else None,
                            "current_brand": cur_product.brand if cur_product else None,
                            "current_image_url": cur_product.image_url if cur_product else None,
                            "current_price_current": cur_product.price_current if cur_product else None,
                            "current_price_original": cur_product.price_original if cur_product else None,
                            "current_coupon_text": cur_product.coupon_text if cur_product else None,
                            "current_deal_info": cur_product.deal_info.model_dump() if cur_product and cur_product.deal_info else None,
                            "current_availability_status": cur_product.availability_status if cur_product else None,
                            "current_buy_box_status": cur_product.buy_box_status if cur_product else None,
                        },
                    )
                )

        for asin, previous_rank in previous_rank_map.items():
            if asin in current_rank_map:
                continue

            prev_product = previous_product_map.get(asin)
            candidates.append(
                DiffCandidate(
                    tracker_type=TrackerType.CATEGORY,
                    tracker_code=tracker_code,
                    marketplace=marketplace,
                    asin=asin,
                    event_type=EventType.EXIT_TOP50,
                    snapshot_date=snapshot_date,
                    event_time=event_time,
                    metadata={
                        "previous_rank": previous_rank,
                        "present_today": False,
                        "previous_title": prev_product.title if prev_product else None,
                        "previous_brand": prev_product.brand if prev_product else None,
                        "previous_image_url": prev_product.image_url if prev_product else None,
                        "previous_price_current": prev_product.price_current if prev_product else None,
                        "previous_price_original": prev_product.price_original if prev_product else None,
                        "previous_currency": prev_product.currency if prev_product else None,
                        "previous_coupon_text": prev_product.coupon_text if prev_product else None,
                        "previous_deal_info": prev_product.deal_info.model_dump() if prev_product and prev_product.deal_info else None,
                        "previous_rating_value": prev_product.rating_value if prev_product else None,
                        "previous_review_count": prev_product.review_count if prev_product else None,
                        "previous_product_url": prev_product.product_url if prev_product else None,
                        "previous_availability_status": prev_product.availability_status if prev_product else None,
                        "previous_buy_box_status": prev_product.buy_box_status if prev_product else None,
                    },
                )
            )
            if previous_rank <= 10:
                candidates.append(
                    DiffCandidate(
                        tracker_type=TrackerType.CATEGORY,
                        tracker_code=tracker_code,
                        marketplace=marketplace,
                        asin=asin,
                        event_type=EventType.EXIT_TOP10,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_rank": previous_rank,
                            "current_rank": None,
                            "previous_title": prev_product.title if prev_product else None,
                            "previous_brand": prev_product.brand if prev_product else None,
                            "previous_image_url": prev_product.image_url if prev_product else None,
                            "previous_price_current": prev_product.price_current if prev_product else None,
                            "previous_price_original": prev_product.price_original if prev_product else None,
                            "previous_coupon_text": prev_product.coupon_text if prev_product else None,
                            "previous_deal_info": prev_product.deal_info.model_dump() if prev_product and prev_product.deal_info else None,
                            "previous_rating_value": prev_product.rating_value if prev_product else None,
                            "previous_review_count": prev_product.review_count if prev_product else None,
                            "previous_availability_status": prev_product.availability_status if prev_product else None,
                            "previous_buy_box_status": prev_product.buy_box_status if prev_product else None,
                        },
                    )
                )

        return candidates

    async def _build_keyword_movement_candidates(
        self,
        *,
        workspace_id: str,
        tracker_code: str,
        snapshot_date: date,
    ) -> list[DiffCandidate]:
        current_snapshot = await KeywordSnapshotDocument.find_one(
            {
                "workspace_id": workspace_id,
                "tracker_code": tracker_code,
                "snapshot_date": snapshot_date,
            }
        )
        if current_snapshot is None:
            return []

        previous_snapshot = await KeywordSnapshotDocument.find_one(
            {
                "workspace_id": workspace_id,
                "tracker_code": tracker_code,
                "snapshot_date": {"$lt": snapshot_date},
            },
            sort=[("snapshot_date", -1)],
        )
        history_snapshots = await KeywordSnapshotDocument.find(
            {
                "workspace_id": workspace_id,
                "tracker_code": tracker_code,
                "snapshot_date": {"$lt": snapshot_date},
            }
        ).to_list()
        current_products = _dedupe_category_snapshot_products(current_snapshot.products)
        previous_products = (
            _dedupe_category_snapshot_products(previous_snapshot.products)
            if previous_snapshot is not None
            else []
        )

        current_rank_map = {
            product.asin: product.rank_position for product in current_products
        }
        current_product_map = {
            product.asin: product for product in current_products
        }
        previous_rank_map = (
            {product.asin: product.rank_position for product in previous_products}
            if previous_snapshot is not None
            else {}
        )
        previous_product_map = {
            product.asin: product for product in previous_products
        }

        historical_last_seen: dict[str, date] = {}
        for snapshot in history_snapshots:
            for product in _dedupe_category_snapshot_products(snapshot.products):
                last_seen = historical_last_seen.get(product.asin)
                if last_seen is None or snapshot.snapshot_date > last_seen:
                    historical_last_seen[product.asin] = snapshot.snapshot_date

        candidates: list[DiffCandidate] = []
        event_time = current_snapshot.captured_at
        marketplace = current_snapshot.marketplace

        for asin, current_rank in current_rank_map.items():
            previous_rank = previous_rank_map.get(asin)
            if previous_rank is None:
                last_seen_date = historical_last_seen.get(asin)
                if last_seen_date is None:
                    candidates.append(
                        DiffCandidate(
                            tracker_type=TrackerType.KEYWORD,
                            tracker_code=tracker_code,
                            marketplace=marketplace,
                            asin=asin,
                            event_type=EventType.NEW_ENTRANT_TOP50,
                            snapshot_date=snapshot_date,
                            event_time=event_time,
                            metadata={
                                "rank_today": current_rank,
                                "first_seen_in_tracker": True,
                            },
                        )
                    )
                else:
                    candidates.append(
                        DiffCandidate(
                            tracker_type=TrackerType.KEYWORD,
                            tracker_code=tracker_code,
                            marketplace=marketplace,
                            asin=asin,
                            event_type=EventType.RETURNING_TOP50,
                            snapshot_date=snapshot_date,
                            event_time=event_time,
                            metadata={
                                "rank_today": current_rank,
                                "last_seen_date": last_seen_date,
                                "days_absent": max(
                                    0,
                                    (snapshot_date - last_seen_date).days - 1,
                                ),
                            },
                        )
                    )

            if current_rank <= 10 and (previous_rank is None or previous_rank > 10):
                candidates.append(
                    DiffCandidate(
                        tracker_type=TrackerType.KEYWORD,
                        tracker_code=tracker_code,
                        marketplace=marketplace,
                        asin=asin,
                        event_type=EventType.ENTER_TOP10,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_rank": previous_rank,
                            "current_rank": current_rank,
                        },
                    )
                )
            if previous_rank is not None and previous_rank <= 10 and current_rank > 10:
                prev_product = previous_product_map.get(asin)
                cur_product = current_product_map.get(asin)
                candidates.append(
                    DiffCandidate(
                        tracker_type=TrackerType.KEYWORD,
                        tracker_code=tracker_code,
                        marketplace=marketplace,
                        asin=asin,
                        event_type=EventType.EXIT_TOP10,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_rank": previous_rank,
                            "current_rank": current_rank,
                            "previous_title": prev_product.title if prev_product else None,
                            "previous_brand": prev_product.brand if prev_product else None,
                            "previous_image_url": prev_product.image_url if prev_product else None,
                            "previous_price_current": prev_product.price_current if prev_product else None,
                            "previous_price_original": prev_product.price_original if prev_product else None,
                            "previous_currency": prev_product.currency if prev_product else None,
                            "previous_coupon_text": prev_product.coupon_text if prev_product else None,
                            "previous_deal_info": prev_product.deal_info.model_dump() if prev_product and prev_product.deal_info else None,
                            "previous_rating_value": prev_product.rating_value if prev_product else None,
                            "previous_review_count": prev_product.review_count if prev_product else None,
                            "previous_product_url": prev_product.product_url if prev_product else None,
                            "previous_availability_status": prev_product.availability_status if prev_product else None,
                            "previous_buy_box_status": prev_product.buy_box_status if prev_product else None,
                            "current_title": cur_product.title if cur_product else None,
                            "current_brand": cur_product.brand if cur_product else None,
                            "current_image_url": cur_product.image_url if cur_product else None,
                            "current_price_current": cur_product.price_current if cur_product else None,
                            "current_price_original": cur_product.price_original if cur_product else None,
                            "current_coupon_text": cur_product.coupon_text if cur_product else None,
                            "current_deal_info": cur_product.deal_info.model_dump() if cur_product and cur_product.deal_info else None,
                            "current_availability_status": cur_product.availability_status if cur_product else None,
                            "current_buy_box_status": cur_product.buy_box_status if cur_product else None,
                        },
                    )
                )

        for asin, previous_rank in previous_rank_map.items():
            if asin in current_rank_map:
                continue

            prev_product = previous_product_map.get(asin)
            candidates.append(
                DiffCandidate(
                    tracker_type=TrackerType.KEYWORD,
                    tracker_code=tracker_code,
                    marketplace=marketplace,
                    asin=asin,
                    event_type=EventType.EXIT_TOP50,
                    snapshot_date=snapshot_date,
                    event_time=event_time,
                    metadata={
                        "previous_rank": previous_rank,
                        "present_today": False,
                        "previous_title": prev_product.title if prev_product else None,
                        "previous_brand": prev_product.brand if prev_product else None,
                        "previous_image_url": prev_product.image_url if prev_product else None,
                        "previous_price_current": prev_product.price_current if prev_product else None,
                        "previous_price_original": prev_product.price_original if prev_product else None,
                        "previous_currency": prev_product.currency if prev_product else None,
                        "previous_coupon_text": prev_product.coupon_text if prev_product else None,
                        "previous_deal_info": prev_product.deal_info.model_dump() if prev_product and prev_product.deal_info else None,
                        "previous_rating_value": prev_product.rating_value if prev_product else None,
                        "previous_review_count": prev_product.review_count if prev_product else None,
                        "previous_product_url": prev_product.product_url if prev_product else None,
                        "previous_availability_status": prev_product.availability_status if prev_product else None,
                        "previous_buy_box_status": prev_product.buy_box_status if prev_product else None,
                    },
                )
            )
            if previous_rank <= 10:
                candidates.append(
                    DiffCandidate(
                        tracker_type=TrackerType.KEYWORD,
                        tracker_code=tracker_code,
                        marketplace=marketplace,
                        asin=asin,
                        event_type=EventType.EXIT_TOP10,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_rank": previous_rank,
                            "current_rank": None,
                            "previous_title": prev_product.title if prev_product else None,
                            "previous_brand": prev_product.brand if prev_product else None,
                            "previous_image_url": prev_product.image_url if prev_product else None,
                            "previous_price_current": prev_product.price_current if prev_product else None,
                            "previous_price_original": prev_product.price_original if prev_product else None,
                            "previous_coupon_text": prev_product.coupon_text if prev_product else None,
                            "previous_deal_info": prev_product.deal_info.model_dump() if prev_product and prev_product.deal_info else None,
                            "previous_rating_value": prev_product.rating_value if prev_product else None,
                            "previous_review_count": prev_product.review_count if prev_product else None,
                            "previous_availability_status": prev_product.availability_status if prev_product else None,
                            "previous_buy_box_status": prev_product.buy_box_status if prev_product else None,
                        },
                    )
                )

        return candidates

    async def _build_product_change_candidates(
        self,
        *,
        workspace_id: str,
        tracker_type: TrackerType,
        tracker_code: str,
        snapshot_date: date,
    ) -> list[DiffCandidate]:
        current_snapshots = await ProductSnapshotDocument.find(
            {
                "workspace_id": workspace_id,
                "snapshot_date": snapshot_date,
                "tracker_refs.tracker_code": tracker_code,
            }
        ).to_list()
        if not current_snapshots:
            return []

        # Batch query: find all previous snapshots for these products in one query
        asin_pairs = [
            {"marketplace": cs.marketplace, "asin": cs.asin}
            for cs in current_snapshots
        ]
        previous_docs = await ProductSnapshotDocument.find(
            {
                "workspace_id": workspace_id,
                "$or": asin_pairs,
                "snapshot_date": {"$lt": snapshot_date},
            }
        ).to_list()

        # Group by (marketplace, asin) and keep only the most recent
        previous_map: dict[tuple[str, str], ProductSnapshotDocument] = {}
        for doc in previous_docs:
            key = (doc.marketplace, doc.asin)
            existing = previous_map.get(key)
            if existing is None or doc.snapshot_date > existing.snapshot_date:
                previous_map[key] = doc

        candidates: list[DiffCandidate] = []
        for current_snapshot in current_snapshots:
            previous_snapshot = previous_map.get(
                (current_snapshot.marketplace, current_snapshot.asin)
            )
            if previous_snapshot is None:
                continue

            event_time = current_snapshot.captured_at

            price_changed = (
                previous_snapshot.price_current != current_snapshot.price_current
                or previous_snapshot.price_original != current_snapshot.price_original
            )
            if price_changed:
                previous_price = previous_snapshot.price_current
                current_price = current_snapshot.price_current
                delta_abs = None
                delta_pct = None
                if previous_price is not None and current_price is not None:
                    delta_abs = current_price - previous_price
                    if previous_price != 0:
                        delta_pct = (delta_abs / previous_price) * 100

                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.PRICE_CHANGED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_price_current": previous_snapshot.price_current,
                            "previous_price_original": previous_snapshot.price_original,
                            "current_price_current": current_snapshot.price_current,
                            "current_price_original": current_snapshot.price_original,
                            "delta_abs": delta_abs,
                            "delta_pct": delta_pct,
                        },
                    )
                )

            if previous_snapshot.coupon_text != current_snapshot.coupon_text:
                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.PROMOTION_CHANGED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_coupon_text": previous_snapshot.coupon_text,
                            "current_coupon_text": current_snapshot.coupon_text,
                        },
                    )
                )

            if previous_snapshot.title_hash != current_snapshot.title_hash:
                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.TITLE_CHANGED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_title": previous_snapshot.title,
                            "current_title": current_snapshot.title,
                        },
                    )
                )

            image_changed = (
                previous_snapshot.main_image_hash != current_snapshot.main_image_hash
                or previous_snapshot.main_image_url != current_snapshot.main_image_url
            )
            if image_changed:
                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.MAIN_IMAGE_CHANGED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_main_image_url": previous_snapshot.main_image_url,
                            "current_main_image_url": current_snapshot.main_image_url,
                        },
                    )
                )

            previous_variation_count = previous_snapshot.variation_count or 0
            current_variation_count = current_snapshot.variation_count or 0
            if current_variation_count > previous_variation_count:
                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.VARIATIONS_ADDED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_variation_count": previous_snapshot.variation_count,
                            "current_variation_count": current_snapshot.variation_count,
                        },
                    )
                )

            if (
                previous_snapshot.availability_status
                != current_snapshot.availability_status
            ):
                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.AVAILABILITY_CHANGED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_availability_status": previous_snapshot.availability_status,
                            "current_availability_status": current_snapshot.availability_status,
                        },
                    )
                )

            if (
                previous_snapshot.buy_box_status != current_snapshot.buy_box_status
                or previous_snapshot.buy_box_seller_name
                != current_snapshot.buy_box_seller_name
            ):
                candidates.append(
                    DiffCandidate(
                        tracker_type=tracker_type,
                        tracker_code=tracker_code,
                        marketplace=current_snapshot.marketplace,
                        asin=current_snapshot.asin,
                        event_type=EventType.BUY_BOX_CHANGED,
                        snapshot_date=snapshot_date,
                        event_time=event_time,
                        metadata={
                            "previous_buy_box_status": previous_snapshot.buy_box_status,
                            "previous_buy_box_seller_name": previous_snapshot.buy_box_seller_name,
                            "current_buy_box_status": current_snapshot.buy_box_status,
                            "current_buy_box_seller_name": current_snapshot.buy_box_seller_name,
                        },
                    )
                )

        return candidates


def _dedupe_category_snapshot_products(products):
    deduped_products = []
    seen_asins: set[str] = set()

    for product in sorted(products, key=lambda item: item.rank_position):
        if product.asin in seen_asins:
            continue
        seen_asins.add(product.asin)
        deduped_products.append(product)

    return deduped_products
