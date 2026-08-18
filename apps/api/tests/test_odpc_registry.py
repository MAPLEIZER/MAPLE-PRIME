from app.services.odpc_registry import parse_registered_handlers_html


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


def test_odpc_registry_parser_fails_on_unrecognized_table() -> None:
    try:
        parse_registered_handlers_html("<html><body>No registry table</body></html>")
    except ValueError as exc:
        assert "registry" in str(exc).lower()
    else:
        raise AssertionError("missing registry table must fail loudly")
