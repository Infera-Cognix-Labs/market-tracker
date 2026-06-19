from __future__ import annotations

from app.integrations.adapters import (
    ActorAdapter,
    DealsScraperAdapter,
    HarvestlabKeywordAdapter,
    JungleeAsinsAdapter,
    JungleeBestsellersAdapter,
    SaswaveCompetitorAdapter,
)

_ADAPTER_REGISTRY: dict[str, ActorAdapter] = {
    "junglee_bestsellers": JungleeBestsellersAdapter(),
    "junglee_asins": JungleeAsinsAdapter(),
    "harvestlab_keyword": HarvestlabKeywordAdapter(),
    "saswave_competitor": SaswaveCompetitorAdapter(),
    "deals_scraper": DealsScraperAdapter(),
}


def get_adapter(name: str) -> ActorAdapter:
    adapter = _ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise ValueError(f"Unknown adapter: {name}")
    return adapter
