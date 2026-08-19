from app.services.odpc_registry import OdpcRegistryAccessRestricted, parse_registered_handlers_html


def test_odpc_registry_parser_preserves_controller_processor_rows() -> None:
    html = """
<table><thead><tr><th>#</th><th>Name</th><th>Data Handler Type</th><th>Registration number</th><th>County</th><th>Country</th><th>Status</th><th>Status as at</th></tr></thead>
<tbody>
<tr><td>1</td><td>Example Credit Limited</td><td>Data Controller</td><td>INST-ABC123</td><td>NAIROBI</td><td>Kenya</td><td>Active/Renewed</td><td>7/9/2026</td></tr>
<tr><td>2</td><td>Example Credit Limited</td><td>Data Processor</td><td>INST-ABC123</td><td>NAIROBI</td><td>Kenya</td><td>Active/Renewed</td><td>7/9/2026</td></tr>
</tbody></table>
"""
    rows = parse_registered_handlers_html(html)
    assert len(rows) == 2
    assert rows[0].name == "Example Credit Limited"
    assert rows[0].handler_type == "Data Controller"
    assert rows[1].handler_type == "Data Processor"
    assert rows[0].registration_number == "INST-ABC123"
    assert rows[0].status == "Active/Renewed"


def test_odpc_registry_parser_finds_schema_after_title_row() -> None:
    html = """
<table>
<thead>
<tr><th colspan="8">REGISTRATION STATUS OF DATA HANDLERS</th></tr>
<tr><th>\ufeff#</th><th>Name</th><th>Data Handler Type</th><th>Registration Number</th><th>County</th><th>Country</th><th>Status</th><th>Status as at</th></tr>
</thead>
<tbody>
<tr><td>1</td><td>10AGROW TECHNOLOGIES LIMITED</td><td>Data Processor</td><td>INST-838411BDBEA</td><td>NAIROBI</td><td>Kenya</td><td>Active/Renewed</td><td>7/9/2026</td></tr>
<tr><td>2</td><td>1ST RONGAI PEDIATRIC CLINIC</td><td>Data Controller</td><td>INST-62521354D9F</td><td>NAIROBI</td><td>Kenya</td><td>Active</td><td>7/9/2026</td></tr>
</tbody>
</table>
"""
    rows = parse_registered_handlers_html(html)
    assert [row.sequence for row in rows] == [1, 2]
    assert rows[0].registration_number == "INST-838411BDBEA"
    assert rows[1].handler_type == "Data Controller"


def test_odpc_registry_parser_accepts_common_header_punctuation() -> None:
    html = """
<table>
<tr><th>No.</th><th>Organisation Name</th><th>Data Handler Type</th><th>Registration No.</th><th>County</th><th>Country</th><th>Status</th><th>Status As At</th></tr>
<tr><td>9</td><td>Example Limited</td><td>Data Controller</td><td>INST-123ABC</td><td>NAIROBI</td><td>Kenya</td><td>Active</td><td>7/9/2026</td></tr>
</table>
"""
    rows = parse_registered_handlers_html(html)
    assert len(rows) == 1
    assert rows[0].sequence == 9
    assert rows[0].name == "Example Limited"
    assert rows[0].registration_number == "INST-123ABC"


def test_odpc_registry_parser_classifies_browser_challenge_separately() -> None:
    html = """
<html><head><title>Checking your browser</title></head>
<body>Verify you are human. Enable JavaScript and cookies to continue.</body></html>
"""
    try:
        parse_registered_handlers_html(html)
    except OdpcRegistryAccessRestricted:
        pass
    else:
        raise AssertionError("ODPC browser challenge must be classified as access restricted")


def test_odpc_registry_parser_fails_on_unrecognized_table() -> None:
    try:
        parse_registered_handlers_html("<html><body>No registry table</body></html>")
    except ValueError as exc:
        assert "registry" in str(exc).lower()
    else:
        raise AssertionError("missing registry table must fail loudly")
