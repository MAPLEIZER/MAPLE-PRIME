from app.api.play_discovery import _diagnostic_failures


def test_recognized_key_reframes_search_rejection_as_permission_issue() -> None:
    warnings = _diagnostic_failures(
        ("SerpApi rejected the configured API key",),
        {
            "key_valid": True,
            "account_status": "Active",
            "searches_left": 200,
        },
    )

    assert len(warnings) == 1
    assert "recognizes this key" in warnings[0]
    assert "permission/account restriction" in warnings[0]
    assert "Active" in warnings[0]


def test_unverified_key_keeps_original_provider_warning() -> None:
    warning = "SerpApi rejected the configured API key"
    assert _diagnostic_failures((warning,), None) == [warning]
