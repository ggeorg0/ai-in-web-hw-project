import uuid

import pytest


async def test_no_header_returns_401(client):
    r = await client.get("/api/lists")
    assert r.status_code == 401


async def test_invalid_uuid_returns_401(client):
    r = await client.get("/api/lists", headers={"X-User-ID": "not-a-uuid"})
    assert r.status_code == 401


async def test_unknown_user_returns_401(client):
    unknown_id = str(uuid.uuid4())
    r = await client.get("/api/lists", headers={"X-User-ID": unknown_id})
    assert r.status_code == 401