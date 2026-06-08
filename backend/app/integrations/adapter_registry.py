from __future__ import annotations

from app.integrations.adapters import (
    ActorAdapter,
    DealsScraperAdapter,
    HarvestlabKeywordAdapter,
    JungleeAsinsAdapter,
    ProdigerCategoryAdapter,
    SaswaveCategoryAdapter,
    SaswaveCompetitorAdapter,
)

_ADAPTER_REGISTRY: dict[str, ActorAdapter] = {
    "saswave_category": SaswaveCategoryAdapter(),
    "prodiger_category": ProdigerCategoryAdapter(),
    "harvestlab_keyword": HarvestlabKeywordAdapter(),
    "junglee_asins": JungleeAsinsAdapter(),
    "saswave_competitor": SaswaveCompetitorAdapter(),
    "deals_scraper": DealsScraperAdapter(),
}


def get_adapter(name: str) -> ActorAdapter:
    adapter = _ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise ValueError(f"Unknown adapter: {name}")
    return adapter
