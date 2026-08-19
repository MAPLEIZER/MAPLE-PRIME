FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --gid 10001 kdr \
    && useradd --uid 10001 --gid 10001 --home-dir /app --no-create-home --shell /usr/sbin/nologin kdr

COPY apps/api/pyproject.toml apps/api/requirements-runtime.lock apps/api/alembic.ini ./
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/docker-entrypoint.sh /usr/local/bin/kdr-api-entrypoint
COPY sources/source-manifest.yaml ./sources/source-manifest.yaml
COPY docs/legal ./docs/legal
COPY docs/public-participation ./docs/public-participation

RUN pip install --no-cache-dir -r requirements-runtime.lock \
    && pip install --no-cache-dir --no-deps . \
    && chmod 0555 /usr/local/bin/kdr-api-entrypoint \
    && mkdir -p /data \
    && chown -R 10001:10001 /app /data

USER kdr
EXPOSE 8000
ENTRYPOINT ["kdr-api-entrypoint"]
