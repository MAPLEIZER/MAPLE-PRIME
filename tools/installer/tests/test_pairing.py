from pathlib import Path

from kdr_installer.pairing import (
    build_runtime_env,
    generate_pairing_token,
    tailscale_serve_args,
    write_runtime_env,
)


def test_pairing_token_is_high_entropy_urlsafe_secret() -> None:
    first = generate_pairing_token()
    second = generate_pairing_token()
    assert first != second
    assert len(first) >= 40
    assert all(ch.isalnum() or ch in "-_" for ch in first)


def test_runtime_env_enables_telemetry_without_leaking_other_environment(tmp_path: Path) -> None:
    token = generate_pairing_token()
    text = build_runtime_env(token=token, telemetry_enabled=True)
    assert "KDR_MOBILE_TELEMETRY_ENABLED=true" in text
    assert f"KDR_MOBILE_API_TOKEN={token}" in text
    assert "PASSWORD=" not in text

    path = write_runtime_env(tmp_path, token=token, telemetry_enabled=True)
    assert path == tmp_path / ".kdr" / "runtime.env"
    assert path.read_text() == text


def test_tailscale_pairing_exposes_only_the_authenticated_mobile_api_path() -> None:
    args = tailscale_serve_args()
    assert args == [
        "tailscale",
        "serve",
        "--bg",
        "--set-path=/api/v1/mobile/",
        "http://127.0.0.1:8000",
    ]
    assert "8080" not in " ".join(args)
