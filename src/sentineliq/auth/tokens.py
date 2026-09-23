from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from sentineliq.config import get_settings


def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    expires_minutes: int = 60,
) -> str:
    settings = get_settings()

    if settings.jwt_secret_key is None:
        raise RuntimeError("SENTINELIQ_JWT_SECRET_KEY is required")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
