from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://scte35:scte35pass@postgres:5432/scte35db"
    redis_url: str = "redis://redis:6379/0"
    output_base_dir: str = "/data/hls"
    detection_sample_fps: float = 2.0
    scte35_cooldown_seconds: float = 30.0
    log_level: str = "INFO"


settings = WorkerSettings()
