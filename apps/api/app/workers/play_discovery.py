from __future__ import annotations

import os
import time

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.services.play_discovery_provider import run_configured_play_discovery


def main() -> None:
    interval = max(3600, int(os.environ.get("KDR_PLAY_DISCOVERY_INTERVAL_SECONDS", "86400")))
    providers = max(1, min(50, int(os.environ.get("KDR_PLAY_DISCOVERY_PROVIDERS_PER_RUN", "25"))))
    apps = max(1, min(200, int(os.environ.get("KDR_PLAY_DISCOVERY_MAX_APPS", "100"))))
    while True:
        try:
            with Session(get_engine()) as session:
                result = run_configured_play_discovery(
                    session,
                    max_providers=providers,
                    max_apps=apps,
                )
                session.commit()
                print(
                    "KDR Play discovery: "
                    f"provider={result.provider} providers={result.providers_considered} "
                    f"apps={result.apps_ingested} candidates={result.ownership_candidates} "
                    f"failures={len(result.failures)}",
                    flush=True,
                )
        except Exception as exc:
            print(f"KDR Play discovery run failed: {type(exc).__name__}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
