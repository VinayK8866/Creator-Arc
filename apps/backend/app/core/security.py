from fastapi import Header, HTTPException, status
from app.core.config import settings


def verify_master_password(x_creatorarc_key: str = Header(None, alias="X-CreatorArc-Key")) -> str:
    # If MASTER_PASSWORD is empty or set to default dev value, warn but allow empty on local
    if not settings.MASTER_PASSWORD:
        return ""

    if x_creatorarc_key != settings.MASTER_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid master password"
        )
    return x_creatorarc_key
