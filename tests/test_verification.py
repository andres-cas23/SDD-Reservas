from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.models import AccountHistory, User, VerificationToken, utc_now
from app.security import hash_opaque_token


def _register(client, email="verify@example.com"):
    sent = []
    client.app.state.send_verification = lambda recipient, link: sent.append(
        (recipient, link)
    )
    response = client.post(
        "/auth/register",
        json={
            "name": "Verification User",
            "email": email,
            "password": "a-very-long-password",
        },
    )
    assert response.status_code == 201
    return sent


def _raw_token(link: str) -> str:
    return parse_qs(urlparse(link).fragment)["token"][0]


def test_verification_is_single_use_and_records_state_change(client, db_session):
    sent = _register(client)
    token_value = _raw_token(sent[0][1])

    landing = client.get("/auth/verify")
    response = client.post("/auth/verify", json={"token": token_value})
    replay = client.post("/auth/verify", json={"token": token_value})

    user = db_session.scalar(select(User))
    history = db_session.scalars(
        select(AccountHistory).where(AccountHistory.change_type == "STATE")
    ).all()
    assert response.status_code == 200
    assert landing.status_code == 200
    assert replay.status_code == 400
    assert user.status == "VERIFICADO"
    assert [(entry.old_value, entry.new_value) for entry in history] == [
        (None, "PENDIENTE_VERIFICACION"),
        ("PENDIENTE_VERIFICACION", "VERIFICADO"),
    ]


def test_expired_verification_link_does_not_change_account(client, db_session):
    sent = _register(client)
    token = db_session.scalar(select(VerificationToken))
    token.expires_at = utc_now() - timedelta(seconds=1)
    db_session.commit()

    response = client.post(
        "/auth/verify", json={"token": _raw_token(sent[0][1])}
    )

    assert response.status_code == 400
    assert db_session.scalar(select(User)).status == "PENDIENTE_VERIFICACION"


def test_resend_only_works_after_cooldown_and_replaces_previous_token(
    client, db_session
):
    sent = _register(client)
    resend = client.post(
        "/auth/resend-verification", json={"email": "VERIFY@example.com"}
    )
    assert resend.status_code == 429
    assert len(sent) == 1

    user = db_session.scalar(select(User))
    user.last_verification_sent_at = utc_now() - timedelta(minutes=2, seconds=1)
    db_session.commit()
    resend = client.post(
        "/auth/resend-verification", json={"email": "VERIFY@example.com"}
    )

    assert resend.status_code == 202
    assert len(sent) == 2
    old_token = _raw_token(sent[0][1])
    new_token = _raw_token(sent[1][1])
    tokens = db_session.scalars(select(VerificationToken)).all()
    old_record = next(
        item for item in tokens if item.token_hash == hash_opaque_token(old_token)
    )
    assert old_record.consumed_at is not None
    assert client.post("/auth/verify", json={"token": old_token}).status_code == 400
    assert client.post("/auth/verify", json={"token": new_token}).status_code == 200


def test_verified_or_unknown_user_cannot_resend(client, db_session):
    sent = _register(client)
    client.post("/auth/verify", json={"token": _raw_token(sent[0][1])})

    verified = client.post(
        "/auth/resend-verification", json={"email": "verify@example.com"}
    )
    missing = client.post(
        "/auth/resend-verification", json={"email": "missing@example.com"}
    )

    assert verified.status_code == 429
    assert missing.status_code == 429
    assert verified.json() == missing.json()
    assert len(sent) == 1
