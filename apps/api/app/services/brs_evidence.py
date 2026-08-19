from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

MAX_BRS_PDF_BYTES = 10 * 1024 * 1024
VALID_BRS_DOCUMENT_TYPES = frozenset({"brs_cr12", "brs_beneficial_ownership_search"})


@dataclass(frozen=True)
class StoredBRSFile:
    sha256: str
    storage_path: Path
    verification_state: str = "uploaded_unverified"


def _capture(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip(" :.-")[:300] or None


def extract_brs_claims(text: str) -> dict[str, object]:
    # Deliberately extract organization/document identifiers only. Beneficial-owner
    # names, national IDs, phone numbers and addresses stay inside the local PDF
    # and are not copied into public/queryable structured fields by default.
    return {
        "company_name": _capture(r"(?:company|entity)\s*name\s*[:\-]\s*([^\r\n]+)", text),
        "registration_number": _capture(
            r"(?:company\s+)?registration\s*(?:number|no\.?|#)\s*[:\-]\s*([^\r\n]+)",
            text,
        ),
        "application_number": _capture(
            r"application\s*(?:number|no\.?|#)\s*[:\-]\s*([^\r\n]+)", text
        ),
        "beneficial_ownership_document": "beneficial ownership" in text.casefold(),
    }


def extract_pdf_text(data: bytes) -> tuple[str, int]:
    reader = PdfReader(BytesIO(data), strict=True)
    parts = [(page.extract_text() or "") for page in reader.pages[:100]]
    return "\n".join(parts), len(reader.pages)


def store_brs_pdf(
    data: bytes,
    *,
    document_type: str,
    storage_root: Path,
) -> StoredBRSFile:
    if document_type not in VALID_BRS_DOCUMENT_TYPES:
        raise ValueError("unsupported BRS document type")
    if not data or len(data) > MAX_BRS_PDF_BYTES:
        raise ValueError("BRS PDF must be between 1 byte and 10 MB")
    if not data.startswith(b"%PDF-"):
        raise ValueError("BRS evidence upload must be a PDF")
    sha256 = hashlib.sha256(data).hexdigest()
    directory = storage_root / "uploads" / "brs"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / f"{sha256}.pdf"
    if not target.exists():
        target.write_bytes(data)
        target.chmod(0o600)
    return StoredBRSFile(sha256=sha256, storage_path=target)
