from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.services.cbk_dcp import DcpDirectoryRecord, parse_directory_text
from app.services.sources import SourceDefinition


class SourceParseError(ValueError):
    pass


def extract_pdf_text(body: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(body), strict=False)
        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:  # pypdf exposes multiple parser exception types
        raise SourceParseError(f"unable to extract PDF text: {exc}") from exc
    text = "\n".join(part for part in page_text if part)
    if not text.strip():
        raise SourceParseError("PDF contained no extractable text")
    return text


def validate_cbk_records(
    records: list[DcpDirectoryRecord], source: SourceDefinition
) -> list[DcpDirectoryRecord]:
    sequences = [record.sequence for record in records]
    expected_sequence = list(range(1, len(records) + 1))
    if sequences != expected_sequence:
        raise SourceParseError(
            "CBK DCP record sequence is not contiguous from 1; parser/source review required"
        )
    if source.expected_record_count is not None and len(records) != source.expected_record_count:
        raise SourceParseError(
            f"CBK DCP source expected {source.expected_record_count} records but parsed {len(records)}"
        )
    return records


def parse_cbk_pdf(body: bytes, source: SourceDefinition) -> list[DcpDirectoryRecord]:
    return validate_cbk_records(parse_directory_text(extract_pdf_text(body)), source)
