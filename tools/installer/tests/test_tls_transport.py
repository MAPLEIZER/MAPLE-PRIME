import ssl
import urllib.request

from kdr_installer.network import trusted_https_context, trusted_urlopen


def test_trusted_https_context_requires_certificate_validation() -> None:
    context = trusted_https_context()
    assert context.verify_mode is ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.get_ca_certs()


def test_trusted_urlopen_supplies_explicit_ssl_context(monkeypatch) -> None:
    captured = {}

    class DummyResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, *, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return DummyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    request = urllib.request.Request("https://api.github.com/")
    with trusted_urlopen(request, timeout=7) as response:
        assert response.status == 200

    assert captured["timeout"] == 7
    assert captured["context"].verify_mode is ssl.CERT_REQUIRED
    assert captured["context"].check_hostname is True
