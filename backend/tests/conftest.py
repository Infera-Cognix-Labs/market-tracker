from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config.config import Config
from app.seed import SeedData, load_demo_seed


@pytest.fixture
def run_async():
    def _run(coro):
        return asyncio.run(coro)

    return _run


@pytest.fixture
def seed_data() -> SeedData:
    return load_demo_seed()


@pytest.fixture
def workspace_id() -> str:
    return "ws_demo_us"


@pytest.fixture
def mock_config() -> Config:
    config = MagicMock(spec=Config)
    config.mongodb_config.dsn = "mongodb://localhost:27017"
    config.mongodb_config.database = "test_market_tracker"
    config.apify_config.token = "test_token"
    config.storage_config.local_object_store_root = "/tmp/test_object_store"
    return config


@pytest.fixture
def mock_tracker_service():
    from app.services.tracker_management_service import TrackerManagementService
    service = MagicMock(spec=TrackerManagementService)
    return service


@pytest.fixture
def mock_dashboard_query_service():
    from app.services.dashboard_query_service import DashboardQueryService
    service = MagicMock(spec=DashboardQueryService)
    return service


@pytest.fixture
def mock_job_service():
    from app.services.job_service import JobService
    service = MagicMock(spec=JobService)
    return service


@pytest.fixture
def mock_diff_service():
    from app.services.diff_service import DiffService
    service = MagicMock(spec=DiffService)
    return service
