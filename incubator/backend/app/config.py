from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    anthropic_api_key: str = ""
    generated_apps_dir: str = "~/generated-apps"
    database_url: str = "sqlite+aiosqlite:///./incubator.db"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def generated_apps_path(self) -> Path:
        return Path(self.generated_apps_dir).expanduser()


settings = Settings()
