from pathlib import Path


def test_compose_passes_mobile_pairing_settings_without_exposing_api_directly() -> None:
    root = Path(__file__).resolve().parents[3]
    compose = (root / "deploy" / "docker-compose" / "compose.yaml").read_text()

    assert "KDR_MOBILE_API_TOKEN" in compose
    assert "KDR_MOBILE_TELEMETRY_ENABLED" in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert '"127.0.0.1:8080:8080"' in compose
