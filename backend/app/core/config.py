"""从环境变量读取应用配置。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hiothy Blood Pressure API"
    app_env: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 5000
    api_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://blood_pressure:CHANGE_ME"
        "@127.0.0.1:5432/blood_pressure"
    )
    allowed_origins: str = "https://hiothy.cn"
    max_upload_mb: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.allowed_origins.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
