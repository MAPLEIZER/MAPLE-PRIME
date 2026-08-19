#!/bin/sh
set -eu

alembic upgrade head

exec uvicorn app.main:app \
  --host "${KDR_CONTAINER_BIND_HOST:-0.0.0.0}" \
  --port "${KDR_BIND_PORT:-8000}"
