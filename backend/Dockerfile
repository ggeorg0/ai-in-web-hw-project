FROM python:3.12-slim

WORKDIR /app/backend

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app/ ./app/
RUN uv sync --frozen --no-dev && uv cache clean && find . -name '__pycache__' -type d -exec rm -rf {} +

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
