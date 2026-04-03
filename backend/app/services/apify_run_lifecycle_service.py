from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.config.config import ApifyConfig
from app.core.errors import ForbiddenError
from app.core.logging import correlation_context, get_logger
from app.core.utils import utc_now
from app.integrations.apify_gateway import ApifyGateway, ApifyRunLookupError, map_apify_status
from app.models.api import (
    ApifyRunPollResult,
    ApifyWebhookAck,
    ApifyWebhookEnvelope,
    ExternalRunStatus,
    ExternalRunSummary,
    JobError,
    JobStatus,
)
from app.models.documents import ApifyRunDocument, JobDocument
from app.services.run_orchestrator import coerce_datetime

logger = get_logger(__name__)

TERMINAL_EXTERNAL_STATUSES = {
    ExternalRunStatus.SUCCEEDED,
    ExternalRunStatus.FAILED,
    ExternalRunStatus.TIMED_OUT,
    ExternalRunStatus.ABORTED,
}
FAILED_EXTERNAL_STATUSES = {
    ExternalRunStatus.FAILED,
    ExternalRunStatus.TIMED_OUT,
    ExternalRunStatus.ABORTED,
}


@dataclass(frozen=True)
class LifecycleUpdateResult:
    ack_status: Literal["ACCEPTED", "IGNORED"]
    apify_run_id: str | None
    tracking_job_code: str | None
    provider_status: ExternalRunStatus | None
    job_status: JobStatus | None
    run_updated: bool
    job_advanced: bool
    job_failed: bool

    def to_webhook_ack(self) -> ApifyWebhookAck:
        return ApifyWebhookAck(
            status=self.ack_status,
            apify_run_id=self.apify_run_id,
            tracking_job_code=self.tracking_job_code,
            provider_status=self.provider_status,
            job_status=self.job_status,
        )


class ApifyRunLifecycleService:
    def __init__(self, gateway: ApifyGateway, config: ApifyConfig) -> None:
        self.gateway = gateway
        self.config = config

    async def handle_webhook(
        self,
        payload: ApifyWebhookEnvelope,
        authorization_header: str | None = None,
    ) -> ApifyWebhookAck:
        self._verify_webhook_secret(authorization_header)

        provider_run_id = self._extract_run_id(payload)
        provider_status = self._extract_status(payload)
        if provider_run_id is None or provider_status is None:
            logger.info(
                "Ignoring Apify webhook because run identity or status could not be resolved.",
                extra={
                    "context": correlation_context(
                        apify_run_id=provider_run_id,
                        event_type=payload.event_type,
                    )
                },
            )
            return ApifyWebhookAck(status="IGNORED")

        result = await self._sync_run_state(
            provider_run_id=provider_run_id,
            provider_status=provider_status,
            raw_status=self._extract_raw_status(payload),
            default_dataset_id=self._extract_dataset_id(payload),
            started_at=self._extract_started_at(payload),
            finished_at=self._extract_finished_at(payload),
            source="WEBHOOK",
        )
        return result.to_webhook_ack()

    async def poll_runs(self) -> ApifyRunPollResult:
        runs = await ApifyRunDocument.find().to_list()
        candidates = sorted(
            [
                document
                for document in runs
                if document.status not in {status.value for status in TERMINAL_EXTERNAL_STATUSES}
            ],
            key=lambda document: document.updated_at,
        )[: self.config.poll_batch_size]

        updated_runs = 0
        jobs_advanced = 0
        jobs_failed = 0
        lookup_failures = 0
        polled_runs = 0

        for run_document in candidates:
            job_document = await self._find_job_document(run_document)
            if job_document is None:
                logger.warning(
                    "Skipping Apify run polling because the linked job was not found.",
                    extra={
                        "context": correlation_context(
                            apify_run_id=run_document.apify_run_id,
                            tracking_job_code=run_document.tracking_job_code,
                        )
                    },
                )
                continue
            if job_document.status != JobStatus.RUNNING_EXTERNAL:
                logger.info(
                    "Skipping Apify run polling because the job is no longer running externally.",
                    extra={
                        "context": correlation_context(
                            apify_run_id=run_document.apify_run_id,
                            tracking_job_code=run_document.tracking_job_code,
                            job_status=job_document.status,
                        )
                    },
                )
                continue

            polled_runs += 1
            try:
                run_state = await self.gateway.get_run(run_document.apify_run_id)
            except ApifyRunLookupError:
                lookup_failures += 1
                logger.exception(
                    "Failed to poll Apify run state.",
                    extra={
                        "context": correlation_context(
                            apify_run_id=run_document.apify_run_id,
                            tracking_job_code=run_document.tracking_job_code,
                        )
                    },
                )
                continue

            result = await self._sync_run_state(
                provider_run_id=run_document.apify_run_id,
                provider_status=run_state.status,
                raw_status=run_state.raw_status,
                default_dataset_id=run_state.default_dataset_id,
                started_at=run_state.started_at,
                finished_at=run_state.finished_at,
                source="POLL",
                run_document=run_document,
                job_document=job_document,
            )
            if result.run_updated:
                updated_runs += 1
            if result.job_advanced:
                jobs_advanced += 1
            if result.job_failed:
                jobs_failed += 1

        return ApifyRunPollResult(
            polled_runs=polled_runs,
            updated_runs=updated_runs,
            jobs_advanced=jobs_advanced,
            jobs_failed=jobs_failed,
            lookup_failures=lookup_failures,
        )

    async def _sync_run_state(
        self,
        *,
        provider_run_id: str,
        provider_status: ExternalRunStatus | None,
        raw_status: str | None,
        default_dataset_id: str | None,
        started_at: object | None,
        finished_at: object | None,
        source: Literal["WEBHOOK", "POLL"],
        run_document: ApifyRunDocument | None = None,
        job_document: JobDocument | None = None,
    ) -> LifecycleUpdateResult:
        run_document = run_document or await ApifyRunDocument.find_one(
            ApifyRunDocument.apify_run_id == provider_run_id
        )
        if run_document is None:
            logger.info(
                "Ignoring Apify lifecycle update because the run was not found.",
                extra={
                    "context": correlation_context(
                        apify_run_id=provider_run_id,
                        provider_status=provider_status,
                        source=source,
                    )
                },
            )
            return LifecycleUpdateResult(
                ack_status="IGNORED",
                apify_run_id=provider_run_id,
                tracking_job_code=None,
                provider_status=provider_status,
                job_status=None,
                run_updated=False,
                job_advanced=False,
                job_failed=False,
            )

        job_document = job_document or await self._find_job_document(run_document)
        current_time = utc_now()
        run_updated = self._update_run_document(
            run_document,
            provider_status=provider_status,
            raw_status=raw_status,
            default_dataset_id=default_dataset_id,
            started_at=started_at,
            finished_at=finished_at,
            source=source,
            current_time=current_time,
        )
        await run_document.save()

        if job_document is None:
            logger.warning(
                "Apify run update was stored but the linked job could not be found.",
                extra={
                    "context": correlation_context(
                        apify_run_id=provider_run_id,
                        tracking_job_code=run_document.tracking_job_code,
                        source=source,
                    )
                },
            )
            return LifecycleUpdateResult(
                ack_status="IGNORED",
                apify_run_id=provider_run_id,
                tracking_job_code=run_document.tracking_job_code,
                provider_status=provider_status,
                job_status=None,
                run_updated=run_updated,
                job_advanced=False,
                job_failed=False,
            )

        job_transition = self._update_job_document(
            job_document=job_document,
            provider_run_id=provider_run_id,
            provider_status=provider_status,
            started_at=started_at,
            finished_at=finished_at,
            current_time=current_time,
        )
        if job_transition["changed"]:
            await job_document.save()

        logger.info(
            "Processed Apify run lifecycle update.",
            extra={
                "context": correlation_context(
                    apify_run_id=provider_run_id,
                    tracking_job_code=run_document.tracking_job_code,
                    provider_status=provider_status,
                    job_status=job_document.status,
                    source=source,
                    ack_status=job_transition["ack_status"],
                )
            },
        )

        return LifecycleUpdateResult(
            ack_status=job_transition["ack_status"],
            apify_run_id=provider_run_id,
            tracking_job_code=run_document.tracking_job_code,
            provider_status=provider_status,
            job_status=job_document.status,
            run_updated=run_updated,
            job_advanced=job_transition["advanced"],
            job_failed=job_transition["failed"],
        )

    async def _find_job_document(
        self, run_document: ApifyRunDocument
    ) -> JobDocument | None:
        return await JobDocument.find_one(
            JobDocument.workspace_id == run_document.workspace_id,
            JobDocument.job_code == run_document.tracking_job_code,
        )

    def _update_run_document(
        self,
        run_document: ApifyRunDocument,
        *,
        provider_status: ExternalRunStatus | None,
        raw_status: str | None,
        default_dataset_id: str | None,
        started_at: object | None,
        finished_at: object | None,
        source: Literal["WEBHOOK", "POLL"],
        current_time: datetime,
    ) -> bool:
        changed = False
        coerced_started_at = coerce_datetime(started_at)
        coerced_finished_at = coerce_datetime(finished_at)

        if provider_status is not None and run_document.status != provider_status.value:
            run_document.status = provider_status.value
            changed = True
        if raw_status is not None and run_document.apify_status_raw != raw_status:
            run_document.apify_status_raw = raw_status
            changed = True
        if default_dataset_id and run_document.default_dataset_id != default_dataset_id:
            run_document.default_dataset_id = default_dataset_id
            changed = True
        if coerced_started_at and run_document.started_at != coerced_started_at:
            run_document.started_at = coerced_started_at
            changed = True
        if coerced_finished_at and run_document.finished_at != coerced_finished_at:
            run_document.finished_at = coerced_finished_at
            changed = True

        if provider_status in FAILED_EXTERNAL_STATUSES:
            error = JobError(
                code=provider_status.value,
                message=f"Apify run finished with status `{provider_status.value}`.",
            )
            if run_document.error != error:
                run_document.error = error
                changed = True
        elif provider_status == ExternalRunStatus.SUCCEEDED and run_document.error is not None:
            run_document.error = None
            changed = True

        if source == "WEBHOOK":
            if run_document.webhook_received_at != current_time:
                run_document.webhook_received_at = current_time
                changed = True
        else:
            run_document.poll_count += 1
            changed = True

        run_document.updated_at = current_time
        return changed

    def _update_job_document(
        self,
        *,
        job_document: JobDocument,
        provider_run_id: str,
        provider_status: ExternalRunStatus | None,
        started_at: object | None,
        finished_at: object | None,
        current_time: datetime,
    ) -> dict[str, bool | Literal["ACCEPTED", "IGNORED"]]:
        changed = False
        advanced = False
        failed = False
        ack_status: Literal["ACCEPTED", "IGNORED"] = "IGNORED"
        coerced_started_at = coerce_datetime(started_at)
        coerced_finished_at = coerce_datetime(finished_at)

        external_run = job_document.external_run or ExternalRunSummary(
            provider_run_id=provider_run_id
        )
        if external_run.provider_run_id != provider_run_id:
            external_run.provider_run_id = provider_run_id
            changed = True
        if provider_status is not None and external_run.status != provider_status:
            external_run.status = provider_status
            changed = True
        if coerced_started_at and external_run.started_at != coerced_started_at:
            external_run.started_at = coerced_started_at
            changed = True
        if coerced_finished_at and external_run.finished_at != coerced_finished_at:
            external_run.finished_at = coerced_finished_at
            changed = True
        job_document.external_run = external_run

        if job_document.status == JobStatus.RUNNING_EXTERNAL:
            if provider_status == ExternalRunStatus.SUCCEEDED:
                job_document.status = JobStatus.IMPORTING
                job_document.error = None
                changed = True
                advanced = True
                ack_status = "ACCEPTED"
            elif provider_status in FAILED_EXTERNAL_STATUSES:
                job_document.status = JobStatus.FAILED
                job_document.error = JobError(
                    code=provider_status.value,
                    message=f"Apify run finished with status `{provider_status.value}`.",
                )
                job_document.finished_at = coerced_finished_at or current_time
                changed = True
                failed = True
                ack_status = "ACCEPTED"
            elif provider_status is not None:
                changed = True
                ack_status = "ACCEPTED"
        elif changed:
            ack_status = "IGNORED"

        return {
            "changed": changed,
            "advanced": advanced,
            "failed": failed,
            "ack_status": ack_status,
        }

    def _verify_webhook_secret(self, authorization_header: str | None) -> None:
        if not self.config.webhook_secret:
            return

        scheme, _, token = (authorization_header or "").partition(" ")
        if scheme != "Bearer" or not hmac.compare_digest(token, self.config.webhook_secret):
            raise ForbiddenError("Invalid webhook secret.")

    def _extract_run_id(self, payload: ApifyWebhookEnvelope) -> str | None:
        resource = self._as_dict(payload.resource)
        if resource and isinstance(resource.get("id"), str):
            return resource["id"]

        event_data = self._as_dict(payload.event_data)
        if event_data and isinstance(event_data.get("actorRunId"), str):
            return event_data["actorRunId"]

        return payload.resource_id

    def _extract_status(self, payload: ApifyWebhookEnvelope) -> ExternalRunStatus | None:
        resource = self._as_dict(payload.resource)
        if resource:
            status = map_apify_status(resource.get("status"))
            if status is not None:
                return status

        event_type = payload.event_type or ""
        event_type_map = {
            "ACTOR.RUN.SUCCEEDED": ExternalRunStatus.SUCCEEDED,
            "ACTOR.RUN.FAILED": ExternalRunStatus.FAILED,
            "ACTOR.RUN.ABORTED": ExternalRunStatus.ABORTED,
            "ACTOR.RUN.TIMED_OUT": ExternalRunStatus.TIMED_OUT,
        }
        return event_type_map.get(event_type)

    def _extract_raw_status(self, payload: ApifyWebhookEnvelope) -> str | None:
        resource = self._as_dict(payload.resource)
        if resource and isinstance(resource.get("status"), str):
            return resource["status"]
        if payload.event_type == "ACTOR.RUN.TIMED_OUT":
            return "TIMED-OUT"
        if payload.event_type and payload.event_type.startswith("ACTOR.RUN."):
            return payload.event_type.removeprefix("ACTOR.RUN.")
        return None

    def _extract_dataset_id(self, payload: ApifyWebhookEnvelope) -> str | None:
        resource = self._as_dict(payload.resource)
        if resource and isinstance(resource.get("defaultDatasetId"), str):
            return resource["defaultDatasetId"]
        return None

    def _extract_started_at(self, payload: ApifyWebhookEnvelope) -> object | None:
        resource = self._as_dict(payload.resource)
        if resource:
            return resource.get("startedAt")
        return None

    def _extract_finished_at(self, payload: ApifyWebhookEnvelope) -> object | None:
        resource = self._as_dict(payload.resource)
        if resource:
            return resource.get("finishedAt")
        return None

    def _as_dict(self, value: object | None) -> dict[str, object] | None:
        if isinstance(value, dict):
            return value
        return None
