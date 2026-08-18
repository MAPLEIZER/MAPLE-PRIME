from pathlib import Path

from app.services.cbk_dcp import parse_directory_text
from app.services.snapshot_store import SnapshotStore


def test_snapshot_store_is_content_addressed_and_immutable(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    first = store.put(
        source_id="cbk_dcp",
        body=b"same source bytes",
        media_type="application/pdf",
        retrieved_at="2026-08-18T06:00:00Z",
    )
    second = store.put(
        source_id="cbk_dcp",
        body=b"same source bytes",
        media_type="application/pdf",
        retrieved_at="2026-08-18T07:00:00Z",
    )
    assert first.sha256 == second.sha256
    assert first.content_path == second.content_path
    assert first.content_path.read_bytes() == b"same source bytes"


def test_cbk_directory_text_parser_extracts_contact_fields() -> None:
    fixture = """
    DIRECTORY OF DIGITAL CREDIT PROVIDERS
    1. Example Credit Limited | Example Credit | https://example.co.ke | privacy@example.co.ke | +254700000001
    2. Another Finance Ltd. | Another App | https://another.example | info@another.example | +254700000002
    """
    records = parse_directory_text(fixture)
    assert len(records) == 2
    assert records[0].legal_name == "Example Credit Limited"
    assert records[0].trading_name == "Example Credit"
    assert records[0].emails == ("privacy@example.co.ke",)
    assert records[0].phones == ("+254700000001",)


def test_cbk_directory_parser_ignores_headers_but_rejects_empty_result() -> None:
    try:
        parse_directory_text("DIRECTORY OF DIGITAL CREDIT PROVIDERS\nNo parseable rows")
    except ValueError as exc:
        assert "no dcp records" in str(exc).lower()
    else:
        raise AssertionError("empty parse must fail loudly")
