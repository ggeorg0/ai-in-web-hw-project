from celery import Celery

from ..config import REDIS_URL

celery_app = Celery(
    "grocery_helper",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.celery_worker.voice_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
