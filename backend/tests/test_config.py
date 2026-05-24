from app.config import DATABASE_URL, REDIS_URL, TRITON_GRPC_URL, VLLM_URL, DATA_DIR, PROJECT_ROOT


def test_database_url_has_postgres():
    assert "postgresql+asyncpg" in DATABASE_URL


def test_redis_url_starts_with_redis():
    assert REDIS_URL.startswith("redis://")


def test_triton_grpc_url_default():
    assert TRITON_GRPC_URL.endswith(":8001")


def test_vllm_url_default():
    assert VLLM_URL.startswith("http://")


def test_project_root_is_absolute():
    assert PROJECT_ROOT.startswith("/")


def test_data_dir_is_under_project_root():
    assert DATA_DIR.startswith(PROJECT_ROOT)