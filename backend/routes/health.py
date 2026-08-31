"""Service health endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report API availability without depending on pipeline services."""
    return {"status": "ok", "service": "depthwizard-api"}
