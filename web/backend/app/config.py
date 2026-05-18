from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # Auth
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Bootstrap admin (used only on first startup to seed the DB)
    admin_username: str = "admin"
    admin_email: str = "admin@constellasim.com"
    admin_password: str = "CHANGE_ME_ADMIN_PASSWORD"
    # Legacy hash field kept so existing .env files don't break
    admin_password_hash: str = "$2b$12$placeholder_hash_change_in_env"

    # Redis / RQ
    redis_url: str = "redis://redis:6379"
    rq_queue_name: str = "sim_jobs"

    # Paths
    outputs_dir: Path = Path("/app/outputs")
    simulator_root: Path = Path("/app/simulator")

    # App base URL (for invite links)
    app_url: str = "http://localhost"

    # CORS origins (comma-separated)
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
