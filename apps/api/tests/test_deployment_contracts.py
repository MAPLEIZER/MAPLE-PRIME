from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_api_container_migrates_before_serving_and_runs_non_root() -> None:
    dockerfile = _read("apps/api/Dockerfile")
    entrypoint = _read("apps/api/docker-entrypoint.sh")
    assert "--uid 10001" in dockerfile
    assert "--gid 10001" in dockerfile
    assert "alembic.ini" in dockerfile
    assert "COPY apps/api/migrations" in dockerfile
    assert "requirements-runtime.lock" in dockerfile
    assert "--no-deps ." in dockerfile
    assert "COPY sources/source-manifest.yaml" in dockerfile
    assert "COPY docs/legal" in dockerfile
    assert "COPY docs/public-participation" in dockerfile
    assert "USER kdr" in dockerfile
    assert "alembic upgrade head" in entrypoint
    assert "exec uvicorn" in entrypoint


def test_web_container_uses_ci_node_major_and_non_root_runtime() -> None:
    dockerfile = _read("apps/web/Dockerfile")
    nginx = _read("apps/web/nginx.conf")
    vite = _read("apps/web/vite.config.ts")
    assert "node:24" in dockerfile
    assert "package-lock.json" in dockerfile
    assert "npm ci" in dockerfile
    assert "vite.config.ts" in dockerfile
    assert "USER nginx" in dockerfile
    assert "location /api/" in nginx
    assert "proxy_pass http://api:8000" in nginx
    assert "client_body_temp_path /tmp/client_temp" in nginx
    assert '"/api"' in vite
    assert "http://127.0.0.1:8000" in vite


def test_compose_initializes_owned_runtime_dirs_then_runs_local_only() -> None:
    compose = _read("deploy/docker-compose/compose.yaml")
    assert compose.startswith("name: kenya-data-rights\n")
    assert "api-data-init:" in compose
    assert 'user: "0:0"' in compose
    assert "mkdir -p /data/runtime /data/snapshots" in compose
    assert "chown 10001:10001 /data/runtime /data/snapshots" in compose
    assert "condition: service_completed_successfully" in compose
    assert "sqlite:////data/runtime/kdr.sqlite3" in compose
    assert "KDR_SNAPSHOT_DIR: /data/snapshots" in compose
    assert "KDR_SOURCE_MANIFEST: /app/sources/source-manifest.yaml" in compose
    assert "KDR_LEGAL_LIBRARY_PATH: /app/docs/legal/index.json" in compose
    assert "KDR_CIVIC_REGISTRY_PATH: /app/docs/public-participation/index.json" in compose
    assert "source-manifest.yaml:/config/source-manifest.yaml:ro" not in compose
    assert "../../docs:/docs:ro" not in compose
    assert "context: ../.." in compose
    assert "dockerfile: apps/api/Dockerfile" in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert '"127.0.0.1:8080:8080"' in compose
    assert "read_only: true" in compose


def test_container_ci_checks_api_web_reverse_proxy_and_healthy_selftest_body() -> None:
    workflow = _read(".github/workflows/ci.yml")
    assert "http://127.0.0.1:8000/api/v1/health" in workflow
    assert "http://127.0.0.1:8080/" in workflow
    assert "http://127.0.0.1:8080/api/v1/health" in workflow
    assert "http://127.0.0.1:8080/api/v1/system/self-test" in workflow
    assert 'grep -q \'"ok":true\'' in workflow


def test_docker_build_contexts_exclude_local_secrets_and_runtime_data() -> None:
    root_ignore = _read(".dockerignore")
    web_ignore = _read("apps/web/.dockerignore")
    for required in [".env", "*.sqlite3", "local-data", "evidence", "secrets", ".git", "node_modules"]:
        assert required in root_ignore
    for required in [".env", "node_modules", "dist", "coverage", "test-results"]:
        assert required in web_ignore
