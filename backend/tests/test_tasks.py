import uuid

from .helpers import register_user


async def test_voice_task_without_file_returns_422(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.post("/api/tasks/voice", headers=headers)
    assert r.status_code == 422


async def test_voice_task_non_audio_content_type_returns_400(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.post(
        "/api/tasks/voice",
        headers=headers,
        files={"file": ("test.txt", b"not audio", "text/plain")},
    )
    assert r.status_code == 400


async def test_task_status_not_found_returns_404(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.get(f"/api/tasks/{uuid.uuid4()}/status", headers=headers)
    assert r.status_code == 404


async def test_task_status_bad_uuid_returns_400(client):
    user_id = await register_user(client, "test")
    headers = {"X-User-ID": user_id}
    r = await client.get("/api/tasks/not-a-uuid/status", headers=headers)
    assert r.status_code == 400