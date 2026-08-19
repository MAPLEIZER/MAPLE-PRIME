from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _config(db_url: str) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_alpha_migrations_upgrade_and_downgrade(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'migration.sqlite3'}"
    config = _config(db_url)
    command.upgrade(config, "head")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "institutions",
        "institution_aliases",
        "source_snapshots",
        "source_observations",
        "rights_requests",
        "audit_events",
        "mapping_evidence",
        "reconciliation_findings",
        "mobile_telemetry_events",
        "marketplace_apps",
        "app_store_observations",
        "app_ownership_links",
    } <= tables

    command.downgrade(config, "base")
    remaining = set(inspect(engine).get_table_names())
    assert remaining <= {"alembic_version"}


def test_migrations_honor_runtime_database_url_environment(tmp_path: Path, monkeypatch) -> None:
    configured_url = f"sqlite:///{tmp_path / 'configured.sqlite3'}"
    runtime_url = f"sqlite:///{tmp_path / 'runtime.sqlite3'}"
    monkeypatch.setenv("KDR_DATABASE_URL", runtime_url)

    command.upgrade(_config(configured_url), "head")

    runtime_tables = set(inspect(create_engine(runtime_url)).get_table_names())
    assert "institutions" in runtime_tables
    configured_tables = set(inspect(create_engine(configured_url)).get_table_names())
    assert configured_tables == set()
