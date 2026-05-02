from __future__ import annotations

from datetime import date

from app.models.api import (
    DashboardOverview,
    EventListResponse,
    EventType,
    ProductDetail,
    ProductTimelineResponse,
    Severity,
    Timeframe,
    TrackerType,
    WeeklyDigest,
    WeeklyDigestListResponse,
)
from app.services.dashboard_query_service import DashboardQueryService


class QueryModule:
    def __init__(self, dashboard_query: DashboardQueryService) -> None:
        self._service = dashboard_query

    async def get_dashboard_overview(
        self, workspace_id: str, timeframe: Timeframe
    ) -> DashboardOverview:
        return await self._service.get_dashboard_overview(workspace_id, timeframe)

    async def get_product_detail(
        self, workspace_id: str, marketplace: str, asin: str
    ) -> ProductDetail:
        return await self._service.get_product_detail(workspace_id, marketplace, asin)

    async def get_product_timeline(
        self,
        workspace_id: str,
        marketplace: str,
        asin: str,
        from_date: date | None,
        to_date: date | None,
        granularity: Timeframe,
        tracker_code: str | None = None,
    ) -> ProductTimelineResponse:
        return await self._service.get_product_timeline(
            workspace_id=workspace_id,
            marketplace=marketplace,
            asin=asin,
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
            tracker_code=tracker_code,
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
        return await self._service.list_events(
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

    async def list_weekly_digests(
        self,
        workspace_id: str,
        page: int,
        page_size: int,
        week_start: date | None = None,
    ) -> WeeklyDigestListResponse:
        return await self._service.list_weekly_digests(
            workspace_id, page, page_size, week_start
        )

    async def get_weekly_digest(
        self, workspace_id: str, digest_code: str
    ) -> WeeklyDigest:
        return await self._service.get_weekly_digest(workspace_id, digest_code)