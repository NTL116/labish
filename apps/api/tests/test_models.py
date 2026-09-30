import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.events import UserCreatedEvent
from app.models import User


def test_user_id_is_auto_generated_uuid() -> None:
    user = User(email="a@example.com", hashed_password="x")
    assert isinstance(user.id, uuid.UUID)


def test_user_ids_are_unique() -> None:
    first = User(email="a@example.com", hashed_password="x")
    second = User(email="b@example.com", hashed_password="x")
    assert first.id != second.id


def test_user_defaults() -> None:
    before = datetime.now(timezone.utc)
    user = User(email="a@example.com", hashed_password="x")
    after = datetime.now(timezone.utc)

    assert user.is_active is True
    assert before <= user.created_at <= after
    assert before <= user.updated_at <= after


def test_user_is_a_table_model() -> None:
    assert User.__tablename__ == "user"


def test_user_email_column_is_unique_and_indexed() -> None:
    email_column = User.__table__.columns["email"]
    assert email_column.unique
    assert email_column.index


def test_user_id_is_primary_key() -> None:
    id_column = User.__table__.columns["id"]
    assert id_column.primary_key


def test_user_created_event_defaults() -> None:
    user_id = uuid.uuid4()
    event = UserCreatedEvent(user_id=user_id, email="a@example.com")

    assert isinstance(event.event_id, uuid.UUID)
    assert event.user_id == user_id
    assert event.email == "a@example.com"
    assert event.occurred_at.tzinfo is not None


def test_user_created_event_requires_user_id_and_email() -> None:
    with pytest.raises(ValidationError):
        UserCreatedEvent.model_validate({})
