import asyncio
import json
import wave
from uuid import UUID

import numpy as np
from redis.asyncio import Redis
from sqlalchemy import select

from ..config import REDIS_URL
from ..database import async_session
from ..models import Task
from ..services.triton_client import call_triton_asr
from ..services.vllm_client import call_vllm_extract
from .celery_app import celery_app


@celery_app.task(bind=True, max_retries=0)
def process_voice(self, task_id: str, audio_path: str) -> dict:
    return asyncio.run(_process_voice_async(task_id, audio_path))


async def _process_voice_async(task_id: str, audio_path: str) -> dict:
    try:
        await _publish_status(task_id, "processing")

        audio = _read_wav(audio_path)
        text = await call_triton_asr(audio)

        if not text or not text.strip():
            await _mark_task_failed(task_id, "Unable to recognize speech")
            return {"status": "failed", "error": "Unable to recognize speech"}

        products = await call_vllm_extract(text)

        if not products:
            await _mark_task_failed(task_id, "No products found")
            return {"status": "failed", "error": "No products found"}

        await _mark_task_completed(task_id, text, products)
        return {"status": "completed", "text": text, "products": products}

    except Exception as exc:
        await _mark_task_failed(task_id, f"Processing error: {exc}")
        return {"status": "failed", "error": str(exc)}


def _read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return audio


async def _publish_status(task_id: str, status: str) -> None:
    async with async_session() as session:
        tid = UUID(task_id)
        result = await session.execute(select(Task).where(Task.id == tid))
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            await session.commit()

    redis = Redis.from_url(REDIS_URL)
    await redis.publish(f"task_status:{task_id}", json.dumps({"status": status}))
    await redis.close()


async def _mark_task_failed(task_id: str, error: str) -> None:
    async with async_session() as session:
        tid = UUID(task_id)
        result = await session.execute(select(Task).where(Task.id == tid))
        task = result.scalar_one_or_none()
        if task:
            task.status = "failed"
            task.error = error
            await session.commit()

    redis = Redis.from_url(REDIS_URL)
    await redis.publish(
        f"task_status:{task_id}",
        json.dumps({"status": "failed", "error": error}),
    )
    await redis.close()


async def _mark_task_completed(task_id: str, text: str, products: list[str]) -> None:
    async with async_session() as session:
        tid = UUID(task_id)
        result = await session.execute(select(Task).where(Task.id == tid))
        task = result.scalar_one_or_none()
        if task:
            task.status = "completed"
            task.audio_text = text
            task.extracted_products = products
            await session.commit()

    redis = Redis.from_url(REDIS_URL)
    await redis.publish(
        f"task_status:{task_id}",
        json.dumps({"status": "completed", "text": text, "products": products}),
    )
    await redis.close()
