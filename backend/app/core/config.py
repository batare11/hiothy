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
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    auth_token_secret: str = ""
    auth_token_expire_days: int = 30
    glm_ocr_api_key: str = ""
    glm_ocr_endpoint: str = "https://open.bigmodel.cn/api/paas/v4/layout_parsing"
    glm_ocr_model: str = "glm-ocr"
    glm_ocr_structured_model: str = ""
    glm_ocr_timeout: int = 60
    glm_ocr_public_base_url: str = ""
    doubao_api_key: str = ""
    doubao_endpoint: str = (
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    )
    doubao_model: str = ""
    doubao_timeout: int = 60
    deepseek_api_key: str = ""
    deepseek_endpoint: str = "https://api.deepseek.com/chat/completions"
    deepseek_timeout: int = 120
    ocr_auto_min_confidence: float = 0.85
    ocr_temp_dir: str = "uploads/ocr-temp"
    ocr_temp_file_ttl: int = 300

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
