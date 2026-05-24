from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models import ListItem, ShoppingList, User
from ..schemas import ListItemCreate, ListItemResponse, ShoppingListResponse

router = APIRouter(prefix="/api/lists", tags=["lists"])


async def _get_or_create_shopping_list(user: User, db: AsyncSession) -> ShoppingList:
    result = await db.execute(select(ShoppingList).where(ShoppingList.user_id == user.id))
    shopping_list = result.scalar_one_or_none()
    if shopping_list is None:
        shopping_list = ShoppingList(user_id=user.id)
        db.add(shopping_list)
        await db.commit()
    return shopping_list


@router.get("", response_model=ShoppingListResponse)
async def get_list(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShoppingListResponse:
    shopping_list = await _get_or_create_shopping_list(user, db)

    result = await db.execute(
        select(ListItem)
        .where(ListItem.list_id == shopping_list.id)
        .order_by(ListItem.added_at.desc())
    )
    items = result.scalars().all()

    return ShoppingListResponse(
        list_id=shopping_list.id,
        items=[ListItemResponse.model_validate(item) for item in items],
    )


@router.post("/items", status_code=201, response_model=ListItemResponse)
async def add_item(
    body: ListItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListItemResponse:
    shopping_list = await _get_or_create_shopping_list(user, db)

    existing = await db.execute(
        select(ListItem).where(
            ListItem.list_id == shopping_list.id,
            ListItem.product_name == body.product_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Product already in list")

    item = ListItem(
        list_id=shopping_list.id,
        product_name=body.product_name,
        source="manual",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return ListItemResponse.model_validate(item)


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    result = await db.execute(
        select(ListItem)
        .join(ShoppingList)
        .where(ListItem.id == item_id, ShoppingList.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()
    return {"ok": True}
