from datetime import datetime, UTC

from app.schemas import ListItemCreate, ListItemResponse, UserCreate, UserResponse


def test_user_create_valid():
    u = UserCreate(username="alice")
    assert u.username == "alice"


def test_user_response_serializes_user_id_as_string():
    from uuid import UUID
    uid = UUID("550e8400-e29b-41d4-a716-446655440000")
    resp = UserResponse(user_id=uid, username="alice")
    data = resp.model_dump(mode="json")
    assert isinstance(data["user_id"], str)
    assert data["user_id"] == "550e8400-e29b-41d4-a716-446655440000"


def test_list_item_create_valid():
    i = ListItemCreate(product_name="помидор")
    assert i.product_name == "помидор"


def test_list_item_response_from_attributes():
    item = ListItemResponse.model_validate({
        "id": 1,
        "product_name": "огурец",
        "added_at": datetime.now(UTC),
        "source": "voice",
    })
    assert item.id == 1
    assert item.product_name == "огурец"
    assert item.source == "voice"
    assert item.added_at.tzinfo is not None