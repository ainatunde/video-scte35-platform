from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://scte35:scte35pass@postgres:5432/scte35db"
    redis_url: str = "redis://redis:6379/0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:80"]
    log_level: str = "INFO"
    output_base_dir: str = "/data/hls"


settings = Settings()
