from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

_APP_CONFIG_PATH = Path(__file__).resolve().parents[2] / "app-config.yaml"


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int | None = None) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return int(raw_value)


def _read_secret(*, env_name: str) -> str | None:
    env_value = os.getenv(env_name)
    if env_value is not None and env_value.strip() != "":
        return env_value.strip()
    return None


def _parse_yaml_scalar(raw_value: str) -> object:
    stripped = raw_value.strip()
    if stripped in {"", "null", "NULL", "~"}:
        return None
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    try:
        return int(stripped)
    except ValueError:
        return stripped


def _parse_simple_yaml(text: str) -> dict[str, object]:
    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue

        normalized_line = line_without_comment.replace("\t", "  ")
        indent = len(normalized_line) - len(normalized_line.lstrip(" "))
        stripped_line = normalized_line.strip()
        if ":" not in stripped_line:
            continue

        key_part, _, value_part = stripped_line.partition(":")
        key = key_part.strip()
        value = value_part.strip()
        if not key:
            continue

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value == "":
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indent, child))
            continue

        parent[key] = _parse_yaml_scalar(value)

    return root


@lru_cache(maxsize=1)
def _load_app_file_config() -> dict[str, object]:
    config_path = _APP_CONFIG_PATH.expanduser()
    if not config_path.exists() or not config_path.is_file():
        return {}

    raw_text = config_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return {}

    try:
        parsed_json = json.loads(raw_text)
        if isinstance(parsed_json, dict):
            return parsed_json
    except json.JSONDecodeError:
        pass

    parsed_yaml = _parse_simple_yaml(raw_text)
    return parsed_yaml if isinstance(parsed_yaml, dict) else {}


def _config_value(path: tuple[str, ...], default: object = None) -> object:
    current: object = _load_app_file_config()
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _config_str(
    path: tuple[str, ...],
    default: str | None = None,
    env_name: str | None = None,
) -> str | None:
    value = _config_value(path)
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    if value is not None and not isinstance(value, dict):
        return str(value)
    if env_name:
        env_value = os.getenv(env_name)
        if env_value is not None and env_value.strip() != "":
            return env_value.strip()
    return default


def _config_int(
    path: tuple[str, ...],
    default: int,
    env_name: str | None = None,
) -> int:
    value = _config_value(path)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip() != "":
        return int(value)
    if env_name:
        env_value = _env_int(env_name)
        if env_value is not None:
            return env_value
    return default


def _config_bool(
    path: tuple[str, ...],
    default: bool,
    env_name: str | None = None,
) -> bool:
    value = _config_value(path)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip() != "":
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if env_name:
        return _env_bool(env_name, default)
    return default


def _binding_config(binding_key: str) -> dict[str, object]:
    file_config = _load_app_file_config()
    apify_config = file_config.get("apify")
    if isinstance(apify_config, dict):
        bindings = apify_config.get("bindings")
        if isinstance(bindings, dict):
            section = bindings.get(binding_key)
            if isinstance(section, dict):
                return section

    bindings = file_config.get("bindings")
    if isinstance(bindings, dict):
        section = bindings.get(binding_key)
        if isinstance(section, dict):
            return section

    direct = file_config.get(binding_key)
    if isinstance(direct, dict):
        return direct
    return {}


def _binding_str(
    binding_key: str, field: str, fallback_env: str | None = None
) -> str | None:
    section = _binding_config(binding_key)
    value = section.get(field)
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    if fallback_env:
        env_value = os.getenv(fallback_env)
        if env_value is not None and env_value.strip() != "":
            return env_value.strip()
    return None


def _binding_int(
    binding_key: str, field: str, fallback_env: str | None = None
) -> int | None:
    section = _binding_config(binding_key)
    value: Any = section.get(field)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip() != "":
        return int(value)
    if fallback_env:
        return _env_int(fallback_env)
    return None


class MongoDBConfig(BaseModel):
    uri: str | None = Field(default_factory=lambda: os.getenv("MONGO_URI"))
    host: str = Field(default_factory=lambda: os.getenv("MONGO_HOST") or "localhost")
    port: int = Field(default_factory=lambda: _env_int("MONGO_PORT", 27017) or 27017)
    username: str | None = Field(default_factory=lambda: os.getenv("MONGO_USERNAME"))
    password: str | None = Field(default_factory=lambda: os.getenv("MONGO_PASSWORD"))
    database: str = Field(
        default_factory=lambda: os.getenv("MONGO_DATABASE") or "market_tracker"
    )

    @property
    def dsn(self) -> str:
        if self.uri:
            return self.uri
        credentials = ""
        if self.username:
            password = f":{self.password}" if self.password else ""
            credentials = f"{self.username}{password}@"
        return f"mongodb://{credentials}{self.host}:{self.port}"


class ApifyConfig(BaseModel):
    token: str | None = _read_secret(env_name="APIFY_TOKEN")
    dispatch_timeout_secs: int = _config_int(
        ("apify", "dispatch_timeout_secs"),
        300,
        "APIFY_DISPATCH_TIMEOUT_SECS",
    )
    webhook_url: str | None = _config_str(
        ("apify", "webhook_url"),
        None,
        "APIFY_WEBHOOK_URL",
    )
    poll_batch_size: int = _config_int(
        ("apify", "poll_batch_size"),
        25,
        "APIFY_POLL_BATCH_SIZE",
    )
    poll_interval_secs: int = _config_int(
        ("apify", "poll_interval_secs"),
        60,
        "APIFY_POLL_INTERVAL_SECS",
    )
    import_batch_size: int = _config_int(
        ("apify", "import_batch_size"),
        200,
        "APIFY_IMPORT_BATCH_SIZE",
    )
    import_worker_batch_size: int = _config_int(
        ("apify", "import_worker_batch_size"),
        10,
        "APIFY_IMPORT_WORKER_BATCH_SIZE",
    )
    import_worker_interval_secs: int = _config_int(
        ("apify", "import_worker_interval_secs"),
        30,
        "APIFY_IMPORT_WORKER_INTERVAL_SECS",
    )
    category_actor_name: str | None = _binding_str("category", "name")
    category_actor_id: str | None = _binding_str(
        "category", "actor_id", "APIFY_CATEGORY_ACTOR_ID"
    )
    category_task_id: str | None = _binding_str(
        "category", "task_id", "APIFY_CATEGORY_TASK_ID"
    )
    category_build: str | None = _binding_str(
        "category", "build", "APIFY_CATEGORY_BUILD"
    )
    category_memory_mbytes: int | None = _binding_int(
        "category", "memory_mbytes", "APIFY_CATEGORY_MEMORY_MBYTES"
    )
    competitor_actor_name: str | None = _binding_str("competitor", "name")
    competitor_actor_id: str | None = _binding_str(
        "competitor", "actor_id", "APIFY_COMPETITOR_ACTOR_ID"
    )
    competitor_task_id: str | None = _binding_str(
        "competitor", "task_id", "APIFY_COMPETITOR_TASK_ID"
    )
    competitor_build: str | None = _binding_str(
        "competitor", "build", "APIFY_COMPETITOR_BUILD"
    )
    competitor_memory_mbytes: int | None = _binding_int(
        "competitor", "memory_mbytes", "APIFY_COMPETITOR_MEMORY_MBYTES"
    )
    deals_actor_name: str | None = _binding_str("deals", "name")
    deals_actor_id: str | None = _binding_str("deals", "actor_id", "APIFY_DEALS_ACTOR_ID")
    deals_task_id: str | None = _binding_str("deals", "task_id", "APIFY_DEALS_TASK_ID")
    deals_build: str | None = _binding_str("deals", "build", "APIFY_DEALS_BUILD")
    deals_memory_mbytes: int | None = _binding_int(
        "deals", "memory_mbytes", "APIFY_DEALS_MEMORY_MBYTES"
    )
    deals_max_results: int = _config_int(
        ("apify", "deals_max_results"),
        100,
        "APIFY_DEALS_MAX_RESULTS",
    )
    category_enrichment_actor_name: str | None = _binding_str(
        "category_enrichment", "name"
    )
    category_enrichment_actor_id: str | None = _binding_str(
        "category_enrichment",
        "actor_id",
        "APIFY_CATEGORY_ENRICHMENT_ACTOR_ID",
    )
    category_enrichment_task_id: str | None = _binding_str(
        "category_enrichment",
        "task_id",
        "APIFY_CATEGORY_ENRICHMENT_TASK_ID",
    )
    category_enrichment_build: str | None = _binding_str(
        "category_enrichment",
        "build",
        "APIFY_CATEGORY_ENRICHMENT_BUILD",
    )
    category_enrichment_memory_mbytes: int | None = _binding_int(
        "category_enrichment",
        "memory_mbytes",
        "APIFY_CATEGORY_ENRICHMENT_MEMORY_MBYTES",
    )


class StorageConfig(BaseModel):
    raw_batch_offload_enabled: bool = _config_bool(
        ("storage", "raw_batch_offload_enabled"),
        False,
        "RAW_BATCH_OFFLOAD_ENABLED",
    )
    raw_batch_offload_min_items: int = _config_int(
        ("storage", "raw_batch_offload_min_items"),
        200,
        "RAW_BATCH_OFFLOAD_MIN_ITEMS",
    )
    local_object_store_root: str = (
        _config_str(
            ("storage", "local_object_store_root"),
            "outputs/object-store",
            "LOCAL_OBJECT_STORE_ROOT",
        )
        or "outputs/object-store"
    )


class WorkerConfig(BaseModel):
    scheduler_interval_secs: int = _config_int(
        ("workers", "scheduler_interval_secs"),
        60,
        "SCHEDULER_WORKER_INTERVAL_SECS",
    )
    digest_interval_secs: int = _config_int(
        ("workers", "digest_interval_secs"),
        3600,
        "DIGEST_WORKER_INTERVAL_SECS",
    )


class Config(BaseModel):
    app_name: str = (
        _config_str(("app", "name"), "Market Tracker API") or "Market Tracker API"
    )
    api_prefix: str = _config_str(("app", "api_prefix"), "/v1") or "/v1"
    seed_demo_data: bool = _config_bool(
        ("app", "seed_demo_data"), True, "SEED_DEMO_DATA"
    )
    mongodb_config: MongoDBConfig = Field(default_factory=MongoDBConfig)
    apify_config: ApifyConfig = ApifyConfig()
    storage_config: StorageConfig = StorageConfig()
    worker_config: WorkerConfig = WorkerConfig()


@lru_cache(maxsize=1)
def get_settings() -> Config:
    return Config()
