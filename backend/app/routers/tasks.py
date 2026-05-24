import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import DATA_DIR
from ..database import get_db
from ..dependencies import get_current_user
from ..models import Task, User
from ..schemas import TaskResponse, TaskStatusResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/voice", response_model=TaskResponse)
async def submit_voice_task(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    task = Task(user_id=user.id, status="pending")
    db.add(task)
    await db.flush()

    audios_dir = os.path.join(DATA_DIR, "audios")
    os.makedirs(audios_dir, exist_ok=True)
    audio_path = os.path.join(audios_dir, f"{task.id}.wav")

    content = await file.read()
    with open(audio_path, "wb") as f:
        f.write(content)

    await db.commit()

    from ..celery_worker.voice_task import process_voice

    process_voice.delay(str(task.id), audio_path)

    return TaskResponse(task_id=task.id, status="pending")


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskStatusResponse:
    try:
        tid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id") from None

    result = await db.execute(select(Task).where(Task.id == tid))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        audio_text=task.audio_text,
        extracted_products=task.extracted_products,
        error=task.error,
    )
