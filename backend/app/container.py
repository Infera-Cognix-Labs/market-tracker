from __future__ import annotations

from typing import Any, Callable, TypeVar

from app.config.config import Config


T = TypeVar("T")


class Container:
    def __init__(
        self,
        factories: dict[type, Callable[..., Any]] | None = None,
        config: Config | None = None,
    ):
        self._factories = factories or {}
        self._singletons: dict[type, Any] = {}
        self._config = config

    def register(self, interface: type[T], factory: Callable[..., T]) -> None:
        self._factories[interface] = factory

    def register_singleton(self, interface: type[T], instance: T) -> None:
        self._singletons[interface] = instance

    def resolve(self, interface: type[T]) -> T:
        if interface in self._singletons:
            return self._singletons[interface]

        if interface not in self._factories:
            raise KeyError(f"No factory registered for {interface}")

        factory = self._factories[interface]
        instance = factory(self)
        return instance


def create_container(config: Config) -> Container:
    from app.integrations.apify_gateway import ApifyGateway
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
    from app.services.snapshot_service import SnapshotService
    from app.services.tracker_management_service import TrackerManagementService
    from app.store_domain.tracker_module import TrackerModule
    from app.store_domain.query_module import QueryModule
    from app.store_domain.job_module import JobModule
    from app.store_domain.worker_module import WorkerModule
    from app.store_domain.seed_module import SeedModule

    factories: dict[type, Callable[..., Any]] = {}

    def create_apify_gateway(c: Container) -> ApifyGateway:
        return ApifyGateway(config.apify_config)

    def create_object_storage(c: Container) -> LocalObjectStorageService:
        return LocalObjectStorageService(config.storage_config.local_object_store_root)

    def create_normalization_service(c: Container) -> NormalizationService:
        return NormalizationService()

    def create_snapshot_service(c: Container) -> SnapshotService:
        return SnapshotService()

    def create_diff_service(c: Container) -> DiffService:
        return DiffService()

    def create_tracker_management(c: Container) -> TrackerManagementService:
        return TrackerManagementService()

    def create_dashboard_query(c: Container) -> DashboardQueryService:
        return DashboardQueryService()

    def create_digest_service(c: Container) -> DigestService:
        return DigestService()

    def create_apify_gateway_singleton(c: Container) -> ApifyGateway:
        gateway = create_apify_gateway(c)
        c.register_singleton(ApifyGateway, gateway)
        return gateway

    def create_object_storage_singleton(c: Container) -> LocalObjectStorageService:
        storage = create_object_storage(c)
        c.register_singleton(LocalObjectStorageService, storage)
        return storage

    def create_run_orchestrator(c: Container) -> RunOrchestrator:
        return RunOrchestrator(c.resolve(ApifyGateway))

    def create_diff_service_singleton(c: Container) -> DiffService:
        diff = create_diff_service(c)
        c.register_singleton(DiffService, diff)
        return diff

    def create_event_engine(c: Container) -> EventEngine:
        return EventEngine(c.resolve(DiffService))

    def create_run_orchestrator_singleton(c: Container) -> RunOrchestrator:
        orchestrator = create_run_orchestrator(c)
        c.register_singleton(RunOrchestrator, orchestrator)
        return orchestrator

    def create_job_service(c: Container) -> JobService:
        return JobService(c.resolve(RunOrchestrator))

    def create_result_importer(c: Container) -> ResultImporterService:
        return ResultImporterService(
            c.resolve(ApifyGateway),
            c.resolve(NormalizationService),
            c.resolve(SnapshotService),
            c.resolve(EventEngine),
            config.apify_config,
            config.storage_config,
            c.resolve(LocalObjectStorageService),
        )

    def create_apify_lifecycle(c: Container) -> ApifyRunLifecycleService:
        return ApifyRunLifecycleService(
            c.resolve(ApifyGateway),
            config.apify_config,
        )

    def create_tracker_module(c: Container) -> TrackerModule:
        return TrackerModule(c.resolve(TrackerManagementService))

    def create_query_module(c: Container) -> QueryModule:
        return QueryModule(c.resolve(DashboardQueryService))

    def create_job_module(c: Container) -> JobModule:
        return JobModule(
            c.resolve(JobService),
            c.resolve(RunOrchestrator),
            c.resolve(ApifyRunLifecycleService),
        )

    def create_seed_module(c: Container) -> SeedModule:
        from app.services.tracker_management_service import TrackerManagementService
        from app.services.dashboard_query_service import DashboardQueryService
        from app.services.digest_service import DigestService

        return SeedModule(
            tracker_management=c.resolve(TrackerManagementService),
            dashboard_query=c.resolve(DashboardQueryService),
            digest_service=c.resolve(DigestService),
        )

    def create_worker_module(c: Container) -> WorkerModule:
        return WorkerModule(
            scheduler_service=SchedulerService(c.resolve(JobService)),
            result_importer=c.resolve(ResultImporterService),
            apify_lifecycle=c.resolve(ApifyRunLifecycleService),
            digest_service=c.resolve(DigestService),
        )

    factories = {
        ApifyGateway: create_apify_gateway_singleton,
        LocalObjectStorageService: create_object_storage_singleton,
        NormalizationService: create_normalization_service,
        SnapshotService: create_snapshot_service,
        DiffService: create_diff_service_singleton,
        TrackerManagementService: create_tracker_management,
        DashboardQueryService: create_dashboard_query,
        DigestService: create_digest_service,
        RunOrchestrator: create_run_orchestrator_singleton,
        EventEngine: create_event_engine,
        JobService: create_job_service,
        ResultImporterService: create_result_importer,
        ApifyRunLifecycleService: create_apify_lifecycle,
        TrackerModule: create_tracker_module,
        QueryModule: create_query_module,
        JobModule: create_job_module,
        SeedModule: create_seed_module,
        WorkerModule: create_worker_module,
    }

    return Container(factories=factories, config=config)
