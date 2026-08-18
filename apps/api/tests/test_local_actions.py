import pytest
from fastapi import HTTPException

from app.api.local_actions import require_local_action
from app.services.sources import SourceDefinition, SourceManifest, find_source


def test_local_action_guard_requires_explicit_header_value() -> None:
    with pytest.raises(HTTPException) as exc:
        require_local_action(None)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException):
        require_local_action("delete")

    assert require_local_action("sync") == "sync"


def test_source_lookup_is_explicit_and_rejects_unknown_ids() -> None:
    manifest = SourceManifest(
        sources=[
            SourceDefinition(
                id="cbk_dcp",
                regulator="CBK",
                url="https://www.centralbank.go.ke/example.pdf",
                parser="cbk_dcp_pdf_v1",
            )
        ]
    )
    assert find_source(manifest, "cbk_dcp").regulator == "CBK"
    with pytest.raises(KeyError):
        find_source(manifest, "not-real")
