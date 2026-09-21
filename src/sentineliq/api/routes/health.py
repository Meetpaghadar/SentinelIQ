from fastapi import APIRouter

from sentineliq.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "SentinelIQ"}


@router.get("/ready")
def ready() -> dict[str, str]:
    get_settings()
    return {"status": "ready"}
