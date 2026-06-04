from __future__ import annotations

from app.integrations.adapters import (
    ActorAdapter,
    CrawlerBrosCategoryAdapter,
    DealsScraperAdapter,
    JungleeAsinsAdapter,
    JungleeCategoryAdapter,
    JungleeProductAdapter,
    SaswaveCategoryAdapter,
    SaswaveCompetitorAdapter,
)

_ADAPTER_REGISTRY: dict[str, ActorAdapter] = {
    "saswave_category": SaswaveCategoryAdapter(),
    "junglee_category": JungleeCategoryAdapter(),
    "junglee_product": JungleeProductAdapter(),
    "junglee_asins": JungleeAsinsAdapter(),
    "saswave_competitor": SaswaveCompetitorAdapter(),
    "deals_scraper": DealsScraperAdapter(),
    "crawlerbros_category": CrawlerBrosCategoryAdapter(),
}


def get_adapter(name: str) -> ActorAdapter:
    adapter = _ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise ValueError(f"Unknown adapter: {name}")
    return adapter
