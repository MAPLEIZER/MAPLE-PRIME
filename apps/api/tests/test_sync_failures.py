from app.services.fetcher import SourceFetchError
from app.services.sync_diagnostics import public_sync_failure


def test_public_sync_failure_preserves_safe_reason_without_internal_exception_text() -> None:
    failure = public_sync_failure(
        "odpc_registered",
        SourceFetchError(
            "403 from upstream with internal transport details that must not leak",
            code="source_access_restricted",
        ),
    )

    assert failure == {
        "source_id": "odpc_registered",
        "code": "source_access_restricted",
        "message": "The official source refused automated access. Retry later or open the official source manually.",
    }
    assert "403" not in failure["message"]


def test_parser_drift_has_a_distinct_safe_failure_code() -> None:
    failure = public_sync_failure("cbk_dcp", ValueError("parser internals"))
    assert failure["source_id"] == "cbk_dcp"
    assert failure["code"] == "source_format_changed"
    assert "parser internals" not in failure["message"]
