from pathlib import Path

from kdr_installer.provider_config import configure_play_provider, read_runtime_settings
from kdr_installer.pairing import generate_pairing_token, write_runtime_env


def test_serpapi_configuration_is_saved_locally_and_pairing_preserves_it(tmp_path: Path) -> None:
    path = configure_play_provider(tmp_path, provider="serpapi", api_key="serp-secret")
    assert path == tmp_path / ".kdr" / "runtime.env"
    settings = read_runtime_settings(tmp_path)
    assert settings["KDR_PLAY_DISCOVERY_PROVIDER"] == "serpapi"
    assert settings["KDR_SERPAPI_API_KEY"] == "serp-secret"

    token = generate_pairing_token()
    write_runtime_env(tmp_path, token=token, telemetry_enabled=True)
    settings = read_runtime_settings(tmp_path)
    assert settings["KDR_SERPAPI_API_KEY"] == "serp-secret"
    assert settings["KDR_MOBILE_API_TOKEN"] == token


def test_talordata_and_serpapi_credentials_can_coexist_for_provider_switching(tmp_path: Path) -> None:
    configure_play_provider(tmp_path, provider="talordata", api_key="sk-talor-secret")
    configure_play_provider(tmp_path, provider="serpapi", api_key="serp-secret")
    settings = read_runtime_settings(tmp_path)
    assert settings["KDR_PLAY_DISCOVERY_PROVIDER"] == "serpapi"
    assert settings["KDR_TALORDATA_API_KEY"] == "sk-talor-secret"
    assert settings["KDR_SERPAPI_API_KEY"] == "serp-secret"

    configure_play_provider(tmp_path, provider="talordata", api_key="sk-talor-secret")
    settings = read_runtime_settings(tmp_path)
    assert settings["KDR_PLAY_DISCOVERY_PROVIDER"] == "talordata"
    assert settings["KDR_TALORDATA_API_KEY"] == "sk-talor-secret"
    assert settings["KDR_SERPAPI_API_KEY"] == "serp-secret"


def test_public_provider_changes_selection_without_destroying_saved_provider_credentials(tmp_path: Path) -> None:
    configure_play_provider(tmp_path, provider="serpapi", api_key="serp-secret")
    configure_play_provider(tmp_path, provider="public_html", api_key=None)
    settings = read_runtime_settings(tmp_path)
    assert settings["KDR_PLAY_DISCOVERY_PROVIDER"] == "public_html"
    assert settings["KDR_SERPAPI_API_KEY"] == "serp-secret"
