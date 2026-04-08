from __future__ import annotations

from datetime import date
from inspect import isawaitable

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config.config import Config
from app.integrations.apify_gateway import ApifyGateway
from app.models.api import (
    ApifyRunPollResult,
    ApifyWebhookAck,
    ApifyWebhookEnvelope,
    CategorySnapshot,
    CategoryTracker,
    CategoryTrackerCreateRequest,
    CategoryTrackerListResponse,
    CategoryTrackerUpdateRequest,
    CompetitorTrackerCreateRequest,
    CompetitorTrackerDetail,
    CompetitorTrackerListResponse,
    CompetitorTrackerUpdateRequest,
    DashboardOverview,
    DigestWorkerResult,
    EventListResponse,
    EventType,
    ImportWorkerResult,
    Job,
    JobCreateRequest,
    JobListResponse,
    JobStatus,
    ProductDetail,
    ProductTimelineResponse,
    SchedulerWorkerResult,
    Severity,
    Timeframe,
    TrackedAsinReplacementRequest,
    TrackerType,
    WeeklyDigest,
    WeeklyDigestListResponse,
)
from app.models.documents import (
    DOCUMENT_MODELS,
    CategorySnapshotDocument,
    CategoryTrackerDocument,
    CompetitorTrackerDocument,
    EventDocument,
    JobDocument,
    ProductDocument,
    ProductSnapshotDocument,
    WeeklyDigestDocument,
)
from app.seed import SeedData
from app.services.apify_run_lifecycle_service import ApifyRunLifecycleService
from app.services.dashboard_query_service import DashboardQueryService
from app.services.diff_service import DiffService
from app.services.digest_service import DigestService
from app.services.event_engine import EventEngine
from app.services.job_service import JobService
from app.services.normalization_service import NormalizationService
from app.services.object_storage_service import LocalObjectStorageService
from app.services.result_importer_service import ResultImporterService
from app.services.run_orchestrator import RunOrchestrator
from app.services.scheduler_service import SchedulerService
from app.services.shared import (
    aggregate_timeline_points,
    build_dashboard_overview,
    build_timeline_summary,
    build_top_threats,
    generate_job_code,
    generate_tracker_code,
    sort_events,
    within_range,
)
from app.services.snapshot_service import SnapshotService
from app.services.tracker_management_service import TrackerManagementService

LISTING_EVENT_TYPES = {
    EventType.TITLE_CHANGED,
    EventType.MAIN_IMAGE_CHANGED,
    EventType.VARIATIONS_ADDED,
    EventType.CONTENT_CHANGED,
}


# Backward-compatible helper re-exports used by unit tests.
def _aggregate_timeline_points(points, granularity):
    return aggregate_timeline_points(points, granularity)


def _build_dashboard_overview(
    *, timeframe, category_trackers, competitor_trackers, events
):
    return build_dashboard_overview(
        timeframe=timeframe,
        category_trackers=category_trackers,
        competitor_trackers=competitor_trackers,
        events=events,
    )


def _build_timeline_summary(events):
    return build_timeline_summary(events)


def _build_top_threats(events, tracker_name_map):
    return build_top_threats(events, tracker_name_map)


def _generate_tracker_code(prefix: str, name: str, existing_codes: set[str]) -> str:
    return generate_tracker_code(prefix, name, existing_codes)


def _generate_job_code(*, snapshot_date, tracker_type, existing_codes: set[str]) -> str:
    tracker_enum = (
        tracker_type
        if isinstance(tracker_type, TrackerType)
        else TrackerType(str(tracker_type))
    )
    return generate_job_code(tracker_enum, snapshot_date, existing_codes)


def _sort_events(events):
    return sort_events(events)


def _within_range(value, from_date=None, to_date=None):
    return within_range(value, from_date, to_date)


class BaseStore:
    async def close(self) -> None:
        return None

    async def seed_demo_data(self, seed_data: SeedData) -> None:
        raise NotImplementedError

    async def get_dashboard_overview(
        self, workspace_id: str, timeframe: Timeframe
    ) -> DashboardOverview:
        raise NotImplementedError

    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        raise NotImplementedError

    async def create_category_tracker(
        self, workspace_id: str, payload: CategoryTrackerCreateRequest
    ) -> CategoryTracker:
        raise NotImplementedError

    async def get_category_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CategoryTracker:
        raise NotImplementedError

    async def update_category_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CategoryTrackerUpdateRequest,
    ) -> CategoryTracker:
        raise NotImplementedError

    async def get_latest_category_snapshot(
        self, workspace_id: str, tracker_code: str
    ) -> CategorySnapshot:
        raise NotImplementedError

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        raise NotImplementedError

    async def create_competitor_tracker(
        self, workspace_id: str, payload: CompetitorTrackerCreateRequest
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def get_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def update_competitor_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CompetitorTrackerUpdateRequest,
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def replace_tracked_asins(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: TrackedAsinReplacementRequest,
    ) -> CompetitorTrackerDetail:
        raise NotImplementedError

    async def get_product_detail(
        self, workspace_id: str, marketplace: str, asin: str
    ) -> ProductDetail:
        raise NotImplementedError

    async def get_product_timeline(
        self,
        workspace_id: str,
        marketplace: str,
        asin: str,
        from_date: date | None,
        to_date: date | None,
        granularity: Timeframe,
    ) -> ProductTimelineResponse:
        raise NotImplementedError

    async def list_events(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        from_date: date | None = None,
        to_date: date | None = None,
        tracker_type: TrackerType | None = None,
        tracker_code: str | None = None,
        marketplace: str | None = None,
        asin: str | None = None,
        event_type: EventType | None = None,
        severity: Severity | None = None,
    ) -> EventListResponse:
        raise NotImplementedError

    async def list_jobs(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        from_date: date | None = None,
        to_date: date | None = None,
        tracker_type: TrackerType | None = None,
        tracker_code: str | None = None,
        status: JobStatus | None = None,
    ) -> JobListResponse:
        raise NotImplementedError

    async def create_job(self, workspace_id: str, payload: JobCreateRequest) -> Job:
        raise NotImplementedError

    async def dispatch_job(self, workspace_id: str, job_code: str) -> None:
        raise NotImplementedError

    async def handle_apify_webhook(
        self,
        payload: ApifyWebhookEnvelope,
    ) -> ApifyWebhookAck:
        raise NotImplementedError

    async def poll_apify_runs(self) -> ApifyRunPollResult:
        raise NotImplementedError

    async def process_import_jobs(self) -> ImportWorkerResult:
        raise NotImplementedError

    async def schedule_jobs(self) -> SchedulerWorkerResult:
        raise NotImplementedError

    async def process_digest_jobs(self) -> DigestWorkerResult:
        raise NotImplementedError

    async def get_job(self, workspace_id: str, job_code: str) -> Job:
        raise NotImplementedError

    async def list_weekly_digests(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        week_start: date | None = None,
    ) -> WeeklyDigestListResponse:
        raise NotImplementedError

    async def get_weekly_digest(
        self, workspace_id: str, digest_code: str
    ) -> WeeklyDigest:
        raise NotImplementedError


class MongoStore(BaseStore):
    def __init__(
        self, client: AsyncMongoClient, database_name: str, settings: Config
    ) -> None:
        self.client = client
        self.database_name = database_name
        self.settings = settings
        self.apify_gateway = ApifyGateway(settings.apify_config)
        self.tracker_management = TrackerManagementService()
        self.dashboard_query = DashboardQueryService()
        self.run_orchestrator = RunOrchestrator(self.apify_gateway)
        self.job_service = JobService(self.run_orchestrator)
        self.scheduler_service = SchedulerService(self.job_service)
        self.digest_service = DigestService()
        self.normalization_service = NormalizationService()
        self.snapshot_service = SnapshotService()
        self.diff_service = DiffService()
        self.event_engine = EventEngine(self.diff_service)
        self.object_storage = LocalObjectStorageService(
            settings.storage_config.local_object_store_root
        )
        self.result_importer = ResultImporterService(
            self.apify_gateway,
            self.normalization_service,
            self.snapshot_service,
            self.event_engine,
            settings.apify_config,
            settings.storage_config,
            self.object_storage,
        )
        self.apify_run_lifecycle = ApifyRunLifecycleService(
            self.apify_gateway,
            settings.apify_config,
        )

    async def close(self) -> None:
        result = self.client.close()
        if isawaitable(result):
            await result

    async def seed_demo_data(self, seed_data: SeedData) -> None:
        for tracker in seed_data.category_trackers:
            existing = await CategoryTrackerDocument.find_one(
                CategoryTrackerDocument.workspace_id == seed_data.workspace_id,
                CategoryTrackerDocument.tracker_code == tracker.tracker_code,
            )
            payload = tracker.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await CategoryTrackerDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for snapshot in seed_data.category_snapshots:
            existing = await CategorySnapshotDocument.find_one(
                CategorySnapshotDocument.workspace_id == seed_data.workspace_id,
                CategorySnapshotDocument.tracker_code == snapshot.tracker_code,
                CategorySnapshotDocument.snapshot_date == snapshot.snapshot_date,
            )
            payload = snapshot.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await CategorySnapshotDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for tracker in seed_data.competitor_trackers:
            existing = await CompetitorTrackerDocument.find_one(
                CompetitorTrackerDocument.workspace_id == seed_data.workspace_id,
                CompetitorTrackerDocument.tracker_code == tracker.tracker_code,
            )
            payload = tracker.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await CompetitorTrackerDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for event in seed_data.events:
            existing = await EventDocument.find_one(
                EventDocument.workspace_id == seed_data.workspace_id,
                EventDocument.event_code == event.event_code,
            )
            payload = event.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await EventDocument(
                    workspace_id=seed_data.workspace_id, **payload
                ).insert()

        for product in seed_data.products:
            existing = await ProductDocument.find_one(
                ProductDocument.workspace_id == seed_data.workspace_id,
                ProductDocument.marketplace == product.marketplace,
                ProductDocument.asin == product.asin,
            )
            payload = product.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await ProductDocument(
                    workspace_id=seed_data.workspace_id, **payload
                ).insert()

        for snapshot in seed_data.product_snapshots:
            existing = await ProductSnapshotDocument.find_one(
                ProductSnapshotDocument.workspace_id == seed_data.workspace_id,
                ProductSnapshotDocument.marketplace == snapshot.marketplace,
                ProductSnapshotDocument.asin == snapshot.asin,
                ProductSnapshotDocument.snapshot_date == snapshot.snapshot_date,
            )
            payload = snapshot.model_dump(mode="python")
            payload.setdefault("created_at", payload.get("captured_at"))
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await ProductSnapshotDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

        for job in seed_data.jobs:
            existing = await JobDocument.find_one(
                JobDocument.workspace_id == seed_data.workspace_id,
                JobDocument.job_code == job.job_code,
            )
            payload = job.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await JobDocument(
                    workspace_id=seed_data.workspace_id, **payload
                ).insert()

        for digest in seed_data.weekly_digests:
            existing = await WeeklyDigestDocument.find_one(
                WeeklyDigestDocument.workspace_id == seed_data.workspace_id,
                WeeklyDigestDocument.digest_code == digest.digest_code,
            )
            payload = digest.model_dump(mode="python")
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await WeeklyDigestDocument(
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

    async def get_dashboard_overview(
        self, workspace_id: str, timeframe: Timeframe
    ) -> DashboardOverview:
        return await self.dashboard_query.get_dashboard_overview(
            workspace_id, timeframe
        )

    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        return await self.tracker_management.list_category_trackers(
            workspace_id, page, page_size
        )

    async def create_category_tracker(
        self, workspace_id: str, payload: CategoryTrackerCreateRequest
    ) -> CategoryTracker:
        return await self.tracker_management.create_category_tracker(
            workspace_id, payload
        )

    async def get_category_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CategoryTracker:
        return await self.tracker_management.get_category_tracker(
            workspace_id, tracker_code
        )

    async def update_category_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CategoryTrackerUpdateRequest,
    ) -> CategoryTracker:
        return await self.tracker_management.update_category_tracker(
            workspace_id,
            tracker_code,
            payload,
        )

    async def get_latest_category_snapshot(
        self, workspace_id: str, tracker_code: str
    ) -> CategorySnapshot:
        return await self.tracker_management.get_latest_category_snapshot(
            workspace_id, tracker_code
        )

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        return await self.tracker_management.list_competitor_trackers(
            workspace_id, page, page_size
        )

    async def create_competitor_tracker(
        self, workspace_id: str, payload: CompetitorTrackerCreateRequest
    ) -> CompetitorTrackerDetail:
        return await self.tracker_management.create_competitor_tracker(
            workspace_id, payload
        )

    async def get_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CompetitorTrackerDetail:
        return await self.tracker_management.get_competitor_tracker(
            workspace_id, tracker_code
        )

    async def update_competitor_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CompetitorTrackerUpdateRequest,
    ) -> CompetitorTrackerDetail:
        return await self.tracker_management.update_competitor_tracker(
            workspace_id,
            tracker_code,
            payload,
        )

    async def replace_tracked_asins(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: TrackedAsinReplacementRequest,
    ) -> CompetitorTrackerDetail:
        return await self.tracker_management.replace_tracked_asins(
            workspace_id,
            tracker_code,
            payload,
        )

    async def get_product_detail(
        self, workspace_id: str, marketplace: str, asin: str
    ) -> ProductDetail:
        return await self.dashboard_query.get_product_detail(
            workspace_id, marketplace, asin
        )

    async def get_product_timeline(
        self,
        workspace_id: str,
        marketplace: str,
        asin: str,
        from_date: date | None,
        to_date: date | None,
        granularity: Timeframe,
    ) -> ProductTimelineResponse:
        return await self.dashboard_query.get_product_timeline(
            workspace_id=workspace_id,
            marketplace=marketplace,
            asin=asin,
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
        )

    async def list_events(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        from_date: date | None = None,
        to_date: date | None = None,
        tracker_type: TrackerType | None = None,
        tracker_code: str | None = None,
        marketplace: str | None = None,
        asin: str | None = None,
        event_type: EventType | None = None,
        severity: Severity | None = None,
    ) -> EventListResponse:
        return await self.dashboard_query.list_events(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            from_date=from_date,
            to_date=to_date,
            tracker_type=tracker_type,
            tracker_code=tracker_code,
            marketplace=marketplace,
            asin=asin,
            event_type=event_type,
            severity=severity,
        )

    async def list_jobs(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        from_date: date | None = None,
        to_date: date | None = None,
        tracker_type: TrackerType | None = None,
        tracker_code: str | None = None,
        status: JobStatus | None = None,
    ) -> JobListResponse:
        return await self.job_service.list_jobs(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            from_date=from_date,
            to_date=to_date,
            tracker_type=tracker_type,
            tracker_code=tracker_code,
            status=status,
        )

    async def create_job(self, workspace_id: str, payload: JobCreateRequest) -> Job:
        return await self.job_service.create_job(workspace_id, payload)

    async def dispatch_job(self, workspace_id: str, job_code: str) -> None:
        await self.job_service.dispatch_job(workspace_id, job_code)

    async def handle_apify_webhook(
        self,
        payload: ApifyWebhookEnvelope,
    ) -> ApifyWebhookAck:
        return await self.apify_run_lifecycle.handle_webhook(payload)

    async def poll_apify_runs(self) -> ApifyRunPollResult:
        return await self.apify_run_lifecycle.poll_runs()

    async def process_import_jobs(self) -> ImportWorkerResult:
        return await self.result_importer.process_pending_jobs()

    async def schedule_jobs(self) -> SchedulerWorkerResult:
        return await self.scheduler_service.schedule_due_jobs()

    async def process_digest_jobs(self) -> DigestWorkerResult:
        return await self.digest_service.generate_weekly_digests()

    async def get_job(self, workspace_id: str, job_code: str) -> Job:
        return await self.job_service.get_job(workspace_id, job_code)

    async def list_weekly_digests(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        week_start: date | None = None,
    ) -> WeeklyDigestListResponse:
        return await self.dashboard_query.list_weekly_digests(
            workspace_id,
            page,
            page_size,
            week_start,
        )

    async def get_weekly_digest(
        self, workspace_id: str, digest_code: str
    ) -> WeeklyDigest:
        return await self.dashboard_query.get_weekly_digest(workspace_id, digest_code)


async def build_store(settings: Config) -> BaseStore:
    client = AsyncMongoClient(settings.mongodb_config.dsn)
    await init_beanie(
        database=client[settings.mongodb_config.database],
        document_models=DOCUMENT_MODELS,
    )
    return MongoStore(
        client=client,
        database_name=settings.mongodb_config.database,
        settings=settings,
    )
