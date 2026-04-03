from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

from app.core.utils import utc_now
from app.models.api import AvailabilityStatus, BuyBoxStatus, TrackerType
from app.services.run_orchestrator import coerce_datetime

_ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10,12}$")
_NUMERIC_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class RawImportedItem:
    batch_no: int
    item_index: int
    payload: dict[str, object]


@dataclass(frozen=True)
class NormalizedProductRecord:
    marketplace: str
    asin: str
    rank_position: int | None
    captured_at: datetime
    brand: str
    title: str
    product_url: str
    main_image_url: str
    title_hash: str
    main_image_hash: str
    bsr_position: int | None
    price_current: float | None
    price_original: float | None
    currency: str | None
    coupon_text: str | None
    availability_status: AvailabilityStatus
    buy_box_status: BuyBoxStatus
    buy_box_seller_name: str | None
    rating_value: float | None
    review_count: int | None
    variation_count: int | None
    source_batch_no: int
    source_item_index: int


@dataclass(frozen=True)
class NormalizationResult:
    records: list[NormalizedProductRecord]
    invalid_count: int


class NormalizationService:
    def normalize_items(
        self,
        *,
        tracker_type: TrackerType,
        marketplace: str,
        raw_items: list[RawImportedItem],
    ) -> NormalizationResult:
        records: list[NormalizedProductRecord] = []
        invalid_count = 0

        for position, item in enumerate(raw_items, start=1):
            record = self._normalize_item(
                payload=item.payload,
                marketplace=marketplace,
                fallback_rank=position
                if tracker_type == TrackerType.CATEGORY
                else None,
                batch_no=item.batch_no,
                item_index=item.item_index,
            )
            if record is None:
                invalid_count += 1
                continue
            records.append(record)

        return NormalizationResult(records=records, invalid_count=invalid_count)

    def _normalize_item(
        self,
        *,
        payload: dict[str, object],
        marketplace: str,
        fallback_rank: int | None,
        batch_no: int,
        item_index: int,
    ) -> NormalizedProductRecord | None:
        asin = _coerce_asin(
            _pick(payload, "asin", "ASIN", "productAsin", "product_asin")
        )
        if asin is None:
            return None

        title = _coerce_string(_pick(payload, "title", "name")) or asin
        brand = (
            _coerce_string(
                _pick(
                    payload,
                    "brand",
                    "manufacturer",
                    "store",
                )
            )
            or "Unknown"
        )

        product_url = (
            _coerce_string(
                _pick(payload, "url", "product_url", "productUrl", "productLink")
            )
            or f"https://www.amazon.com/dp/{asin}"
        )

        main_image_url = _coerce_image_url(payload)

        rank_position = _coerce_int(
            _pick(payload, "rank_position", "rank", "position", "best_seller_rank")
        )
        if rank_position is None:
            rank_position = _extract_rank_from_payload(payload)
        if rank_position is None:
            rank_position = fallback_rank

        price_current = _coerce_float(
            _pick(
                payload,
                "price_current",
                "price",
                "price_buybox",
                "price_new_fba",
                "price_new",
            )
        )
        price_original = _coerce_float(
            _pick(payload, "price_original", "originalPrice", "list_price")
        )

        currency = _coerce_currency(
            _pick(payload, "currency", "currencyCode", "currency_code")
        )
        coupon_text = _coerce_string(
            _pick(payload, "coupon_text", "coupon", "promotion_text", "promo_text")
        )

        availability_status = _normalize_availability_status(payload)
        buy_box_seller_name = _coerce_string(
            _pick(
                payload,
                "buy_box_seller_name",
                "buyBoxSellerName",
                "seller_name",
                "soldBy",
                "seller",
            )
        )
        buy_box_status = _normalize_buy_box_status(payload, buy_box_seller_name)

        rating_value = _coerce_float(_pick(payload, "rating", "stars", "rating_value"))
        review_count = _coerce_int(
            _pick(payload, "reviewCount", "reviewsCount", "n_reviews", "review_count")
        )

        variation_count = _coerce_int(
            _pick(payload, "variation_count", "variationCount")
        )
        if variation_count is None:
            variation_count = _extract_variation_count(payload)

        captured_at = (
            _coerce_datetime(
                _pick(
                    payload,
                    "scrapedAt",
                    "data_captured_at",
                    "last_updated",
                    "captured_at",
                )
            )
            or utc_now()
        )

        return NormalizedProductRecord(
            marketplace=marketplace,
            asin=asin,
            rank_position=rank_position,
            captured_at=captured_at,
            brand=brand,
            title=title,
            product_url=product_url,
            main_image_url=main_image_url,
            title_hash=_digest(title),
            main_image_hash=_digest(main_image_url),
            bsr_position=rank_position,
            price_current=price_current,
            price_original=price_original,
            currency=currency,
            coupon_text=coupon_text,
            availability_status=availability_status,
            buy_box_status=buy_box_status,
            buy_box_seller_name=buy_box_seller_name,
            rating_value=rating_value,
            review_count=review_count,
            variation_count=variation_count,
            source_batch_no=batch_no,
            source_item_index=item_index,
        )


def _pick(payload: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _coerce_asin(value: object | None) -> str | None:
    text = _coerce_string(value)
    if not text:
        return None
    normalized = text.upper().strip()
    if _ASIN_PATTERN.fullmatch(normalized):
        return normalized
    return None


def _coerce_string(value: object | None) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_float(value: object | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        match = _NUMERIC_PATTERN.search(text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def _coerce_int(value: object | None) -> int | None:
    numeric = _coerce_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _coerce_image_url(payload: dict[str, object]) -> str:
    direct = _coerce_string(_pick(payload, "image", "main_image_url", "image_url"))
    if direct:
        return direct

    images = payload.get("images")
    if isinstance(images, list):
        for item in images:
            image = _coerce_string(item)
            if image:
                return image

    asin = _coerce_asin(_pick(payload, "asin", "ASIN"))
    if asin:
        return f"https://www.amazon.com/dp/{asin}"
    return "https://www.amazon.com"


def _normalize_availability_status(payload: dict[str, object]) -> AvailabilityStatus:
    in_stock = _pick(payload, "inStock", "in_stock", "availability")
    if isinstance(in_stock, bool):
        return (
            AvailabilityStatus.IN_STOCK if in_stock else AvailabilityStatus.OUT_OF_STOCK
        )

    status_text = _coerce_string(
        _pick(payload, "availability_status", "availability_text", "availabilityStatus")
    )
    if not status_text:
        return AvailabilityStatus.UNKNOWN

    normalized = status_text.lower()
    if "out of stock" in normalized or "unavailable" in normalized:
        return AvailabilityStatus.OUT_OF_STOCK
    if "in stock" in normalized or "available" in normalized:
        return AvailabilityStatus.IN_STOCK
    return AvailabilityStatus.UNKNOWN


def _normalize_buy_box_status(
    payload: dict[str, object],
    buy_box_seller_name: str | None,
) -> BuyBoxStatus:
    raw_status = _coerce_string(_pick(payload, "buy_box_status", "buyBoxStatus"))
    if raw_status:
        normalized = raw_status.upper()
        if normalized in BuyBoxStatus._value2member_map_:
            return BuyBoxStatus(normalized)

    has_buy_box = _pick(payload, "has_buy_box", "hasBuyBox")
    if isinstance(has_buy_box, bool):
        return BuyBoxStatus.HAS_BUY_BOX if has_buy_box else BuyBoxStatus.NO_BUY_BOX

    if buy_box_seller_name:
        return BuyBoxStatus.HAS_BUY_BOX
    return BuyBoxStatus.UNKNOWN


def _coerce_currency(value: object | None) -> str | None:
    text = _coerce_string(value)
    if not text:
        return None
    if len(text) <= 4:
        return text.upper()
    return text


def _extract_rank_from_payload(payload: dict[str, object]) -> int | None:
    for key in ("bestsellerRanks", "bestSellerRank"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict):
                    rank = _coerce_int(item.get("rank"))
                    if rank is not None:
                        return rank
                    rank = _coerce_int(item.get("position"))
                    if rank is not None:
                        return rank
        elif isinstance(candidate, dict):
            rank = _coerce_int(candidate.get("rank"))
            if rank is not None:
                return rank
    return None


def _extract_variation_count(payload: dict[str, object]) -> int | None:
    variant_asins = _coerce_string(_pick(payload, "variantAsins", "variant_asins"))
    if not variant_asins:
        return None
    return len([value for value in variant_asins.split(",") if value.strip()])


def _coerce_datetime(value: object | None) -> datetime | None:
    try:
        return coerce_datetime(value)
    except ValueError:
        return None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
