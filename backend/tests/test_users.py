from .helpers import register_user


async def test_register_new_user(client):
    user_id = await register_user(client, "alice")
    assert isinstance(user_id, str)
    assert len(user_id) == 36


async def test_register_same_username_is_idempotent(client):
    first = await register_user(client, "bob")
    second_r = await client.post("/api/users/register", json={"username": "bob"})
    assert second_r.json()["user_id"] == first


async def test_register_different_users_get_different_ids(client):
    alice = await register_user(client, "alice_unique")
    bob = await register_user(client, "bob_unique")
    assert alice != bob