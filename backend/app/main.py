import logging
import signal
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .config import LOG_LEVEL
from .database import engine
from .models import Base
from .routers import health, lists, tasks, users, ws

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("grocery_helper")

_shutting_down = False


def _handle_sigterm(signum: int, _frame) -> None:
    global _shutting_down
    logger.warning("Received %s, initiating graceful shutdown", signal.Signals(signum).name)
    _shutting_down = True


signal.signal(signal.SIGTERM, _handle_sigterm)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Disposing database engine")
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_and_shutdown_middleware(request: Request, call_next) -> Response:
    if _shutting_down:
        return JSONResponse(status_code=503, content={"detail": "Server is shutting down"})

    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info("%s %s %d %.1fms", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.warning("Validation error: %s", errors)
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(lists.router)
app.include_router(ws.router)
app.include_router(health.router)

Instrumentator().instrument(app).expose(app)