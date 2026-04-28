import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str = ""
    generated_apps_dir: str = "~/generated-apps"
    database_url: str = "sqlite+aiosqlite:///./incubator.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def generated_apps_path(self) -> Path:
        return Path(self.generated_apps_dir).expanduser()


settings = Settings()

# Forward Langfuse keys to os.environ so langfuse SDK auto-discovers them.
# pydantic-settings reads .env but does not populate os.environ.
if settings.langfuse_public_key:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
if settings.langfuse_secret_key:
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
