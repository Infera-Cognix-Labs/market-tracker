from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from apify_client import ApifyClient

from app.config.config import ApifyConfig, InputAdapterConfig
from app.models.api import ExternalRunStatus


class ApifyGatewayError(Exception):
    pass


class ApifyBindingResolutionError(ApifyGatewayError):
    pass


class ApifyRunStartError(ApifyGatewayError):
    pass


class ApifyRunLookupError(ApifyGatewayError):
    pass


class ApifyDatasetLookupError(ApifyGatewayError):
    pass


@dataclass(frozen=True)
class ActorPoolEntry:
    index: int
    actor_id: str | None
    task_id: str | None
    name: str | None
    build: str | None
    memory_mbytes: int | None
    adapter_name: str | None
    input_adapter: InputAdapterConfig | None


@dataclass(frozen=True)
class ApifyBindingTarget:
    binding_code: str
    actor_name: str | None
    actor_id: str | None
    task_id: str | None
    build: str | None
    memory_mbytes: int | None


@dataclass(frozen=True)
class ApifyRunLaunch:
    provider_run_id: str
    default_dataset_id: str | None
    status: ExternalRunStatus | None
    raw_status: str | None
    started_at: Any
    finished_at: Any
    input_hash: str
    binding: ApifyBindingTarget
    run_input: dict[str, object]
    pool_actor_id: str | None = None
    pool_actor_name: str | None = None
    pool_index: int | None = None


@dataclass(frozen=True)
class ApifyRunState:
    provider_run_id: str
    default_dataset_id: str | None
    status: ExternalRunStatus | None
    raw_status: str | None
    started_at: Any
    finished_at: Any


@dataclass(frozen=True)
class ApifyDatasetBatch:
    dataset_id: str
    offset: int
    limit: int
    count: int
    total: int | None
    items: list[dict[str, object]]


def _normalize_run(run: dict[str, object] | object | None) -> dict[str, object] | None:
    """Normalize an Apify run response to a dict with consistent camelCase keys.

    apify-client 2.x returns plain dicts; 3.x returns Pydantic models with
    snake_case attributes. This helper extracts the fields our codebase needs
    into a plain dict so callers can keep using ``run["id"]`` and
    ``run.get("defaultDatasetId")``.
    """
    if run is None:
        return None
    if isinstance(run, dict):
        return run
    return {
        "id": getattr(run, "id", None),
        "defaultDatasetId": getattr(run, "default_dataset_id", None),
        "status": getattr(run, "status", None),
        "startedAt": getattr(run, "started_at", None),
        "finishedAt": getattr(run, "finished_at", None),
    }


def _normalize_dataset_response(
    response: dict[str, object] | object,
) -> dict[str, object]:
    """Normalize a dataset list_items response to a dict.

    apify-client 2.x returns a dict; 3.x returns a ``DatasetItemsPage``
    Pydantic model. This extracts ``items``, ``count``, and ``total`` into a
    plain dict.
    """
    if isinstance(response, dict):
        return response
    return {
        "items": list(getattr(response, "items", []) or []),
        "count": getattr(response, "count", None),
        "total": getattr(response, "total", None),
    }


class ApifyGateway:
    def __init__(self, config: ApifyConfig) -> None:
        self.config = config

    def resolve_pool(self, pool_code: str) -> list[ActorPoolEntry]:
        pools = self.config.actor_pools
        entries_config = pools.get(pool_code)
        if not entries_config:
            raise ApifyBindingResolutionError(
                f"Unknown actor pool `{pool_code}`."
            )
        result: list[ActorPoolEntry] = []
        for idx, entry in enumerate(entries_config):
            if not entry.enabled:
                continue
            result.append(
                ActorPoolEntry(
                    index=idx,
                    actor_id=entry.actor_id,
                    task_id=entry.task_id,
                    name=entry.name,
                    build=entry.build,
                    memory_mbytes=entry.memory_mbytes,
                    adapter_name=entry.adapter,
                    input_adapter=entry.input_adapter,
                )
            )
        return result

    def _apply_adapter(
        self, entry: ActorPoolEntry, run_input: dict[str, object]
    ) -> dict[str, object]:
        if not entry.input_adapter:
            return dict(run_input)
        adapted = dict(run_input)

        for source_key, target_key in entry.input_adapter.field_map.items():
            if source_key in adapted:
                adapted[target_key] = adapted.pop(source_key)

        for field in entry.input_adapter.wrap_array:
            if field in adapted and not isinstance(adapted[field], list):
                adapted[field] = [adapted[field]]

        for field, url_key in entry.input_adapter.wrap_object.items():
            if field in adapted and isinstance(adapted[field], str):
                adapted[field] = [{url_key: adapted[field]}]

        if entry.input_adapter.asin_to_url:
            target_field = entry.input_adapter.asin_to_url
            if target_field in adapted:
                asins = adapted[target_field]
                if isinstance(asins, list):
                    amazon_domain = adapted.get("amazon_domain", "www.amazon.com")
                    adapted[target_field] = [
                        f"https://{amazon_domain}/dp/{asin}" for asin in asins
                    ]

        for key, value in entry.input_adapter.static_fields.items():
            adapted[key] = value

        if entry.input_adapter.marketplace_map and "marketplace" in adapted:
            marketplace = adapted["marketplace"]
            if marketplace in entry.input_adapter.marketplace_map:
                adapted["marketplace"] = entry.input_adapter.marketplace_map[marketplace]

        return adapted

    @staticmethod
    def _parse_pool_code(pool_code: str) -> tuple[str, int]:
        if ":" in pool_code:
            pool, index_str = pool_code.rsplit(":", 1)
            try:
                return pool, int(index_str)
            except ValueError:
                pass
        return pool_code, 0

    async def start_run(
        self,
        pool_code: str,
        run_input: dict[str, object],
        *,
        webhooks: list[dict[str, object]] | None = None,
    ) -> ApifyRunLaunch:
        if not self.config.token:
            raise ApifyBindingResolutionError("Missing APIFY_TOKEN for Apify dispatch.")

        pool, idx = self._parse_pool_code(pool_code)
        entries = self.resolve_pool(pool)
        if idx >= len(entries):
            raise ApifyBindingResolutionError(
                f"Pool index {idx} out of range for pool `{pool}` "
                f"(size={len(entries)})."
            )
        entry = entries[idx]
        adapted_input = self._apply_adapter(entry, run_input)
        binding = ApifyBindingTarget(
            binding_code=pool_code,
            actor_name=entry.name,
            actor_id=entry.actor_id,
            task_id=entry.task_id,
            build=entry.build,
            memory_mbytes=entry.memory_mbytes,
        )
        if not binding.actor_id and not binding.task_id:
            raise ApifyBindingResolutionError(
                f"Missing actor/task configuration for pool entry `{pool}:{idx}`."
            )

        input_hash = hashlib.sha256(
            json.dumps(adapted_input, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        try:
            run = await asyncio.to_thread(
                self._start_run_sync, binding, adapted_input, webhooks
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via monkeypatch in unit tests
            raise ApifyRunStartError(str(exc)) from exc

        return ApifyRunLaunch(
            provider_run_id=run["id"],
            default_dataset_id=run.get("defaultDatasetId"),
            status=map_apify_status(run.get("status")),
            raw_status=run.get("status"),
            started_at=run.get("startedAt"),
            finished_at=run.get("finishedAt"),
            input_hash=input_hash,
            binding=binding,
            run_input=adapted_input,
            pool_actor_id=entry.actor_id,
            pool_actor_name=entry.name,
            pool_index=idx,
        )

    async def get_run(self, run_id: str) -> ApifyRunState:
        if not self.config.token:
            raise ApifyRunLookupError("Missing APIFY_TOKEN for Apify run lookup.")

        try:
            run = await asyncio.to_thread(self._get_run_sync, run_id)
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via monkeypatch in unit tests
            raise ApifyRunLookupError(str(exc)) from exc

        if run is None:
            raise ApifyRunLookupError(f"Apify run `{run_id}` was not found.")

        return ApifyRunState(
            provider_run_id=run["id"],
            default_dataset_id=run.get("defaultDatasetId"),
            status=map_apify_status(run.get("status")),
            raw_status=run.get("status"),
            started_at=run.get("startedAt"),
            finished_at=run.get("finishedAt"),
        )

    async def list_dataset_items(
        self,
        dataset_id: str,
        *,
        limit: int,
        offset: int = 0,
    ) -> ApifyDatasetBatch:
        if not self.config.token:
            raise ApifyDatasetLookupError("Missing APIFY_TOKEN for dataset lookup.")

        try:
            response = await asyncio.to_thread(
                self._list_dataset_items_sync,
                dataset_id,
                limit,
                offset,
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised via monkeypatch in unit tests
            raise ApifyDatasetLookupError(str(exc)) from exc

        items = [item for item in response.get("items", []) if isinstance(item, dict)]
        count = response.get("count")
        total = response.get("total")
        return ApifyDatasetBatch(
            dataset_id=dataset_id,
            offset=offset,
            limit=limit,
            count=count if isinstance(count, int) else len(items),
            total=total if isinstance(total, int) else None,
            items=items,
        )

    def _start_run_sync(
        self,
        binding: ApifyBindingTarget,
        run_input: dict[str, object],
        webhooks: list[dict[str, object]] | None,
    ) -> dict[str, object]:
        client = ApifyClient(self.config.token)
        raw: dict[str, object] | object | None = None
        if binding.task_id:
            task_kwargs: dict[str, object] = {
                "task_input": run_input,
            }
            if webhooks is not None:
                task_kwargs["webhooks"] = webhooks
            if binding.memory_mbytes is not None:
                task_kwargs["memory_mbytes"] = binding.memory_mbytes
            if binding.build is not None:
                task_kwargs["build"] = binding.build
            raw = client.task(binding.task_id).call(**task_kwargs)
        elif binding.actor_id:
            actor_kwargs: dict[str, object] = {
                "run_input": run_input,
            }
            if webhooks is not None:
                actor_kwargs["webhooks"] = webhooks
            if binding.memory_mbytes is not None:
                actor_kwargs["memory_mbytes"] = binding.memory_mbytes
            if binding.build is not None:
                actor_kwargs["build"] = binding.build
            raw = client.actor(binding.actor_id).call(**actor_kwargs)
        else:
            raise ApifyBindingResolutionError(
                f"Missing actor/task configuration for `{binding.binding_code}`."
            )
        normalized = _normalize_run(raw)
        if normalized is None:
            raise ApifyRunStartError(
                "Apify call() returned None — the run may have failed to start."
            )
        return normalized

    def _get_run_sync(self, run_id: str) -> dict[str, object] | None:
        client = ApifyClient(self.config.token)
        return _normalize_run(client.run(run_id).get())

    def _list_dataset_items_sync(
        self,
        dataset_id: str,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        client = ApifyClient(self.config.token)
        response = client.dataset(dataset_id).list_items(limit=limit, offset=offset)
        return _normalize_dataset_response(response)


def map_apify_status(raw_status: str | None) -> ExternalRunStatus | None:
    if raw_status is None:
        return None
    normalized = raw_status.upper()
    if normalized in {
        "READY",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "TIMED-OUT",
        "TIMED_OUT",
        "ABORTED",
    }:
        if normalized == "TIMED-OUT":
            normalized = "TIMED_OUT"
        return ExternalRunStatus(normalized)
    return None
