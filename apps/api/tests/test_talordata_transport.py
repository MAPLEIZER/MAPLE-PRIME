import httpx
import pytest

from app.services.play_store_discovery import PlayDiscoveryUnavailable
from app.services.talordata_play_discovery import _fetch_talordata_json


def test_talordata_transport_uses_bearer_post_and_form_data() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["authorization"] = request.headers.get("authorization")
        captured["content_type"] = request.headers.get("content-type")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"organic_results": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = _fetch_talordata_json(
            client,
            api_key="sk-secret",
            endpoint="https://api.talordata.com/accounts/v1/serp/get_serp_data",
            payload={"engine": "google_play", "q": "loan", "gl": "ke", "hl": "en"},
        )

    assert payload == {"organic_results": []}
    assert captured["method"] == "POST"
    assert captured["authorization"] == "Bearer sk-secret"
    assert str(captured["content_type"]).startswith("application/x-www-form-urlencoded")
    assert "engine=google_play" in str(captured["body"])
    assert "q=loan" in str(captured["body"])


def test_talordata_transport_does_not_echo_secret_in_auth_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PlayDiscoveryUnavailable) as exc:
            _fetch_talordata_json(
                client,
                api_key="sk-super-secret",
                endpoint="https://api.talordata.com/accounts/v1/serp/get_serp_data",
                payload={"engine": "google_play", "q": "loan"},
            )

    assert "sk-super-secret" not in str(exc.value)
    assert "rejected" in str(exc.value).casefold()
