from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import User


async def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header required")
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID format")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
