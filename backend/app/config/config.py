from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


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


def _read_secret(*, env_name: str, file_env_name: str) -> str | None:
    env_value = os.getenv(env_name)
    if env_value is not None and env_value.strip() != "":
        return env_value.strip()

    file_path = os.getenv(file_env_name)
    if not file_path:
        return None
    path = Path(file_path).expanduser()
    if not path.exists() or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


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
def _load_apify_file_config() -> dict[str, object]:
    default_path = Path(__file__).resolve().parents[2] / "apify-config.yaml"
    config_path = Path(os.getenv("APIFY_CONFIG_FILE", str(default_path))).expanduser()
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


def _binding_config(binding_key: str) -> dict[str, object]:
    file_config = _load_apify_file_config()
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
    uri: str | None = os.getenv("MONGO_URI")
    host: str = os.getenv("MONGO_HOST", "localhost")
    port: int = int(os.getenv("MONGO_PORT", "27017"))
    username: str | None = os.getenv("MONGO_USERNAME")
    password: str | None = os.getenv("MONGO_PASSWORD")
    database: str = os.getenv("MONGO_DATABASE", "market_tracker")

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
    token: str | None = _read_secret(
        env_name="APIFY_TOKEN",
        file_env_name="APIFY_TOKEN_FILE",
    )
    dispatch_timeout_secs: int = _env_int("APIFY_DISPATCH_TIMEOUT_SECS", 300) or 300
    webhook_url: str | None = os.getenv("APIFY_WEBHOOK_URL")
    webhook_secret: str | None = os.getenv("APIFY_WEBHOOK_SECRET")
    poll_batch_size: int = _env_int("APIFY_POLL_BATCH_SIZE", 25) or 25
    poll_interval_secs: int = _env_int("APIFY_POLL_INTERVAL_SECS", 60) or 60
    import_batch_size: int = _env_int("APIFY_IMPORT_BATCH_SIZE", 200) or 200
    import_worker_batch_size: int = _env_int("APIFY_IMPORT_WORKER_BATCH_SIZE", 10) or 10
    import_worker_interval_secs: int = (
        _env_int("APIFY_IMPORT_WORKER_INTERVAL_SECS", 30) or 30
    )
    config_file: str = os.getenv("APIFY_CONFIG_FILE", "apify-config.yaml")
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
    category_input_adapter: str = _binding_str("category", "input_adapter") or "native"
    category_amazon_domain: str | None = _binding_str("category", "amazon_domain")
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
    competitor_input_adapter: str = (
        _binding_str("competitor", "input_adapter") or "native"
    )
    competitor_amazon_domain: str | None = _binding_str("competitor", "amazon_domain")


class StorageConfig(BaseModel):
    raw_batch_offload_enabled: bool = _env_bool("RAW_BATCH_OFFLOAD_ENABLED", False)
    raw_batch_offload_min_items: int = (
        _env_int("RAW_BATCH_OFFLOAD_MIN_ITEMS", 200) or 200
    )
    local_object_store_root: str = os.getenv(
        "LOCAL_OBJECT_STORE_ROOT", "outputs/object-store"
    )


class WorkerConfig(BaseModel):
    scheduler_interval_secs: int = _env_int("SCHEDULER_WORKER_INTERVAL_SECS", 60) or 60
    digest_interval_secs: int = _env_int("DIGEST_WORKER_INTERVAL_SECS", 3600) or 3600


class Config(BaseModel):
    app_name: str = "Market Tracker API"
    api_prefix: str = "/v1"
    seed_demo_data: bool = _env_bool("SEED_DEMO_DATA", True)
    mongodb_config: MongoDBConfig = MongoDBConfig()
    apify_config: ApifyConfig = ApifyConfig()
    storage_config: StorageConfig = StorageConfig()
    worker_config: WorkerConfig = WorkerConfig()


@lru_cache(maxsize=1)
def get_settings() -> Config:
    return Config()
