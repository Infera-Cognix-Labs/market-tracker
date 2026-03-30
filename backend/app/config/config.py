from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class MongoDBConfig(BaseModel):
    host: str = os.getenv("MONGO_HOST")
    port: int = int(os.getenv("MONGO_PORT", 27017))
    username: str = os.getenv("MONGO_USERNAME")
    password: str = os.getenv("MONGO_PASSWORD")


class ApifyConfig(BaseModel):
    token: str = os.getenv("APIFY_TOKEN")


class Config(BaseModel):
    mongodb_config: MongoDBConfig = MongoDBConfig()
    apify_config: ApifyConfig = ApifyConfig()
