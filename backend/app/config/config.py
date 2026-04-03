from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


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
    token: str | None = os.getenv("APIFY_TOKEN")


class Config(BaseModel):
    app_name: str = "Market Tracker API"
    api_prefix: str = "/v1"
    seed_demo_data: bool = _env_bool("SEED_DEMO_DATA", True)
    mongodb_config: MongoDBConfig = MongoDBConfig()
    apify_config: ApifyConfig = ApifyConfig()


@lru_cache(maxsize=1)
def get_settings() -> Config:
    return Config()
