from typing import Annotated

from fastapi import Header, HTTPException, status


def require_local_action(
    x_kdr_local_action: Annotated[str | None, Header(alias="X-KDR-Local-Action")] = None,
) -> str:
    if x_kdr_local_action != "sync":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="explicit local action header required",
        )
    return x_kdr_local_action
