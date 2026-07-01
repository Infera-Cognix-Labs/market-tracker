from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
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
    stuck_processing_reclaim_secs: int = _config_int(
        ("apify", "stuck_processing_reclaim_secs"),
        900,
    )
    deals_max_results: int = _config_int(
        ("apify", "deals_max_results"),
        100,
        "APIFY_DEALS_MAX_RESULTS",
    )

    @property
    def actor_pools(self) -> dict[str, list[ActorPoolEntryConfig]]:
        return _actor_pools_config()


class InputAdapterConfig(BaseModel):
    field_map: dict[str, str] = Field(default_factory=dict)
    wrap_array: list[str] = Field(default_factory=list)
    wrap_object: dict[str, str] = Field(default_factory=dict)
    asin_to_url: str | None = None
    marketplace_map: dict[str, str] = Field(default_factory=dict)
    static_fields: dict[str, object] = Field(default_factory=dict)


class ActorPoolEntryConfig(BaseModel):
    actor_id: str | None = None
    task_id: str | None = None
    name: str | None = None
    adapter: str | None = None
    build: str | None = "latest"
    memory_mbytes: int | None = 4096
    enabled: bool = True
    priority: int = 0
    input_adapter: InputAdapterConfig | None = None


def _actor_pools_config() -> dict[str, list[ActorPoolEntryConfig]]:
    file_config = _load_app_file_config()
    apify_config = file_config.get("apify")
    if not isinstance(apify_config, dict):
        return {}

    pools_raw = apify_config.get("actor_pools")
    if not isinstance(pools_raw, dict):
        return {}

    result: dict[str, list[ActorPoolEntryConfig]] = {}
    for pool_code, entries_raw in pools_raw.items():
        if not isinstance(entries_raw, dict):
            continue
        entries: list[ActorPoolEntryConfig] = []
        for entry_name, entry_raw in entries_raw.items():
            if not isinstance(entry_raw, dict):
                continue
            input_adapter_raw = entry_raw.get("input_adapter")
            input_adapter = None
            if isinstance(input_adapter_raw, dict):
                field_map = input_adapter_raw.get("field_map")
                raw_wrap = input_adapter_raw.get("wrap_array")
                wrap_array: list[str] = []
                if isinstance(raw_wrap, str) and raw_wrap.strip():
                    wrap_array = [f.strip() for f in raw_wrap.split(",") if f.strip()]
                elif isinstance(raw_wrap, list):
                    wrap_array = [str(f) for f in raw_wrap]
                raw_wrap_object = input_adapter_raw.get("wrap_object")
                wrap_object: dict[str, str] = {}
                if isinstance(raw_wrap_object, dict):
                    wrap_object = {str(k): str(v) for k, v in raw_wrap_object.items()}
                asin_to_url = input_adapter_raw.get("asin_to_url")
                raw_marketplace_map = input_adapter_raw.get("marketplace_map")
                marketplace_map: dict[str, str] = {}
                if isinstance(raw_marketplace_map, dict):
                    marketplace_map = {
                        str(k): str(v) for k, v in raw_marketplace_map.items()
                    }
                static_fields_raw = input_adapter_raw.get("static_fields")
                input_adapter = InputAdapterConfig(
                    field_map=field_map if isinstance(field_map, dict) else {},
                    wrap_array=wrap_array,
                    wrap_object=wrap_object,
                    asin_to_url=asin_to_url if isinstance(asin_to_url, str) else None,
                    marketplace_map=marketplace_map,
                    static_fields=static_fields_raw
                    if isinstance(static_fields_raw, dict)
                    else {},
                )
            entries.append(
                ActorPoolEntryConfig(
                    actor_id=entry_raw.get("actor_id"),
                    task_id=entry_raw.get("task_id"),
                    name=entry_raw.get("name") or entry_name,
                    adapter=entry_raw.get("adapter"),
                    build=entry_raw.get("build", "latest"),
                    memory_mbytes=entry_raw.get("memory_mbytes", 4096),
                    enabled=entry_raw.get("enabled", True),
                    priority=entry_raw.get("priority", 0),
                    input_adapter=input_adapter,
                )
            )
        result[pool_code] = sorted(entries, key=lambda e: e.priority)
    return result


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
    notification_interval_secs: int = _config_int(
        ("workers", "notification_interval_secs"),
        60,
        "NOTIFICATION_WORKER_INTERVAL_SECS",
    )


class LLMConfig(BaseModel):
    enabled: bool = _config_bool(("llm", "enabled"), False, "LLM_ENABLED")
    api_key: str | None = _read_secret(env_name="OPENAI_API_KEY")
    model: str = (
        _config_str(("llm", "model"), "gpt-4o-mini", "LLM_MODEL") or "gpt-4o-mini"
    )
    max_tokens: int = _config_int(("llm", "max_tokens"), 2500, "LLM_MAX_TOKENS") or 2500
    temperature: float = float(
        _config_str(("llm", "temperature"), "0.3", "LLM_TEMPERATURE") or "0.3"
    )
    timeout_secs: int = (
        _config_int(("llm", "timeout_secs"), 30, "LLM_TIMEOUT_SECS") or 30
    )
    retry_attempts: int = (
        _config_int(("llm", "retry_attempts"), 2, "LLM_RETRY_ATTEMPTS") or 2
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
    llm_config: LLMConfig = Field(default_factory=LLMConfig)


@lru_cache(maxsize=1)
def get_settings() -> Config:
    return Config()
