import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/executor_balancer"
    redis_url: str = "redis://localhost:6379/0"
    prometheus_port: int = 8001
    api_title: str = "Executor Balancer API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
