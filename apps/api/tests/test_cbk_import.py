import pytest

from app.services.cbk_dcp import parse_directory_text
from app.services.cbk_import import SourceParseError, validate_cbk_records
from app.services.sources import SourceDefinition


def _source(expected: int) -> SourceDefinition:
    return SourceDefinition(
        id="cbk_dcp",
        regulator="CBK",
        url="https://www.centralbank.go.ke/example.pdf",
        parser="cbk_dcp_pdf_v1",
        expected_record_count=expected,
    )


def test_cbk_import_enforces_manifest_record_count() -> None:
    records = parse_directory_text(
        "1. Alpha Credit Limited | Alpha | https://alpha.example | a@alpha.example | +254700000001\n"
        "2. Beta Credit Limited | Beta | https://beta.example | b@beta.example | +254700000002"
    )
    assert validate_cbk_records(records, _source(2)) == records
    with pytest.raises(SourceParseError, match="expected 3"):
        validate_cbk_records(records, _source(3))


def test_cbk_import_requires_contiguous_sequence() -> None:
    records = parse_directory_text(
        "1. Alpha Credit Limited | Alpha | https://alpha.example | a@alpha.example | +254700000001\n"
        "3. Gamma Credit Limited | Gamma | https://gamma.example | g@gamma.example | +254700000003"
    )
    with pytest.raises(SourceParseError, match="sequence"):
        validate_cbk_records(records, _source(2))
