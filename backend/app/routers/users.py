from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ShoppingList, User
from ..schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=UserResponse)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    result = await db.execute(select(User).where(User.username == body.username))
    if user := result.scalar_one_or_none():
        return UserResponse(user_id=user.id, username=user.username)

    user = User(username=body.username)
    db.add(user)
    await db.flush()

    shopping_list = ShoppingList(user_id=user.id)
    db.add(shopping_list)
    await db.commit()

    return UserResponse(user_id=user.id, username=user.username)
