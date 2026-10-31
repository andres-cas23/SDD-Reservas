from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.models import AccountHistory, User, VerificationToken
from app.security import verify_password


def test_registration_creates_pending_user_and_emails_verification_link(
    client, db_session
):
    sent = []
    client.app.state.send_verification = lambda recipient, link: sent.append(
        (recipient, link)
    )

    response = client.post(
        "/auth/register",
        json={
            "name": "  Ada Lovelace  ",
            "email": "Ada.Lovelace@Example.com",
            "password": "a-very-long-password",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Ada Lovelace"
    assert response.json()["email"] == "ada.lovelace@example.com"
    assert response.json()["status"] == "PENDIENTE_VERIFICACION"
    assert "password_hash" not in response.json()
    assert len(sent) == 1
    assert sent[0][0] == "ada.lovelace@example.com"

    raw_token = parse_qs(urlparse(sent[0][1]).fragment)["token"][0]
    user = db_session.scalar(select(User))
    token = db_session.scalar(select(VerificationToken))
    history = db_session.scalar(select(AccountHistory))
    assert user is not None
    assert verify_password("a-very-long-password", user.password_hash)
    assert user.password_hash != "a-very-long-password"
    assert raw_token not in token.token_hash
    assert token.kind == "EMAIL_VERIFICATION"
    assert history.change_type == "STATE"
    assert history.old_value is None
    assert history.new_value == "PENDIENTE_VERIFICACION"


def test_registration_rejects_short_password_and_invalid_email(client, db_session):
    short_password = client.post(
        "/auth/register",
        json={
            "name": "User",
            "email": "user@example.com",
            "password": "my-secret",
        },
    )
    invalid_email = client.post(
        "/auth/register",
        json={
            "name": "User",
            "email": "not-an-email",
            "password": "a-very-long-password",
        },
    )

    assert short_password.status_code == 422
    assert "my-secret" not in short_password.text
    assert invalid_email.status_code == 422
    assert db_session.scalar(select(User)) is None


def test_registration_rejects_case_insensitive_duplicate_email(client, db_session):
    client.app.state.send_verification = lambda _recipient, _link: None
    first = client.post(
        "/auth/register",
        json={
            "name": "User",
            "email": "User@Example.com",
            "password": "a-very-long-password",
        },
    )
    duplicate = client.post(
        "/auth/register",
        json={
            "name": "Another User",
            "email": "user@example.com",
            "password": "a-very-long-password",
        },
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert db_session.query(User).count() == 1


def test_registration_surfaces_mail_failure_without_disclosing_token(client):
    client.app.state.send_verification = lambda _recipient, _link: (_ for _ in ()).throw(
        RuntimeError("internal smtp failure")
    )

    response = client.post(
        "/auth/register",
        json={
            "name": "User",
            "email": "user@example.com",
            "password": "a-very-long-password",
        },
    )

    assert response.status_code == 503
    assert "token" not in response.text.lower()
    assert "internal smtp failure" not in response.text
