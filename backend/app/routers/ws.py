import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy import select

from ..config import REDIS_URL
from ..database import async_session
from ..models import User

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str) -> None:
    x_user_id = websocket.headers.get("X-User-ID")
    if not x_user_id:
        await websocket.close(code=4001, reason="X-User-ID header required")
        return
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid X-User-ID format")
        return

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        if not result.scalar_one_or_none():
            await websocket.close(code=4001, reason="User not found")
            return

    await websocket.accept()

    redis = Redis.from_url(REDIS_URL)
    pubsub = redis.pubsub()
    channel = f"task_status:{task_id}"
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.close()
