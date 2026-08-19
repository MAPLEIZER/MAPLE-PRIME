from app.services.cbk_dcp import parse_directory_text


def test_cbk_parser_handles_official_multiline_record_format() -> None:
    text = """
CENTRAL BANK OF KENYA
DIRECTORY OF DIGITAL CREDIT PROVIDERS
UPDATED ON JULY 9, 2026
1. Abito Limited
Postal Address: P.O. Box 67450 - 00100, Nairobi
Telephone: +254753536473
Email: abitozfin@gmail.com
Physical Address: Garden Estate Quinox Room A01, Alozi Estate Road, Nairobi
Date Licensed: September 2, 2025
2. Ambush Capital Limited trading under FlashPesa
Postal Address: P.O. Box 52800, Nairobi
Telephone: +254769159474
Email: support@flashpesa.co.ke
Physical Address: Unit 1302, 13th Floor, Applewood Adams, Ngong Road, Nairobi
Date Licensed: October 1, 2024
"""
    records = parse_directory_text(text)
    assert len(records) == 2
    assert records[0].sequence == 1
    assert records[0].legal_name == "Abito Limited"
    assert records[0].postal_address == "P.O. Box 67450 - 00100, Nairobi"
    assert records[0].emails == ("abitozfin@gmail.com",)
    assert records[0].licensed_date == "September 2, 2025"
    assert records[1].legal_name == "Ambush Capital Limited"
    assert records[1].trading_name == "FlashPesa"


def test_cbk_parser_handles_field_variants_and_continuations() -> None:
    text = """
10. Aleza Limited
Postal Address: P.O Box 2382– 40100, Kisumu
E-mail address: alezalimited@gmail.com
Telephone: +254716517065
Physical Address: Pioneer Hse 2nd Floor, Oginga Odinga Street, Kisumu
Date Licensed: December 24, 2025
11. Amaze Credit Limited
Postal Address: P.O. Box 13234-00400, Nairobi
E-mail address: amaze25c@gmail.com/info@amazecreditlimited.com
Telephone No: +2542022613869 / +254721726845
Physical Address: Motorworld centre, Jogoo road
near city stadium.
Date Licensed: April 10, 2026
"""
    records = parse_directory_text(text)
    assert records[0].emails == ("alezalimited@gmail.com",)
    assert records[1].emails == (
        "amaze25c@gmail.com",
        "info@amazecreditlimited.com",
    )
    assert "+2542022613869" in records[1].phones
    assert "near city stadium" in (records[1].physical_address or "")
