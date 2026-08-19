#!/usr/bin/env python3
"""Normalize public Google Play scraper/API exports into KDR's import contract.

This tool performs no scraping itself. It accepts JSON exported from a third-party
collector or a user-owned script, maps common field names, and emits the stable
`POST /api/v1/apps/import/play` payload expected by KDR.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "package_name": ("package_name", "packageName", "appId", "app_id", "package", "id"),
    "app_name": ("app_name", "appName", "title", "name"),
    "developer_name": ("developer_name", "developerName", "developer", "seller", "publisher"),
    "developer_id": ("developer_id", "developerId", "developer_id_text", "publisherId"),
    "support_email": ("support_email", "developerEmail", "developer_email", "email", "supportEmail"),
    "developer_website": ("developer_website", "developerWebsite", "developer_url", "website", "developerUrl"),
    "privacy_policy_url": ("privacy_policy_url", "privacyPolicy", "privacyPolicyUrl", "privacy_policy"),
    "store_url": ("store_url", "url", "playUrl", "play_url", "appUrl"),
    "category": ("category", "genre", "genreId", "primaryGenre"),
    "installs": ("installs", "realInstalls", "downloads", "downloadCount"),
}


def first_value(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return None


def rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ("records", "results", "items", "apps", "data"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                rows = candidate
                break
        if rows is None:
            rows = [payload]
    else:
        raise ValueError("input JSON must be an object or array")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("every app record must be a JSON object")
    return rows


def clean_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    text = str(value).strip()
    return text or None


def package_from_store_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    package = parse_qs(parsed.query).get("id", [None])[0]
    return clean_string(package)


def normalize_email(value: Any) -> str | None:
    text = clean_string(value)
    return text.lower() if text else None


def normalize_row(
    row: dict[str, Any],
    *,
    source_provider: str,
    source_url: str | None,
    observed_at: str,
    row_number: int,
) -> dict[str, Any]:
    store_url = clean_string(first_value(row, FIELD_ALIASES["store_url"]))
    package_name = clean_string(first_value(row, FIELD_ALIASES["package_name"])) or package_from_store_url(store_url)
    if not package_name:
        raise ValueError(f"row {row_number}: package identity is missing")
    if not store_url:
        store_url = f"https://play.google.com/store/apps/details?id={package_name}"

    app_name = clean_string(first_value(row, FIELD_ALIASES["app_name"]))
    developer_name = clean_string(first_value(row, FIELD_ALIASES["developer_name"]))
    if not app_name:
        raise ValueError(f"row {row_number}: app name is missing for {package_name}")
    if not developer_name:
        raise ValueError(f"row {row_number}: developer name is missing for {package_name}")

    provenance_url = source_url or store_url
    parsed = urlparse(provenance_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"row {row_number}: source URL must be HTTPS")

    return {
        "store": "google_play",
        "package_name": package_name,
        "app_name": app_name,
        "developer_name": developer_name,
        "developer_id": clean_string(first_value(row, FIELD_ALIASES["developer_id"])),
        "support_email": normalize_email(first_value(row, FIELD_ALIASES["support_email"])),
        "developer_website": clean_string(first_value(row, FIELD_ALIASES["developer_website"])),
        "privacy_policy_url": clean_string(first_value(row, FIELD_ALIASES["privacy_policy_url"])),
        "store_url": store_url,
        "category": clean_string(first_value(row, FIELD_ALIASES["category"])),
        "installs": clean_string(first_value(row, FIELD_ALIASES["installs"])),
        "source_provider": source_provider,
        "source_url": provenance_url,
        "observed_at": observed_at,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a public Google Play metadata JSON export for Kenya Data Rights."
    )
    parser.add_argument("input", type=Path, help="JSON export from a scraper/API or local collector")
    parser.add_argument("--source-provider", required=True, help="Collector/provider label, e.g. apify, serpapi, local")
    parser.add_argument("--source-url", help="HTTPS URL identifying the export/run. Defaults to each Play listing URL.")
    parser.add_argument(
        "--observed-at",
        help="ISO-8601 observation time. Defaults to current UTC time.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        rows = rows_from_payload(payload)
        observed_at = args.observed_at or datetime.now(UTC).isoformat()
        # Validate an explicitly supplied observation time before copying it to all records.
        datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        records = [
            normalize_row(
                row,
                source_provider=args.source_provider.strip(),
                source_url=args.source_url,
                observed_at=observed_at,
                row_number=index,
            )
            for index, row in enumerate(rows, start=1)
        ]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Play export normalization failed: {exc}", file=sys.stderr)
        return 2

    json.dump({"records": records}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
