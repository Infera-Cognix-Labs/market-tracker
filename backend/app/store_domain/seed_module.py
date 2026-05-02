from __future__ import annotations

from app.models.documents import (
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


class SeedModule:
    async def seed_demo_data(self, seed_data: SeedData) -> None:
        await self._seed_category_trackers(seed_data)
        await self._seed_category_snapshots(seed_data)
        await self._seed_competitor_trackers(seed_data)
        await self._seed_events(seed_data)
        await self._seed_products(seed_data)
        await self._seed_product_snapshots(seed_data)
        await self._seed_jobs(seed_data)
        await self._seed_weekly_digests(seed_data)

    async def _seed_category_trackers(self, seed_data: SeedData) -> None:
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

    async def _seed_category_snapshots(self, seed_data: SeedData) -> None:
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

    async def _seed_competitor_trackers(self, seed_data: SeedData) -> None:
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

    async def _seed_events(self, seed_data: SeedData) -> None:
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

    async def _seed_products(self, seed_data: SeedData) -> None:
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
                    workspace_id=seed_data.workspace_id,
                    **payload,
                ).insert()

    async def _seed_product_snapshots(self, seed_data: SeedData) -> None:
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

    async def _seed_jobs(self, seed_data: SeedData) -> None:
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

    async def _seed_weekly_digests(self, seed_data: SeedData) -> None:
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
