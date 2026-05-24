import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/grocery_helper"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TRITON_GRPC_URL = os.getenv("TRITON_GRPC_URL", "localhost:8001")
VLLM_URL = os.getenv("VLLM_URL", "http://localhost:9000")
DATA_DIR = os.getenv("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
