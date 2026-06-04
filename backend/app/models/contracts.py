from __future__ import annotations

from pydantic import BaseModel

from app.models.api import DealInfo


class CategoryProductRecord(BaseModel):
    asin: str
    rank_position: int | None = None
    title: str | None = None
    brand: str | None = None
    product_url: str | None = None
    main_image_url: str | None = None
    price_current: float | None = None
    price_original: float | None = None
    currency: str | None = None
    coupon_text: str | None = None
    rating_value: float | None = None
    review_count: int | None = None
    variation_count: int | None = None
    availability_status: str | None = None
    buy_box_status: str | None = None
    buy_box_seller_name: str | None = None
    bsr_position: int | None = None
    deal_info: DealInfo | None = None

    def has_null_critical_fields(self) -> bool:
        return (
            self.price_current is None
            or self.rating_value is None
            or self.review_count is None
        )


class CompetitorProductRecord(BaseModel):
    asin: str
    title: str | None = None
    brand: str | None = None
    price_current: float | None = None
    price_original: float | None = None
    currency: str | None = None
    rating_value: float | None = None
    review_count: int | None = None
    availability_status: str | None = None
    buy_box_status: str | None = None
    buy_box_seller_name: str | None = None
    variation_count: int | None = None

    def has_null_critical_fields(self) -> bool:
        return (
            self.price_current is None
            or self.rating_value is None
            or self.review_count is None
        )


class DealRecord(BaseModel):
    asin: str
    deal_info: DealInfo | None = None

    def has_null_critical_fields(self) -> bool:
        return self.deal_info is None
