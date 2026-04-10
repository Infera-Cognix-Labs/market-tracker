from __future__ import annotations

from app.core.errors import ConflictError
from app.core.logging import correlation_context, get_logger
from app.models.api import JobCreateRequest, TrackerType, TriggerMode
from app.store import BaseStore

logger = get_logger(__name__)


async def create_and_dispatch_initial_job(
    *,
    store: BaseStore,
    workspace_id: str,
    tracker_type: TrackerType,
    tracker_code: str,
) -> None:
    try:
        job = await store.create_job(
            workspace_id,
            JobCreateRequest(
                tracker_type=tracker_type,
                tracker_code=tracker_code,
                trigger_mode=TriggerMode.MANUAL,
            ),
        )
    except ConflictError:
        logger.info(
            "Skipping initial tracker fetch because a job already exists.",
            extra={
                "context": correlation_context(
                    workspace_id=workspace_id,
                    tracker_type=tracker_type,
                    tracker_code=tracker_code,
                )
            },
        )
        return

    await store.dispatch_job(workspace_id, job.job_code)

    logger.info(
        "Created and dispatched initial tracker fetch.",
        extra={
            "context": correlation_context(
                workspace_id=workspace_id,
                tracker_type=tracker_type,
                tracker_code=tracker_code,
                job_code=job.job_code,
            )
        },
    )
