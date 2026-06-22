from __future__ import annotations

from app.integrations.adapters import (
    ActorAdapter,
    HarvestlabKeywordAdapter,
    JungleeAsinsAdapter,
    JungleeBestsellersAdapter,
)

_ADAPTER_REGISTRY: dict[str, ActorAdapter] = {
    "junglee_bestsellers": JungleeBestsellersAdapter(),
    "junglee_asins": JungleeAsinsAdapter(),
    "harvestlab_keyword": HarvestlabKeywordAdapter(),
}


def get_adapter(name: str) -> ActorAdapter:
    adapter = _ADAPTER_REGISTRY.get(name)
    if not adapter:
        raise ValueError(f"Unknown adapter: {name}")
    return adapter
