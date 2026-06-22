from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Protocol

from app.models.contracts import (
    CategoryProductRecord,
    CompetitorProductRecord,
)

_ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10,12}$")
_NUMERIC_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_ISO_DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_IMAGE_EXT_PATTERN = re.compile(
    r"\.(jpe?g|png|gif|webp|bmp|svg|tiff?)(?:\?|$)", re.IGNORECASE
)
_AMAZON_PRODUCT_URL_PATTERN = re.compile(
    r"amazon\.\w+/(?:dp|gp/product|gp/aw/d)/", re.IGNORECASE
)
_AMAZON_IMAGE_HOST = re.compile(
    r"(?:m\.media-amazon\.com|images-na\.ssl-images-amazon\.com|images\.ssl-images-amazon\.com)",
    re.IGNORECASE,
)


def _is_image_url(url: str) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False
    if _IMAGE_EXT_PATTERN.search(url):
        return True
    if _AMAZON_IMAGE_HOST.search(url):
        return True
    if _AMAZON_PRODUCT_URL_PATTERN.search(url):
        return False
    return True


def _pick_image_url(payload: dict[str, object], *keys: str) -> str:
    candidate = _coerce_string(_pick(payload, *keys))
    if candidate and _is_image_url(candidate):
        return candidate
    return ""


def _coerce_asin(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if _ASIN_PATTERN.fullmatch(text):
        return text
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


def _coerce_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    match = _ISO_DATETIME_PATTERN.search(text)
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(0)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _pick(payload: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _extract_nested_price(payload: dict[str, object], key: str) -> float | None:
    nested = payload.get(key)
    if isinstance(nested, dict):
        return _coerce_float(nested.get("value"))
    return _coerce_float(payload.get(key))


def _pick_nested(
    payload: dict[str, object], outer_key: str, inner_key: str
) -> object | None:
    outer = payload.get(outer_key)
    if isinstance(outer, dict):
        return outer.get(inner_key)
    return None


class ActorAdapter(Protocol):
    actor_id: str

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | CompetitorProductRecord | None: ...


_ASIN_IN_URL_PATTERN = re.compile(r"/dp/([A-Z0-9]{10,12})")


def _extract_asin_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = _ASIN_IN_URL_PATTERN.search(url)
    if match:
        return match.group(1)
    return None


class JungleeBestsellersAdapter:
    actor_id = "junglee/amazon-bestsellers"

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | None:
        asin = _coerce_asin(_pick(raw_payload, "asin"))
        if not asin:
            asin = _extract_asin_from_url(_coerce_string(_pick(raw_payload, "url")))
        if not asin:
            return None

        bsr_position = None
        bestseller_ranks = raw_payload.get("bestsellerRanks")
        if isinstance(bestseller_ranks, list) and bestseller_ranks:
            last_rank = bestseller_ranks[-1]
            if isinstance(last_rank, dict):
                bsr_position = _coerce_int(last_rank.get("rank"))

        return CategoryProductRecord(
            asin=asin,
            rank_position=_coerce_int(_pick(raw_payload, "position")),
            title=_coerce_string(_pick(raw_payload, "name")),
            brand=_coerce_string(_pick(raw_payload, "brand")) or "Unknown",
            product_url=_coerce_string(_pick(raw_payload, "url")),
            main_image_url=_pick_image_url(raw_payload, "thumbnailUrl", "thumbnail"),
            price_current=_coerce_float(_pick(raw_payload, "price")),
            price_original=None,
            currency=_coerce_string(_pick(raw_payload, "currency")),
            coupon_text=None,
            rating_value=_coerce_float(_pick(raw_payload, "stars", "rating")),
            review_count=_coerce_int(_pick(raw_payload, "reviewsCount")),
            variation_count=None,
            availability_status=None,
            buy_box_status=None,
            buy_box_seller_name=None,
            bsr_position=bsr_position,
        )


class SaswaveCategoryAdapter:
    actor_id = "saswave/amazon-product-scraper"

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | None:
        asin = _coerce_asin(_pick(raw_payload, "asin", "ASIN", "productAsin"))
        if not asin:
            return None
        return CategoryProductRecord(
            asin=asin,
            rank_position=_coerce_int(
                _pick(raw_payload, "rank_position", "rank", "position")
            ),
            title=_coerce_string(_pick(raw_payload, "title", "name")),
            brand=_coerce_string(_pick(raw_payload, "brand", "manufacturer"))
            or "Unknown",
            product_url=_coerce_string(
                _pick(raw_payload, "url", "product_url", "productUrl")
            ),
            main_image_url=_pick_image_url(
                raw_payload, "image", "main_image_url", "image_url"
            ),
            price_current=_coerce_float(
                _pick(raw_payload, "price", "price_current", "deal_price")
            ),
            price_original=_coerce_float(
                _pick(raw_payload, "price_original", "originalPrice", "list_price")
            ),
            currency=_coerce_string(_pick(raw_payload, "currency", "currencyCode")),
            coupon_text=_coerce_string(
                _pick(raw_payload, "coupon_text", "coupon", "promotion_text")
            ),
            rating_value=_coerce_float(
                _pick(raw_payload, "rating", "stars", "rating_value")
            ),
            review_count=_coerce_int(
                _pick(raw_payload, "reviewCount", "reviewsCount", "review_count")
            ),
            variation_count=_coerce_int(
                _pick(raw_payload, "variation_count", "variationCount")
            ),
            availability_status=_coerce_string(
                _pick(raw_payload, "availability_status", "availability")
            ),
            buy_box_status=_coerce_string(
                _pick(raw_payload, "buy_box_status", "buyBoxStatus")
            ),
            buy_box_seller_name=_coerce_string(
                _pick(
                    raw_payload,
                    "buy_box_seller_name",
                    "buyBoxSellerName",
                    "seller_name",
                )
            ),
            bsr_position=_coerce_int(
                _pick(raw_payload, "best_seller_rank", "bsr_position")
            ),
        )


class ProdigerCategoryAdapter:
    actor_id = "prodiger/amazon-product-scraper"

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | None:
        asin = _coerce_asin(_pick(raw_payload, "asin"))
        if not asin:
            return None
        return CategoryProductRecord(
            asin=asin,
            rank_position=_coerce_int(
                _pick(raw_payload, "pageNumber", "searchResultPosition")
            ),
            title=_coerce_string(_pick(raw_payload, "title")),
            brand=_coerce_string(_pick(raw_payload, "brand")) or "Unknown",
            product_url=_coerce_string(_pick(raw_payload, "url")),
            main_image_url=_pick_image_url(raw_payload, "thumbnail"),
            price_current=_coerce_float(_pick(raw_payload, "price")),
            price_original=_coerce_float(_pick(raw_payload, "listPriceValue")),
            currency=_coerce_string(_pick(raw_payload, "currency")),
            rating_value=_coerce_float(_pick(raw_payload, "rating")),
            review_count=_coerce_int(_pick(raw_payload, "reviewCount")),
            availability_status="IN_STOCK"
            if raw_payload.get("isPrime") is True
            else None,
        )


class HarvestlabKeywordAdapter:
    actor_id = "harvestlab/amazon-scraper"

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | None:
        asin = _coerce_asin(_pick(raw_payload, "asin"))
        if not asin:
            return None
        return CategoryProductRecord(
            asin=asin,
            rank_position=_coerce_int(
                _pick(raw_payload, "searchResultPosition", "position")
            ),
            title=_coerce_string(_pick(raw_payload, "title")),
            brand=_coerce_string(_pick(raw_payload, "brand")) or "Unknown",
            product_url=_coerce_string(_pick(raw_payload, "url", "product_url")),
            main_image_url=_pick_image_url(raw_payload, "image_url"),
            price_current=_coerce_float(_pick(raw_payload, "price")),
            price_original=_coerce_float(_pick(raw_payload, "original_price")),
            currency=_coerce_string(_pick(raw_payload, "currency")),
            rating_value=_coerce_float(_pick(raw_payload, "rating")),
            review_count=_coerce_int(_pick(raw_payload, "reviews_count")),
            availability_status=_coerce_string(
                _pick(raw_payload, "availability_status", "availability")
            ),
            bsr_position=_coerce_int(_pick(raw_payload, "bestseller_rank")),
        )


class JungleeAsinsAdapter:
    actor_id = "junglee/amazon-asins-scraper"

    def to_standard_contract(
        self,
        raw_payload: dict[str, object],
        marketplace: str,
    ) -> CategoryProductRecord | None:
        asin = _coerce_asin(_pick(raw_payload, "asin", "originalAsin"))
        if not asin:
            return None
        price_value = _extract_nested_price(raw_payload, "price")
        list_price_value = _extract_nested_price(raw_payload, "listPrice")
        currency = _coerce_string(
            _pick_nested(raw_payload, "price", "currency")
            or _pick_nested(raw_payload, "listPrice", "currency")
        )
        bsr_position = None
        bestseller_ranks = raw_payload.get("bestsellerRanks")
        if isinstance(bestseller_ranks, list) and bestseller_ranks:
            last_rank = bestseller_ranks[-1]
            if isinstance(last_rank, dict):
                bsr_position = _coerce_int(last_rank.get("rank"))

        return CategoryProductRecord(
            asin=asin,
            rank_position=bsr_position,
            title=_coerce_string(_pick(raw_payload, "title")),
            brand=_coerce_string(_pick(raw_payload, "brand")) or "Unknown",
            product_url=_coerce_string(_pick(raw_payload, "url")),
            main_image_url=_pick_image_url(raw_payload, "thumbnailImage"),
            price_current=price_value,
            price_original=list_price_value,
            currency=currency,
            rating_value=_coerce_float(_pick(raw_payload, "stars", "rating")),
            review_count=_coerce_int(_pick(raw_payload, "reviewsCount")),
            availability_status="IN_STOCK"
            if raw_payload.get("inStock") is True
            else "OUT_OF_STOCK"
            if raw_payload.get("inStock") is False
            else None,
            buy_box_seller_name=_coerce_string(
                _pick_nested(raw_payload, "seller", "name")
            ),
            bsr_position=bsr_position,
            variation_count=_coerce_int(_pick(raw_payload, "variation_count")),
        )
