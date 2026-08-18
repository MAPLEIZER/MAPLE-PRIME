from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def discover_project_root(module_file: Path) -> Path:
    resolved = module_file.resolve()
    for parent in resolved.parents:
        if (parent / "sources" / "source-manifest.yaml").is_file():
            return parent
    if resolved.parent.name == "core" and resolved.parent.parent.name == "app":
        return resolved.parent.parent.parent
    return Path.cwd().resolve()


PROJECT_ROOT = discover_project_root(Path(__file__))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KDR_", env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./kdr.sqlite3"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    allowed_origins: str = "http://localhost:5173"
    vault_master_key: str | None = None
    log_level: str = "INFO"
    source_manifest_path: str = str(PROJECT_ROOT / "sources" / "source-manifest.yaml")
    snapshot_dir: str = str(PROJECT_ROOT / "local-data" / "snapshots")

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
