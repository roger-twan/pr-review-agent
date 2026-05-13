from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_app_id: str = Field(alias="GITHUB_APP_ID")
    github_webhook_secret: str = Field(alias="GITHUB_WEBHOOK_SECRET")
    github_private_key: str | None = Field(default=None, alias="GITHUB_PRIVATE_KEY")
    github_private_key_path: str | None = Field(default=None, alias="GITHUB_PRIVATE_KEY_PATH")
    github_api_url: str = Field(default="https://api.github.com", alias="GITHUB_API_URL")

    llm_provider: str = Field(default="deepseek", alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")

    server_public_url: str | None = Field(default=None, alias="SERVER_PUBLIC_URL")
    review_max_diff_chars: int = Field(default=60000, alias="REVIEW_MAX_DIFF_CHARS")
    request_timeout_seconds: float = Field(default=45.0, alias="REQUEST_TIMEOUT_SECONDS")
    dry_run: bool = Field(default=False, alias="DRY_RUN")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("github_api_url", "deepseek_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def private_key(self) -> str:
        if self.github_private_key:
            return self.github_private_key.replace("\\n", "\n")
        if self.github_private_key_path:
            return Path(self.github_private_key_path).read_text(encoding="utf-8")
        raise ValueError("Set GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
