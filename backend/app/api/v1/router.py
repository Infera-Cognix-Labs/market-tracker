from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    category_trackers,
    competitor_trackers,
    dashboard,
    events,
    jobs,
    keyword_trackers,
    notification_rules,
    products,
    reports,
    summaries,
    webhooks_apify,
)

api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(category_trackers.router)
api_router.include_router(competitor_trackers.router)
api_router.include_router(keyword_trackers.router)
api_router.include_router(products.router)
api_router.include_router(events.router)
api_router.include_router(notification_rules.router)
api_router.include_router(jobs.router)
api_router.include_router(reports.router)
api_router.include_router(summaries.router)
api_router.include_router(webhooks_apify.router)
