from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # Auth
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    admin_username: str = "admin"
    admin_password_hash: str = "$2b$12$placeholder_hash_change_in_env"

    # Redis / RQ
    redis_url: str = "redis://redis:6379"
    rq_queue_name: str = "sim_jobs"

    # Paths
    outputs_dir: Path = Path("/app/outputs")
    simulator_root: Path = Path("/app/simulator")

    # CORS origins (comma-separated)
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
