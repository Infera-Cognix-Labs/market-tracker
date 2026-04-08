from __future__ import annotations

import json
from pathlib import Path


class LocalObjectStorageService:
    def __init__(self, root_dir: str) -> None:
        self.root_dir = Path(root_dir)

    async def write_raw_batch(
        self,
        *,
        workspace_id: str,
        apify_run_id: str,
        batch_no: int,
        items: list[dict[str, object]],
    ) -> str:
        path = self._raw_batch_path(
            workspace_id=workspace_id,
            apify_run_id=apify_run_id,
            batch_no=batch_no,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items, ensure_ascii=True), encoding="utf-8")
        return f"local://{path.as_posix()}"

    async def read_raw_batch(self, storage_uri: str) -> list[dict[str, object]]:
        path = self._path_from_uri(storage_uri)
        if not path.exists() or not path.is_file():
            return []

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _raw_batch_path(
        self,
        *,
        workspace_id: str,
        apify_run_id: str,
        batch_no: int,
    ) -> Path:
        return (
            self.root_dir
            / "raw-import-batches"
            / workspace_id
            / apify_run_id
            / f"batch_{batch_no:05d}.json"
        )

    def _path_from_uri(self, storage_uri: str) -> Path:
        prefix = "local://"
        if storage_uri.startswith(prefix):
            return Path(storage_uri.removeprefix(prefix))
        return Path(storage_uri)
