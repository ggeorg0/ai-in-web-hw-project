import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from ..config import REDIS_URL, TRITON_HTTP_URL, VLLM_URL
from ..database import engine
from ..schemas import HealthResponse

logger = logging.getLogger("grocery_helper.health")

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    checks: dict[str, str] = {}
    status_code = 200

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"
        status_code = 503

    try:
        redis = Redis.from_url(REDIS_URL)
        pong = await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok" if pong else "error"
    except Exception:
        checks["redis"] = "error"
        status_code = 503

    checks["triton"] = "not_configured"
    if TRITON_HTTP_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{TRITON_HTTP_URL}/v2/health/ready", timeout=2.0)
                checks["triton"] = "ok" if resp.status_code == 200 else "error"
        except Exception:
            checks["triton"] = "error"
            status_code = 503

    checks["vllm"] = "not_configured"
    if VLLM_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{VLLM_URL}/health", timeout=2.0)
                checks["vllm"] = "ok" if resp.status_code == 200 else "error"
        except Exception:
            checks["vllm"] = "error"
            status_code = 503

    all_ok = all(v == "ok" for k, v in checks.items() if v != "not_configured")
    checks["status"] = "healthy" if all_ok else "degraded"

    if status_code == 503:
        return JSONResponse(status_code=503, content=checks)
    return checks


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}
