from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from apify_client import ApifyClient

from app.config.config import ApifyConfig
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


class ApifyGateway:
    def __init__(self, config: ApifyConfig) -> None:
        self.config = config

    def resolve_binding(self, binding_code: str) -> ApifyBindingTarget:
        if binding_code == "bind_category_top50_v1":
            return ApifyBindingTarget(
                binding_code=binding_code,
                actor_name=self.config.category_actor_name,
                actor_id=self.config.category_actor_id,
                task_id=self.config.category_task_id,
                build=self.config.category_build,
                memory_mbytes=self.config.category_memory_mbytes,
            )
        if binding_code == "bind_competitor_tracking_v1":
            return ApifyBindingTarget(
                binding_code=binding_code,
                actor_name=self.config.competitor_actor_name,
                actor_id=self.config.competitor_actor_id,
                task_id=self.config.competitor_task_id,
                build=self.config.competitor_build,
                memory_mbytes=self.config.competitor_memory_mbytes,
            )
        if binding_code == "bind_deals_v1":
            return ApifyBindingTarget(
                binding_code=binding_code,
                actor_name=self.config.deals_actor_name,
                actor_id=self.config.deals_actor_id,
                task_id=self.config.deals_task_id,
                build=self.config.deals_build,
                memory_mbytes=self.config.deals_memory_mbytes,
            )
        raise ApifyBindingResolutionError(
            f"Unsupported Apify binding_code `{binding_code}`."
        )

    async def start_run(
        self,
        binding_code: str,
        run_input: dict[str, object],
        *,
        webhooks: list[dict[str, object]] | None = None,
    ) -> ApifyRunLaunch:
        if not self.config.token:
            raise ApifyBindingResolutionError("Missing APIFY_TOKEN for Apify dispatch.")

        binding = self.resolve_binding(binding_code)
        if not binding.actor_id and not binding.task_id:
            raise ApifyBindingResolutionError(
                f"Missing actor/task configuration for binding `{binding_code}`."
            )

        input_hash = hashlib.sha256(
            json.dumps(run_input, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        try:
            run = await asyncio.to_thread(
                self._start_run_sync, binding, run_input, webhooks
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
            run_input=run_input,
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
        if binding.task_id:
            task_kwargs: dict[str, object] = {
                "task_input": run_input,
                "timeout_secs": self.config.dispatch_timeout_secs,
            }
            if webhooks is not None:
                task_kwargs["webhooks"] = webhooks
            if binding.memory_mbytes is not None:
                task_kwargs["memory_mbytes"] = binding.memory_mbytes
            if binding.build is not None:
                task_kwargs["build"] = binding.build
            return client.task(binding.task_id).call(**task_kwargs)
        if binding.actor_id:
            actor_kwargs: dict[str, object] = {
                "run_input": run_input,
                "timeout_secs": self.config.dispatch_timeout_secs,
            }
            if webhooks is not None:
                actor_kwargs["webhooks"] = webhooks
            if binding.memory_mbytes is not None:
                actor_kwargs["memory_mbytes"] = binding.memory_mbytes
            if binding.build is not None:
                actor_kwargs["build"] = binding.build
            return client.actor(binding.actor_id).call(**actor_kwargs)
        raise ApifyBindingResolutionError(
            f"Missing actor/task configuration for binding `{binding.binding_code}`."
        )

    def _get_run_sync(self, run_id: str) -> dict[str, object] | None:
        client = ApifyClient(self.config.token)
        return client.run(run_id).get()

    def _list_dataset_items_sync(
        self,
        dataset_id: str,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        client = ApifyClient(self.config.token)
        response = client.dataset(dataset_id).list_items(limit=limit, offset=offset)
        return {
            "count": response.count,
            "total": response.total,
            "items": list(response.items),
        }


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
