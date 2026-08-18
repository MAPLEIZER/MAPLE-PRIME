from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_api_container_migrates_before_serving_and_runs_non_root() -> None:
    dockerfile = _read("apps/api/Dockerfile")
    entrypoint = _read("apps/api/docker-entrypoint.sh")
    assert "COPY alembic.ini" in dockerfile
    assert "COPY migrations" in dockerfile
    assert "USER kdr" in dockerfile
    assert "alembic upgrade head" in entrypoint
    assert "exec uvicorn" in entrypoint


def test_web_container_uses_ci_node_major_and_non_root_runtime() -> None:
    dockerfile = _read("apps/web/Dockerfile")
    nginx = _read("apps/web/nginx.conf")
    assert "node:24" in dockerfile
    assert "vite.config.ts" in dockerfile
    assert "USER nginx" in dockerfile
    assert "location /api/" in nginx
    assert "proxy_pass http://api:8000" in nginx


def test_compose_is_local_only_by_default() -> None:
    compose = _read("deploy/docker-compose/compose.yaml")
    assert '"127.0.0.1:8000:8000"' in compose
    assert '"127.0.0.1:8080:8080"' in compose
    assert "read_only: true" in compose
    assert "KDR_SOURCE_MANIFEST" in compose
    assert "KDR_SNAPSHOT_DIR" in compose
    assert "source-manifest.yaml:/config/source-manifest.yaml:ro" in compose
