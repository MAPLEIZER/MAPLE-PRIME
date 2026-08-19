from __future__ import annotations

from typing import Any

import httpx

_SERPAPI_ACCOUNT_ENDPOINT = "https://serpapi.com/account.json"
_MAX_ERROR_CHARS = 240


def _redact_message(value: object, *, api_key: str) -> str:
    text = str(value or "").strip()
    if api_key:
        text = text.replace(api_key, "<redacted>")
    return text[:_MAX_ERROR_CHARS]


def _response_error(response: httpx.Response, *, api_key: str) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    return _redact_message(error, api_key=api_key) if error else None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def check_serpapi_account(
    api_key: str | None,
    *,
    client: httpx.Client | None = None,
) -> dict[str, object]:
    """Validate a SerpApi key with the free Account API without exposing secrets.

    SerpApi documents the Account API as free of charge and not counted toward
    monthly search quota. KDR only returns operational fields needed for local
    diagnostics; account email, account id, and the API key are deliberately
    omitted.
    """

    key = (api_key or "").strip()
    if not key:
        return {
            "checked": False,
            "key_valid": False,
            "account_status": None,
            "plan_name": None,
            "searches_left": None,
            "this_month_usage": None,
            "this_hour_searches": None,
            "hourly_limit": None,
            "plan_renewal_date": None,
            "error": "SerpApi API key is not configured",
        }

    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        try:
            response = http_client.get(
                _SERPAPI_ACCOUNT_ENDPOINT,
                params={"api_key": key},
                headers={"User-Agent": "KenyaDataRights/0.1 account-health-check"},
                timeout=8.0,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            return {
                "checked": False,
                "key_valid": None,
                "account_status": None,
                "plan_name": None,
                "searches_left": None,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": "SerpApi Account API could not be reached",
            }

        error = _response_error(response, api_key=key)
        if response.status_code == 401:
            return {
                "checked": True,
                "key_valid": False,
                "account_status": None,
                "plan_name": None,
                "searches_left": None,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": error or "SerpApi reports that this API key is invalid",
            }
        if response.status_code == 403:
            return {
                "checked": True,
                "key_valid": True,
                "account_status": "Forbidden",
                "plan_name": None,
                "searches_left": None,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": error or "SerpApi recognized the key but the account is forbidden",
            }
        if response.status_code == 429:
            return {
                "checked": True,
                "key_valid": True,
                "account_status": None,
                "plan_name": None,
                "searches_left": 0,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": error or "SerpApi account quota or throughput limit was reached",
            }
        if response.status_code != 200:
            return {
                "checked": True,
                "key_valid": None,
                "account_status": None,
                "plan_name": None,
                "searches_left": None,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": error or f"SerpApi Account API returned HTTP {response.status_code}",
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "checked": True,
                "key_valid": True,
                "account_status": None,
                "plan_name": None,
                "searches_left": None,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": "SerpApi Account API returned invalid JSON",
            }
        if not isinstance(payload, dict):
            return {
                "checked": True,
                "key_valid": True,
                "account_status": None,
                "plan_name": None,
                "searches_left": None,
                "this_month_usage": None,
                "this_hour_searches": None,
                "hourly_limit": None,
                "plan_renewal_date": None,
                "error": "SerpApi Account API returned an unexpected JSON shape",
            }

        searches_left = payload.get("total_searches_left")
        if searches_left is None:
            searches_left = payload.get("plan_searches_left")
        return {
            "checked": True,
            "key_valid": True,
            "account_status": str(payload.get("account_status") or "").strip() or None,
            "plan_name": str(payload.get("plan_name") or "").strip() or None,
            "searches_left": _int_or_none(searches_left),
            "this_month_usage": _int_or_none(payload.get("this_month_usage")),
            "this_hour_searches": _int_or_none(payload.get("this_hour_searches")),
            "hourly_limit": _int_or_none(payload.get("account_rate_limit_per_hour")),
            "plan_renewal_date": str(payload.get("plan_renewal_date") or "").strip() or None,
            "error": _redact_message(payload.get("error"), api_key=key) or None,
        }
    finally:
        if owns_client:
            http_client.close()
