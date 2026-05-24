import uuid

import pytest

from .helpers import register_user


async def test_get_empty_list(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.get("/api/lists", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert isinstance(data["list_id"], int)


async def test_add_item(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.post("/api/lists/items", headers=headers, json={"product_name": "помидор"})
    assert r.status_code == 201
    data = r.json()
    assert data["product_name"] == "помидор"
    assert data["source"] == "manual"
    assert isinstance(data["id"], int)


async def test_add_duplicate_returns_409(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    await client.post("/api/lists/items", headers=headers, json={"product_name": "хлеб"})
    r = await client.post("/api/lists/items", headers=headers, json={"product_name": "хлеб"})
    assert r.status_code == 409


async def test_get_list_with_items(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    await client.post("/api/lists/items", headers=headers, json={"product_name": "молоко"})
    await client.post("/api/lists/items", headers=headers, json={"product_name": "яйца"})

    r = await client.get("/api/lists", headers=headers)
    assert r.status_code == 200
    data = r.json()
    names = [i["product_name"] for i in data["items"]]
    assert "молоко" in names
    assert "яйца" in names


async def test_delete_item(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    add_r = await client.post("/api/lists/items", headers=headers, json={"product_name": "сыр"})
    item_id = add_r.json()["id"]

    r = await client.delete(f"/api/lists/items/{item_id}", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    list_r = await client.get("/api/lists", headers=headers)
    assert list_r.json()["items"] == []


async def test_delete_nonexistent_item_returns_404(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.delete("/api/lists/items/99999", headers=headers)
    assert r.status_code == 404


async def test_cannot_delete_another_users_item(client):
    alice_id = await register_user(client, "alice")
    bob_id = await register_user(client, "bob")

    alice_headers = {"X-User-ID": alice_id}
    add_r = await client.post("/api/lists/items", headers=alice_headers, json={"product_name": "вино"})
    alice_item_id = add_r.json()["id"]

    bob_headers = {"X-User-ID": bob_id}
    r = await client.delete(f"/api/lists/items/{alice_item_id}", headers=bob_headers)
    assert r.status_code == 404

    list_r = await client.get("/api/lists", headers=alice_headers)
    assert len(list_r.json()["items"]) == 1