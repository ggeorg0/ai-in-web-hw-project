# Grocery Helper — Agent Instructions

**Status:** Backend, Nginx, Frontend, Monitoring, and ML services fully implemented (FastAPI + Celery worker + React + reverse proxy + Prometheus + Grafana). HA features (replicas, load balancing, graceful shutdown) configured. Telegram bot not yet implemented — remaining section below is the implementation blueprint.

**What exists:**
- `GigaAM/` — git submodule with ASR model & Triton conversion scripts
- `docker-compose.yml` — 12 services: `asr-init`, `triton`, `vllm`, `postgres`, `redis`, `nginx`, `backend` (×2 replicas), `celery-worker` (×2 replicas), `frontend`, `prometheus`, `grafana`; two isolated networks: `frontend_net` + `backend_net`
- `frontend/` — React SPA (Vite + Ant Design)
  - `frontend/src/App.jsx` — conditional render: Login vs MainScreen
  - `frontend/src/Login.jsx` — registration form, calls `POST /api/users/register`, stores `user_id` in `localStorage`
  - `frontend/src/MainScreen.jsx` — "Talk" button (MediaRecorder API), polls `GET /api/tasks/{task_id}/status`, shopping list display
  - `frontend/src/api.js` — fetch wrappers for all API endpoints
  - `frontend/Dockerfile` — multi-stage build (Vite → nginx serving on `:3000`)
  - No router, no undo popups (simplified from design spec); uses polling instead of WebSocket (browsers can't set custom headers on WS)
- `backend/` — FastAPI application package
  - `backend/app/main.py` — FastAPI app with CORS, lifespan (DB init + engine dispose), SIGTERM graceful shutdown handler, logging middleware (request method/path/status/duration), `@app.exception_handler` for `RequestValidationError` (422) and unhandled `Exception` (500), `/metrics` endpoint
  - `backend/app/routers/` — REST endpoints: `users`, `tasks`, `lists`, `ws`, `health`
    - `health.py` — `GET /health` (probes DB/Redis/Triton/vLLM, returns 200 or 503), `GET /healthz` (liveness)
  - `backend/app/celery_worker/` — Celery app + `process_voice` task (Triton ASR → vLLM extraction)
    - `celery_app.py` — `task_acks_late=True`, `worker_prefetch_multiplier=1` for graceful shutdown
    - `voice_task.py` — per-stage timing logs (read_audio, asr, vllm, total ms)
  - `backend/app/services/` — `triton_client.py` (gRPC via `tritonclient[grpc]`), `vllm_client.py` (OpenAI Python client, few-shot prompt)
  - `backend/app/models.py` — SQLAlchemy ORM: `User`, `ShoppingList`, `ListItem`, `Task`
  - `backend/app/database.py` — Async engine + session + `get_db` dependency
  - `backend/app/config.py` — env-var settings (`DATABASE_URL`, `REDIS_URL`, `TRITON_GRPC_URL`, `TRITON_HTTP_URL`, `VLLM_URL`, `DATA_DIR`, `LOG_LEVEL`)
  - `backend/app/schemas.py` — Pydantic v2 schemas with `Field(min_length, max_length, description, examples)` on all models
  - `backend/app/dependencies.py` — `get_current_user` (validates `X-User-ID` header)
  - `backend/pyproject.toml` — `uv`-managed deps: fastapi, celery, sqlalchemy, asyncpg, redis, httpx, tritonclient[grpc]>=2.68, openai>=1.0, prometheus-fastapi-instrumentator, etc.
  - `backend/Dockerfile` — API server (uvicorn on `:8000`)
  - `backend/Dockerfile.worker` — Celery worker with `--concurrency=1` (ensures task completion before shutdown)
  - `backend/tests/` — 34 pytest tests (32 pass, 2 skipped). In-process via `httpx.ASGITransport`, async SQLAlchemy with per-test schema reset. Includes mock + real integration tests for Triton (gRPC) and vLLM (OpenAI client), with `example.wav` test fixture.
  - `backend/alembic/` — initial 001 migration + `env.py` for async migrations
- `data/` — shared bind mount for audio files between `backend` and `celery-worker`
- `nginx/nginx.conf` — reverse proxy: rate-limited `/api/` → `backend:8000`, `/ws/` with WebSocket upgrade → `backend:8000`, `/grafana/` → `grafana:3000` (sub-path), `/` → `frontend:3000` (runtime DNS via `resolver 127.0.0.11`; variable-based proxy_pass provides DNS round-robin load balancing for backend replicas)
- `monitoring/` — Prometheus scrape config + Grafana dashboard JSON (5 panels: RPS, p50/p95 latency, status codes, endpoint table, latency heatmap). Grafana accessible at `http://localhost:3001` or `http://localhost/grafana/` (admin/admin)
- `asr-init/Dockerfile` + `entrypoint.sh` — GPU model conversion container
- `triton/Dockerfile` — Triton server container
- `common/install-asr-deps.sh` — shared pip dependency script

**Network architecture:**
```
frontend_net (10.10.0.0/16):   nginx → frontend, backend, grafana
backend_net  (10.20.0.0/16):   backend → postgres, redis, celery-worker, triton, vllm, asr-init, prometheus, grafana
```
- UI and Proxy cannot reach Redis/Postgres/Celery — backend is the sole bridge
- Backend on both networks as API gateway
- Grafana on both networks (scraped by Prometheus internally, dashboard served via nginx)

**Graceful shutdown:**
- Backend: SIGTERM handler sets `_shutting_down` flag; middleware returns 503 for new requests; in-flight requests complete within `stop_grace_period: 30s`
- Celery-worker: `task_acks_late=True`, `worker_prefetch_multiplier=1`, `--concurrency=1` — finishes current task, acks only on success, `stop_grace_period: 120s`

**Docker Compose resource limits:**
- Backend: `mem_limit: 512m`, `cpus: 0.5`
- Celery-worker: `mem_limit: 2g`, `cpus: 1.0`

**Health checks:**
- All 12 services have `healthcheck` blocks with `interval`/`timeout`/`retries`
- `depends_on` uses `condition: service_healthy` or `service_completed_successfully` throughout
- `/health` endpoint probes DB (`SELECT 1`), Redis (`PING`), Triton (`/v2/health/ready`), vLLM (`/health`); returns 503 if any critical component fails

**Python conventions:**
- Use `uv` for package management (not pip, not poetry)
- Use modern Python typing (`list[str]` over `List[str]`, `|` for unions, `type[X]` over `Type[X]`)
- Keep all imports at the top of the file
- **Do not install system-wide packages (apt, apk, etc.) without asking the user first and getting an explicit answer**

**Testing:**
- Run tests with `uv run pytest tests/ -v` from the `backend/` directory
- Requires PostgreSQL on `localhost:5432` (start with `docker run -d --name test-pg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16`)
- Tests use `httpx.ASGITransport` (no running server needed, in-process)
- Each test gets a clean database (per-function `drop_all` + `create_all`)
- Redis, Triton, vLLM are not required for the test suite

**Design sections below** define the full architecture (FastAPI + Celery + React + Telegram bot + Triton + vLLM + Nginx + Redis + PostgreSQL, all Docker Compose). Use them as the implementation blueprint.

---

# Voice-Powered Shopping List Application – System Specification

## 1. Introduction
This system enables users to create and manage a shopping list using voice input. A spoken phrase is transcribed, and grocery items are extracted and normalized to their dictionary form (lemma). The result can be viewed via a web interface (React) or through a Telegram bot. All services run inside Docker containers orchestrated by Docker Compose.

## 2. High-Level Architecture
- **Nginx** – Single entry point, reverse proxy, rate limiting.
- **FastAPI Backend** – Core REST API, asynchronous task management, WebSocket notifications.
- **Celery Worker** – Handles audio processing (ASR + LLM extraction) asynchronously.
- **Redis** – Celery broker and result backend, Pub/Sub for task status updates, caching.
- **PostgreSQL** – Persistent storage for users, shopping lists, and items.
- **asr-init** – One-shot container that prepares the GigaAM v3 model for the specific GPU: downloads, converts to ONNX FP16, then to TensorRT.
- **Triton Inference Server** – Serves the GigaAM v3 TensorRT model with built-in audio preprocessing.
- **vLLM** – Serves the Qwen3-0.6B LLM with structured output for product extraction and lemmatization.
- **React Frontend** – Minimal UI using ready-made component libraries.
- **Telegram Bot** – Receives voice messages, presents extracted products with inline confirmation buttons.
- **Prometheus & Grafana** – Metrics collection and dashboard.

## 3. Component Details

### 3.1 Nginx
- Listens on ports 80/443.
- Proxies `/api/*` to `backend:8000`, `/grafana/` to `grafana:3000`, all other requests to `frontend:3000`.
- Rate limiting: zone `api_limit` – 60 requests per minute per IP for `/api/` endpoints.
- Passes client real IP via `X-Real-IP` and `X-Forwarded-For` headers.
- DNS round-robin load balancing via `resolver 127.0.0.11` with variable-based `proxy_pass` — each request independently resolves `backend` through Docker embedded DNS.

### 3.2 FastAPI Backend
- Uses SQLAlchemy asynchronous ORM; Alembic for database migrations.
- Does **not** directly interact with the database – all access through the ORM.
- **Authentication** (MVP): clients identify with a `X-User-ID` header obtained from the registration/login endpoint.
- **Endpoints**:
  - `POST /api/users/register` – Accepts `{"username": "..."}`, returns `{"user_id": "uuid"}`.
  - `POST /api/tasks/voice` – Accepts an audio file (multipart/form-data), creates a Celery task, returns `{"task_id": "uuid"}`.
  - `GET /api/lists` – Returns the current shopping list for the authenticated user.
  - `POST /api/lists/items` – Adds an item to the list. Request body: `{"product_name": "string"}`. Returns 409 Conflict if the product already exists in the list.
  - `DELETE /api/lists/items/{item_id}` – Removes an item.
  - `GET /health` – Probes DB, Redis, Triton, vLLM. Returns 200 or 503 with per-component status.
  - `GET /healthz` – Simple liveness check.
- **WebSocket**:
  - `WS /ws/tasks/{task_id}` – Server sends JSON status updates (`status: "processing"/"completed"/"failed"`, result payload). Uses Redis Pub/Sub internally.
- **Error handling**: Custom `@app.exception_handler` for `RequestValidationError` (422) and unhandled `Exception` (500).
- **Graceful shutdown**: SIGTERM handler sets shutdown flag; middleware returns 503 for new requests; in-flight requests complete within `stop_grace_period`.
- **Request logging**: Middleware logs method, path, status code, and duration in ms for every request.

### 3.3 Celery Worker
- Executes the `process_voice(task_id, audio_bytes)` task:
  1. Sends audio to Triton for ASR (GigaAM v3). If the result text is empty (silence/noise), transitions task to `failed` with error `"Unable to recognize speech"`.
  2. Sends transcribed text to vLLM with a structured output schema to extract and lemmatize product names. If the returned list is empty, transitions to `failed` with error `"No products found"`.
  3. On success, publishes the result (original text, list of lemmatized products) to Redis channel `task_status:{task_id}` and stores the final task state.
- The task is idempotent: re-running with the same `task_id` does not cause duplicate processing or side effects.
- **Logging**: Per-stage timing logs (read_audio, ASR, vLLM, total) in milliseconds.
- **Graceful shutdown**: `task_acks_late=True`, `worker_prefetch_multiplier=1`, `--concurrency=1` — worker finishes current task before stopping.

### 3.4 Redis
- Acts as message broker and result backend for Celery.
- Implements Pub/Sub: channel `task_status:{task_id}` where Celery publishes updates. Backend WebSocket handler and Telegram bot subscribe to this channel.
- Stores a set of processed Telegram callback keys: `processed_callback:{task_id}:{product_name}` with a TTL of 24 hours to enforce idempotency.
- Data persisted via Docker named volume `redis_data`.

### 3.5 PostgreSQL
- Tables (managed by Alembic):
  - `users` – `id UUID PRIMARY KEY`, `username VARCHAR`, `created_at TIMESTAMP`.
  - `shopping_lists` – `id SERIAL PRIMARY KEY`, `user_id UUID REFERENCES users(id) UNIQUE`, `created_at TIMESTAMP`. (Each user has exactly one active shopping list.)
  - `list_items` – `id SERIAL PRIMARY KEY`, `list_id INTEGER REFERENCES shopping_lists(id) ON DELETE CASCADE`, `product_name VARCHAR NOT NULL`, `added_at TIMESTAMP DEFAULT NOW()`, `source VARCHAR (voice/manual)`. A unique constraint `UNIQUE(list_id, product_name)` prevents duplicate product names (lemmatized) within a single list.
- `product_name` always stores the normalized lemma form.

### 3.6 Triton Inference Server
- Serves the GigaAM v3 Automatic Speech Recognition model in TensorRT format.
- The model repository contains `model.plan` (TensorRT engine) pre-built by the `asr-init` container.
- Audio preprocessing is handled **inside Triton**: a Python backend accepts flat audio buffer + lengths, runs feature extraction (PyTorch, FP16), and feeds the tensor to the ASR model.
- Built from `triton/Dockerfile` (`nvcr.io/nvidia/tritonserver:26.04-py3`), Python deps via `common/install-asr-deps.sh`.
- Exposes HTTP/gRPC endpoints on ports 8000/8001/8002.
- Mounts `./converted-models:/models` for the model repository and `./GigaAM:/opt/gigaam_repo:ro` (for `gigaam` package, via `PYTHONPATH`).

### 3.7 vLLM
- Serves the Qwen3-0.6B model with structured output enabled (JSON mode).
- Backend calls vLLM via the OpenAI Python client (`openai.AsyncOpenAI`) with `base_url=f"{VLLM_URL}/v1"`.
- The prompt includes few-shot examples for lemmatization:
  - Plural→singular, case normalization (помидоры→помидор, пачку масла→масло).
  - Edge case: empty result when no products detected (`"сегодня хорошая погода"`).
- Required JSON schema:
  ```json
  {
    "type": "object",
    "properties": {
      "products": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["products"]
  }
  ```
- Returns `{"products": ["огурец", "помидор"]}` (lemmatized strings). If no products are detected, returns `{"products": []}`.

### 3.8 React Frontend *(implemented)*
- Built with Vite + Ant Design.
- **Registration/Login**: username form → `POST /api/users/register`, stores `user_id` in `localStorage`.
- **Main screen**:
  - "Talk" button records audio via `MediaRecorder` API.
  - Sends audio to `POST /api/tasks/voice` with `X-User-ID` header.
  - Polls `GET /api/tasks/{task_id}/status` every 1s (up to 60s) — **not WebSocket** (browsers can't set `X-User-ID` on native WebSocket).
- **On task completion**:
  - If **successful**: extracted products are auto-added via `POST /api/lists/items`. Duplicates (409) silently skipped. No undo popups.
  - If **failed**: error message displayed, "Talk" button re-enabled.
- Shopping list displayed with per-item delete button.
- No router — conditional render based on `localStorage.user_id`.
- Dockerfile: multi-stage (Vite build → nginx on `:3000`).

### 3.9 Telegram Bot
- Implemented with `python-telegram-bot`.
- Receives voice messages:
  1. Downloads the audio file, sends it to `POST /api/tasks/voice` (header `X-User-ID: telegram_{user_id}`).
  2. Subscribes to Redis channel `task_status:{task_id}`.
  3. Awaits task completion.
- **On success**:
  - Sends the user a message with the transcription and extracted products.
  - Attaches an inline keyboard: for each product, buttons "➕ Add" and "❌ Reject". Callback data encodes `task_id` and `product_name`.
- **Callback handling**:
  - Checks Redis for idempotency key (`processed_callback:{task_id}:{product_name}`). If already processed, answers with a brief alert.
  - For "Add": calls `POST /api/lists/items`. If the product is already in the list (409 Conflict), the bot informs the user "Already in list".
  - For "Reject": does nothing, just acknowledges.
  - After all products are processed, the bot updates the message with the final list (or the user can use `/list`).
- **Commands**:
  - `/start` – Welcome message and instructions.
  - `/list` or `/ls` – Shows the current shopping list.

### 3.10 asr-init Container
- **Purpose**: Convert the GigaAM v3 model to a TensorRT engine optimized for the specific GPU in the deployment environment.
- **Lifecycle**:
  - Container runs once (`restart: "no"`) and executes a shell script.
  - Steps:
    1. Check if `model.plan` exists in the shared volume (`/models`). If yes, exit successfully.
    2. If not, check for the original model checkpoint; download if missing.
    3. If no `.onnx` file exists, export the model to ONNX with FP16 precision.
    4. Run `trtexec` to build the TensorRT engine (`--fp16 --memPoolSize=workspace:3072`) and save `model.plan` into the model repository volume.
    5. Exit with code 0.
- **Runtime environment**: Needs NVIDIA GPU access (nvidia-container-runtime) and includes tools like PyTorch, ONNX export utilities, and TensorRT.
- The container uses the same shared bind mount as Triton (`converted-models/`).

### 3.11 Prometheus & Grafana *(implemented)*
- Prometheus collects:
  - FastAPI metrics via `prometheus-fastapi-instrumentator` (requests per second, latency, error rates).
- Grafana dashboard: 5 panels for API RPS, p50/p95 latency, status codes per endpoint, endpoint latency table, latency heatmap.
- Accessible at `http://localhost:3001` (direct) or `http://localhost/grafana/` (via nginx, sub-path).
- Credentials: `admin` / `admin`.

## 4. Use Cases

### 4.1 Use Case 1: Web Interface (React)
1. User opens the application, enters a username, obtains a `user_id` (stored in browser).
2. Clicks "Talk" and speaks a phrase (e.g., "Привет, мне нужно купить помидоры и огурцы").
3. Audio is sent to the backend; a Celery task is created.
4. The frontend polls `GET /api/tasks/{task_id}/status` every second until completion.
5. On success, the extracted lemmatized products are auto-added to the shopping list (409 duplicates silently skipped).
6. On failure, an error message is displayed, and the user can try again.

### 4.2 Use Case 2: Telegram Bot
1. User sends a voice message to the bot.
2. Bot downloads the audio, submits it to the API, and subscribes to the task's Redis channel.
3. Once the result is ready, the bot shows the transcription and extracted products with inline "Add"/"Reject" buttons.
4. The user taps buttons; the bot calls the API accordingly, ensuring idempotency.
5. After processing all items, the bot can display the updated list using `/list`.

## 5. API Contract (Summary)

| Method   | Endpoint                    | Description |
|----------|-----------------------------|-------------|
| POST     | `/api/users/register`       | Register/login, returns `user_id`. |
| POST     | `/api/tasks/voice`          | Upload audio, returns `task_id`. |
| WS       | `/ws/tasks/{task_id}`       | WebSocket for task status updates. |
| GET      | `/api/lists`                | Get current shopping list. |
| POST     | `/api/lists/items`          | Add a product (409 if duplicate). |
| DELETE   | `/api/lists/items/{item_id}`| Remove a product. |
| GET      | `/api/tasks/{task_id}/status`| Polling endpoint for status. |
| GET      | `/health`                   | Component-level health probes (DB, Redis, Triton, vLLM). |
| GET      | `/healthz`                  | Simple liveness check. |

All endpoints except `/api/users/register`, `/health`, and `/healthz` require the `X-User-ID` header.

## 6. Data Model

```
users
  id UUID PK
  username VARCHAR
  created_at TIMESTAMP

shopping_lists
  id SERIAL PK
  user_id UUID FK (unique)
  created_at TIMESTAMP

list_items
  id SERIAL PK
  list_id INTEGER FK
  product_name VARCHAR
  added_at TIMESTAMP
  source VARCHAR
  UNIQUE(list_id, product_name)

tasks
  id UUID PK
  user_id UUID FK
  status VARCHAR (pending/processing/completed/failed)
  audio_text TEXT
  extracted_products JSONB
  error TEXT
  created_at TIMESTAMP
```

## 7. Security & Constraints
- Nginx enforces rate limit of 60 requests per minute per IP on `/api/`.
- All inter-service communication occurs over the internal Docker network; only Nginx and the Telegram bot (optional webhook) are exposed externally.
- Two isolated networks: `frontend_net` (nginx, frontend, backend, grafana) and `backend_net` (backend, postgres, redis, celery-worker, triton, vllm, asr-init, prometheus, grafana). Frontend and Nginx cannot reach Redis/Postgres/Celery directly.
- The TensorRT engine is GPU-specific; changing the GPU model requires deleting the `converted-models` directory and re-running `asr-init`.

## 9. Monitoring
- FastAPI metrics exposed at `/metrics` via `prometheus-fastapi-instrumentator`.
- A Grafana dashboard is provided with key panels: overall RPS, endpoint latency, Celery task throughput, and task failure rate (ASR/LLM errors).
- Grafana accessible at `http://localhost:3001` (direct) or `http://localhost/grafana/` (via nginx). Credentials: `admin`/`admin`.
