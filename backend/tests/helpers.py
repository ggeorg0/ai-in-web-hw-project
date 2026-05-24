from httpx import AsyncClient


async def register_user(client: AsyncClient, username: str) -> str:
    r = await client.post("/api/users/register", json={"username": username})
    assert r.status_code == 200
    return r.json()["user_id"]