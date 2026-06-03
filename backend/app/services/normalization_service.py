from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

from app.core.utils import utc_now
from app.models.api import (
    AvailabilityStatus,
    BuyBoxStatus,
    DealInfo,
    TrackerType,
)
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
    deal_info: DealInfo | None
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
                "deal_price",
            )
        )
        if price_current is None:
            nested_deal_price = _pick(payload, "deal_price")
            if isinstance(nested_deal_price, dict):
                price_current = _coerce_float(nested_deal_price.get("amount"))

        price_original = _coerce_float(
            _pick(payload, "price_original", "originalPrice", "list_price", "list_price")
        )
        if price_original is None:
            nested_list_price = _pick(payload, "list_price")
            if isinstance(nested_list_price, dict):
                price_original = _coerce_float(nested_list_price.get("amount"))

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

        deal_info = _extract_deal_info(payload, captured_at)

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
            deal_info=deal_info,
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


def _extract_deal_info(payload: dict[str, object], captured_at: datetime) -> DealInfo | None:
    deal_id = _coerce_string(_pick(payload, "deal_id"))
    deal_type = _coerce_string(_pick(payload, "deal_type"))
    deal_state = _coerce_string(_pick(payload, "deal_state"))
    deal_badge = _coerce_string(_pick(payload, "deal_badge"))

    deal_price_obj = _pick(payload, "deal_price")
    deal_price: float | None = None
    currency: str | None = None
    if isinstance(deal_price_obj, dict):
        deal_price = _coerce_float(deal_price_obj.get("amount"))
        currency = _coerce_string(deal_price_obj.get("currency"))

    list_price_obj = _pick(payload, "list_price")
    list_price: float | None = None
    if isinstance(list_price_obj, dict):
        list_price = _coerce_float(list_price_obj.get("amount"))
        if currency is None:
            currency = _coerce_string(list_price_obj.get("currency"))

    savings_amount: float | None = None
    savings_amount_obj = _pick(payload, "savings_amount")
    if isinstance(savings_amount_obj, dict):
        savings_amount = _coerce_float(savings_amount_obj.get("amount"))

    savings_percentage = _coerce_int(_pick(payload, "savings_percentage"))

    deal_starts_at = _coerce_datetime(_pick(payload, "deal_starts_at"))
    deal_ends_at = _coerce_datetime(_pick(payload, "deal_ends_at"))

    if deal_id or deal_type or deal_state or deal_price:
        return DealInfo(
            deal_id=deal_id,
            deal_type=deal_type,
            deal_state=deal_state,
            deal_price=deal_price,
            list_price=list_price,
            savings_percentage=savings_percentage,
            savings_amount=savings_amount,
            currency=currency,
            deal_starts_at=deal_starts_at,
            deal_ends_at=deal_ends_at,
            deal_badge=deal_badge,
            captured_at=captured_at,
        )
    return None


def _coerce_datetime(value: object | None) -> datetime | None:
    try:
        return coerce_datetime(value)
    except ValueError:
        return None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_junglee_item(
    payload: dict[str, object],
    marketplace: str,
) -> NormalizedProductRecord | None:
    asin = _coerce_asin(_pick(payload, "asin", "originalAsin"))
    if asin is None:
        return None

    title = _coerce_string(_pick(payload, "title")) or asin
    brand = _coerce_string(_pick(payload, "brand")) or "Unknown"
    product_url = (
        _coerce_string(_pick(payload, "url"))
        or f"https://www.amazon.com/dp/{asin}"
    )
    main_image_url = _pick_junglee_image_url(payload)

    price_current = _extract_nested_price(payload, "price")
    price_original = _extract_nested_price(payload, "listPrice")
    currency = _coerce_currency(
        _pick_nested(payload, "price", "currency")
        or _pick_nested(payload, "listPrice", "currency")
    )

    rating_value = _coerce_float(_pick(payload, "stars", "rating", "rating_value"))
    review_count = _coerce_int(
        _pick(payload, "reviewsCount", "review_count", "n_reviews")
    )

    bsr_position = _extract_rank_from_payload(payload)

    availability_status = _normalize_availability_status(payload)

    buy_box_seller_name = _coerce_string(
        _pick_nested(payload, "seller", "name")
        or _pick(payload, "seller_name", "soldBy", "buy_box_seller_name")
    )
    buy_box_status = _normalize_buy_box_status(payload, buy_box_seller_name)

    variation_count = _coerce_int(
        _pick(payload, "variation_count", "variationCount")
    )
    if variation_count is None:
        variation_count = _extract_variation_count(payload)

    captured_at = (
        _coerce_datetime(_pick(payload, "scrapedAt", "captured_at")) or utc_now()
    )
    deal_info = _extract_deal_info(payload, captured_at)

    return NormalizedProductRecord(
        marketplace=marketplace,
        asin=asin,
        rank_position=bsr_position,
        captured_at=captured_at,
        brand=brand,
        title=title,
        product_url=product_url,
        main_image_url=main_image_url,
        title_hash=_digest(title),
        main_image_hash=_digest(main_image_url),
        bsr_position=bsr_position,
        price_current=price_current,
        price_original=price_original,
        currency=currency,
        coupon_text=_coerce_string(_pick(payload, "coupon_text", "coupon")),
        availability_status=availability_status,
        buy_box_status=buy_box_status,
        buy_box_seller_name=buy_box_seller_name,
        rating_value=rating_value,
        review_count=review_count,
        variation_count=variation_count,
        deal_info=deal_info,
        source_batch_no=0,
        source_item_index=0,
    )


def _extract_nested_price(payload: dict, key: str) -> float | None:
    nested = payload.get(key)
    if isinstance(nested, dict):
        return _coerce_float(nested.get("value"))
    return _coerce_float(payload.get(key))


def _pick_nested(payload: dict, outer_key: str, inner_key: str) -> object | None:
    outer = payload.get(outer_key)
    if isinstance(outer, dict):
        return outer.get(inner_key)
    return None


def _pick_junglee_image_url(payload: dict) -> str:
    thumbnail = _coerce_string(payload.get("thumbnailImage"))
    if thumbnail:
        return thumbnail
    gallery = payload.get("galleryThumbnails")
    if isinstance(gallery, list) and gallery:
        for item in gallery:
            url = _coerce_string(item)
            if url:
                return url
    hires = payload.get("highResolutionImages")
    if isinstance(hires, list) and hires:
        for item in hires:
            url = _coerce_string(item)
            if url:
                return url
    asin = _coerce_asin(_pick(payload, "asin"))
    if asin:
        return f"https://www.amazon.com/dp/{asin}"
    return "https://www.amazon.com"
