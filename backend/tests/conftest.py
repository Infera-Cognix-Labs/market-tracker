from __future__ import annotations

import asyncio

import pytest

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
