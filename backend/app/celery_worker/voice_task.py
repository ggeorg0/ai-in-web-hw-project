import asyncio
import json
import logging
import time
from io import BytesIO
from uuid import UUID

import numpy as np
from pydub import AudioSegment
from redis.asyncio import Redis
from sqlalchemy import select

from ..config import REDIS_URL
from ..database import async_session, engine
from ..models import Task
from ..services.triton_client import call_triton_asr
from ..services.vllm_client import call_vllm_extract
from .celery_app import celery_app

logger = logging.getLogger("grocery_helper.worker")


@celery_app.task(bind=True, max_retries=0)
def process_voice(self, task_id: str, audio_path: str) -> dict:
    return asyncio.run(_process_voice_async(task_id, audio_path))


async def _process_voice_async(task_id: str, audio_path: str) -> dict:
    redis = Redis.from_url(REDIS_URL)
    t_start = time.monotonic()
    try:
        async with async_session() as session:
            try:
                await _set_task_status(task_id, "processing", session, redis)

                t_read = time.monotonic()
                audio = _read_audio(audio_path)
                logger.info("task=%s read_audio %.1fms", task_id, (time.monotonic() - t_read) * 1000)

                t_asr = time.monotonic()
                text = await call_triton_asr(audio)
                logger.info("task=%s asr %.1fms text=%s", task_id, (time.monotonic() - t_asr) * 1000, text[:200] if text else "<empty>")

                if not text or not text.strip():
                    await _set_task_status(task_id, "failed", session, redis, error="Unable to recognize speech")
                    logger.warning("task=%s asr_empty", task_id)
                    return {"status": "failed", "error": "Unable to recognize speech"}

                t_llm = time.monotonic()
                products = await call_vllm_extract(text)
                logger.info("task=%s vllm %.1fms products=%s", task_id, (time.monotonic() - t_llm) * 1000, products)

                if not products:
                    await _set_task_status(task_id, "failed", session, redis, error="No products found")
                    logger.warning("task=%s no_products", task_id)
                    return {"status": "failed", "error": "No products found"}

                await _set_task_status(task_id, "completed", session, redis, text=text, products=products)
                logger.info("task=%s completed total=%.1fms", task_id, (time.monotonic() - t_start) * 1000)
                return {"status": "completed", "text": text, "products": products}

            except Exception as exc:
                logger.exception("task=%s processing_error", task_id)
                await _set_task_status(task_id, "failed", session, redis, error=f"Processing error: {exc}")
                return {"status": "failed", "error": str(exc)}
    finally:
        await redis.aclose()
        await engine.dispose()


def _read_audio(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        raw = f.read()
    audio = AudioSegment.from_file(BytesIO(raw))
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0
    return samples


async def _set_task_status(
    task_id: str,
    status: str,
    session,
    redis: Redis,
    text: str | None = None,
    products: list[str] | None = None,
    error: str | None = None,
) -> None:
    tid = UUID(task_id)
    result = await session.execute(select(Task).where(Task.id == tid))
    task = result.scalar_one_or_none()
    if task:
        task.status = status
        if text is not None:
            task.audio_text = text
        if products is not None:
            task.extracted_products = products
        if error is not None:
            task.error = error
        await session.commit()

    payload: dict = {"status": status}
    if text is not None:
        payload["text"] = text
        payload["products"] = products
    if error is not None:
        payload["error"] = error
    await redis.publish(f"task_status:{task_id}", json.dumps(payload))