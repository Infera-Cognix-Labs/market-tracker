from __future__ import annotations


from app.models.api import (
    CategorySnapshot,
    CategoryTracker,
    CategoryTrackerCreateRequest,
    CategoryTrackerListResponse,
    CategoryTrackerUpdateRequest,
    CompetitorTrackerCreateRequest,
    CompetitorTrackerDetail,
    CompetitorTrackerListResponse,
    CompetitorTrackerUpdateRequest,
    KeywordSnapshot,
    KeywordTracker,
    KeywordTrackerCreateRequest,
    KeywordTrackerListResponse,
    KeywordTrackerUpdateRequest,
    Timeframe,
    TrackedAsinReplacementRequest,
)
from app.services.tracker_management_service import TrackerManagementService


class TrackerModule:
    def __init__(self, tracker_management: TrackerManagementService) -> None:
        self._service = tracker_management

    async def list_category_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CategoryTrackerListResponse:
        return await self._service.list_category_trackers(workspace_id, page, page_size)

    async def create_category_tracker(
        self, workspace_id: str, payload: CategoryTrackerCreateRequest
    ) -> CategoryTracker:
        return await self._service.create_category_tracker(workspace_id, payload)

    async def get_category_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CategoryTracker:
        return await self._service.get_category_tracker(workspace_id, tracker_code)

    async def update_category_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CategoryTrackerUpdateRequest,
    ) -> CategoryTracker:
        return await self._service.update_category_tracker(
            workspace_id, tracker_code, payload
        )

    async def get_latest_category_snapshot(
        self,
        workspace_id: str,
        tracker_code: str,
        timeframe: Timeframe = Timeframe.WEEKLY,
    ) -> CategorySnapshot:
        return await self._service.get_latest_category_snapshot(
            workspace_id, tracker_code, timeframe
        )

    async def list_competitor_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> CompetitorTrackerListResponse:
        return await self._service.list_competitor_trackers(
            workspace_id, page, page_size
        )

    async def create_competitor_tracker(
        self, workspace_id: str, payload: CompetitorTrackerCreateRequest
    ) -> CompetitorTrackerDetail:
        return await self._service.create_competitor_tracker(workspace_id, payload)

    async def get_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> CompetitorTrackerDetail:
        return await self._service.get_competitor_tracker(workspace_id, tracker_code)

    async def update_competitor_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: CompetitorTrackerUpdateRequest,
    ) -> CompetitorTrackerDetail:
        return await self._service.update_competitor_tracker(
            workspace_id, tracker_code, payload
        )

    async def replace_tracked_asins(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: TrackedAsinReplacementRequest,
    ) -> CompetitorTrackerDetail:
        return await self._service.replace_tracked_asins(
            workspace_id, tracker_code, payload
        )

    async def delete_category_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> None:
        await self._service.delete_category_tracker(workspace_id, tracker_code)

    async def delete_competitor_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> None:
        await self._service.delete_competitor_tracker(workspace_id, tracker_code)

    async def list_keyword_trackers(
        self, workspace_id: str, page: int, page_size: int
    ) -> KeywordTrackerListResponse:
        return await self._service.list_keyword_trackers(workspace_id, page, page_size)

    async def create_keyword_tracker(
        self, workspace_id: str, payload: KeywordTrackerCreateRequest
    ) -> KeywordTracker:
        return await self._service.create_keyword_tracker(workspace_id, payload)

    async def get_keyword_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> KeywordTracker:
        return await self._service.get_keyword_tracker(workspace_id, tracker_code)

    async def update_keyword_tracker(
        self,
        workspace_id: str,
        tracker_code: str,
        payload: KeywordTrackerUpdateRequest,
    ) -> KeywordTracker:
        return await self._service.update_keyword_tracker(
            workspace_id, tracker_code, payload
        )

    async def get_latest_keyword_snapshot(
        self,
        workspace_id: str,
        tracker_code: str,
        timeframe: Timeframe = Timeframe.WEEKLY,
    ) -> KeywordSnapshot:
        return await self._service.get_latest_keyword_snapshot(
            workspace_id, tracker_code, timeframe
        )

    async def delete_keyword_tracker(
        self, workspace_id: str, tracker_code: str
    ) -> None:
        await self._service.delete_keyword_tracker(workspace_id, tracker_code)
