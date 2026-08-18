from typing import Annotated

from fastapi import Header, HTTPException, status

LocalActionHeader = Annotated[str | None, Header(alias="X-KDR-Local-Action")]


def _require(expected: str, value: str | None) -> str:
    if value != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="explicit local action header required",
        )
    return value


def require_local_action(x_kdr_local_action: LocalActionHeader = None) -> str:
    return _require("sync", x_kdr_local_action)


def require_reconcile_action(x_kdr_local_action: LocalActionHeader = None) -> str:
    return _require("reconcile", x_kdr_local_action)
