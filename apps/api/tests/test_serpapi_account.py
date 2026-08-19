import httpx

from app.services.serpapi_account import check_serpapi_account


def _client(status: int, payload: dict[str, object]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_account_health_reports_active_plan_without_exposing_secret() -> None:
    client = _client(
        200,
        {
            "account_id": "private-id",
            "api_key": "secret-key",
            "account_email": "private@example.com",
            "account_status": "Active",
            "plan_name": "Free Plan",
            "plan_renewal_date": "2026-09-03",
            "total_searches_left": 217,
            "this_month_usage": 33,
            "this_hour_searches": 4,
            "account_rate_limit_per_hour": 250,
        },
    )
    health = check_serpapi_account(" secret-key ", client=client)

    assert health["checked"] is True
    assert health["key_valid"] is True
    assert health["account_status"] == "Active"
    assert health["plan_name"] == "Free Plan"
    assert health["searches_left"] == 217
    assert health["this_month_usage"] == 33
    assert health["this_hour_searches"] == 4
    assert health["hourly_limit"] == 250
    assert "api_key" not in health
    assert "account_email" not in health
    assert "account_id" not in health
    assert "secret-key" not in str(health)


def test_account_health_distinguishes_invalid_key_from_forbidden_account() -> None:
    invalid = check_serpapi_account(
        "secret-key",
        client=_client(401, {"error": "Invalid API key: secret-key"}),
    )
    forbidden = check_serpapi_account(
        "secret-key",
        client=_client(403, {"error": "Account does not have permission"}),
    )

    assert invalid["key_valid"] is False
    assert "invalid" in str(invalid["error"]).lower()
    assert forbidden["key_valid"] is True
    assert forbidden["account_status"] == "Forbidden"
    assert "permission" in str(forbidden["error"]).lower()
    assert "secret-key" not in str(invalid)
    assert "secret-key" not in str(forbidden)


def test_account_health_reports_quota_or_throughput_separately() -> None:
    limited = check_serpapi_account(
        "secret-key",
        client=_client(429, {"error": "Your account has run out of searches."}),
    )

    assert limited["key_valid"] is True
    assert limited["searches_left"] == 0
    assert "searches" in str(limited["error"]).lower()


def test_account_health_handles_missing_key_without_network() -> None:
    health = check_serpapi_account(None)
    assert health["checked"] is False
    assert health["key_valid"] is False
    assert "not configured" in str(health["error"]).lower()
