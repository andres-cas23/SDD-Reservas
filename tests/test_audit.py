import pytest
from sqlalchemy import select

from app.models import AccountHistory, User


def test_registration_and_verification_append_state_and_role_history(client, db_session):
    sent = []
    client.app.state.send_verification = lambda recipient, link: sent.append(link)
    registration = client.post(
        "/auth/register",
        json={
            "name": "History User",
            "email": "history@example.com",
            "password": "a-very-long-password",
        },
    )
    from urllib.parse import parse_qs, urlparse

    token = parse_qs(urlparse(sent[0]).fragment)["token"][0]
    client.post("/auth/verify", json={"token": token})

    user = db_session.scalar(select(User))
    history = db_session.scalars(
        select(AccountHistory)
        .where(AccountHistory.target_user_id == user.id)
        .order_by(AccountHistory.change_type)
    ).all()

    assert registration.status_code == 201
    assert {(item.change_type, item.old_value, item.new_value) for item in history} == {
        ("ROLE", None, "USER"),
        ("STATE", None, "PENDIENTE_VERIFICACION"),
        ("STATE", "PENDIENTE_VERIFICACION", "VERIFICADO"),
    }
    verified_change = next(item for item in history if item.new_value == "VERIFICADO")
    assert verified_change.actor_user_id == user.id


def test_account_history_rejects_orm_updates_and_deletes(db_session):
    user = User(
        name="History User",
        email="history@example.com",
        status="VERIFICADO",
        role="USER",
    )
    db_session.add(user)
    db_session.flush()
    record = AccountHistory(
        target_user_id=user.id,
        actor_user_id=None,
        change_type="STATE",
        old_value=None,
        new_value="VERIFICADO",
    )
    db_session.add(record)
    db_session.commit()

    record.new_value = "DESHABILITADO"
    with pytest.raises(ValueError, match="append-only"):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(AccountHistory, record.id).new_value == "VERIFICADO"

    db_session.delete(db_session.get(AccountHistory, record.id))
    with pytest.raises(ValueError, match="append-only"):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(AccountHistory, record.id) is not None
