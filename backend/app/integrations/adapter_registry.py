from __future__ import annotations

from app.integrations.adapters import (
    ActorAdapter,
    DealsScraperAdapter,
    HarvestlabKeywordAdapter,
    JungleeAsinsAdapter,
    JungleeBestsellersAdapter,
    ProdigerCategoryAdapter,
    SaswaveCategoryAdapter,
)

_ADAPTER_REGISTRY: dict[str, ActorAdapter] = {
    "saswave_category": SaswaveCategoryAdapter(),
    "prodiger_category": ProdigerCategoryAdapter(),
    "harvestlab_keyword": HarvestlabKeywordAdapter(),
    "junglee_bestsellers": JungleeBestsellersAdapter(),
    "junglee_asins": JungleeAsinsAdapter(),
    "deals_scraper": DealsScraperAdapter(),
}


def get_adapter(name: str) -> ActorAdapter:
    adapter = _ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise ValueError(f"Unknown adapter: {name}")
    return adapter
