import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db
from app.models import Base

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/grocery_helper_test"
ADMIN_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

_db_created = False


async def _ensure_test_db():
    global _db_created
    if _db_created:
        return
    admin_engine = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'grocery_helper_test'")
        )
        if result.scalar():
            await conn.execute(text("DROP DATABASE grocery_helper_test"))
        await conn.execute(text("CREATE DATABASE grocery_helper_test"))
    await admin_engine.dispose()
    _db_created = True


@pytest_asyncio.fixture
async def engine():
    await _ensure_test_db()
    test_engine = create_async_engine(TEST_DB_URL)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session = async_sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    await session.rollback()
    await session.close()


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
