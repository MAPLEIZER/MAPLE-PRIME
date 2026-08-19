from io import BytesIO

from pypdf import PdfWriter

from app.services.brs_evidence import extract_brs_claims, store_brs_pdf


def test_brs_text_extraction_keeps_company_identity_but_not_private_owner_details() -> None:
    claims = extract_brs_claims(
        """
        BUSINESS REGISTRATION SERVICE
        Company Name: EXAMPLE CREDIT LIMITED
        Registration Number: PVT-ABC123
        Application Number: BRS-2026-000123
        BENEFICIAL OWNERSHIP OFFICIAL SEARCH
        John Example 0712345678 ID 12345678
        """
    )
    assert claims["company_name"] == "EXAMPLE CREDIT LIMITED"
    assert claims["registration_number"] == "PVT-ABC123"
    assert claims["application_number"] == "BRS-2026-000123"
    assert claims["beneficial_ownership_document"] is True
    assert "John Example" not in str(claims)
    assert "12345678" not in str(claims)


def test_brs_upload_is_content_addressed_and_starts_unverified(tmp_path) -> None:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(stream)
    stored = store_brs_pdf(
        stream.getvalue(),
        document_type="brs_cr12",
        storage_root=tmp_path,
    )
    assert stored.sha256
    assert stored.storage_path.exists()
    assert stored.storage_path.name == f"{stored.sha256}.pdf"
    assert stored.verification_state == "uploaded_unverified"
