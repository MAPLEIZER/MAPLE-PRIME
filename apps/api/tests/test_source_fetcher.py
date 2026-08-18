import httpx
import pytest

from app.services.fetcher import SourceFetchError, fetch_source
from app.services.sources import SourceDefinition


def _source(url: str = "https://www.centralbank.go.ke/example.pdf") -> SourceDefinition:
    return SourceDefinition(
        id="cbk_dcp",
        regulator="CBK",
        url=url,
        parser="cbk_dcp_pdf_v1",
        update_policy="manual",
        expected_record_count=252,
    )


def test_fetcher_rejects_hosts_outside_reviewed_allowlist() -> None:
    with pytest.raises(SourceFetchError, match="approved"):
        fetch_source(
            _source("https://example.org/data.pdf"),
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x")),
        )


def test_fetcher_does_not_follow_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.org/redirect"})

    with pytest.raises(SourceFetchError, match="redirect"):
        fetch_source(_source(), transport=httpx.MockTransport(handler))


def test_fetcher_limits_response_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"0123456789")

    with pytest.raises(SourceFetchError, match="size"):
        fetch_source(_source(), transport=httpx.MockTransport(handler), max_bytes=5)


def test_fetcher_returns_bytes_and_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"].startswith("KenyaDataRights/")
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"pdf")

    fetched = fetch_source(_source(), transport=httpx.MockTransport(handler))
    assert fetched.body == b"pdf"
    assert fetched.media_type == "application/pdf"
    assert fetched.source_id == "cbk_dcp"
