from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Sequence, TypeVar

T = TypeVar("T")

_slug_pattern = re.compile(r"[^a-z0-9]+")


def utc_now() -> datetime:
    return datetime.now(UTC)


def slugify(value: str) -> str:
    slug = _slug_pattern.sub("_", value.lower()).strip("_")
    return slug or "item"


def paginate(items: Sequence[T], page: int, page_size: int) -> tuple[list[T], int]:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return list(items[start:end]), total
