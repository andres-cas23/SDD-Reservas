from datetime import timezone
from urllib.parse import parse_qs, urlparse

import jwt
from sqlalchemy import select

from app.models import RevokedToken, User

PASSWORD = "a-very-long-password"


def _register_user(client, email="login@example.com"):
    sent = []
    client.app.state.send_verification = lambda recipient, link: sent.append(
        (recipient, link)
    )
    registered = client.post(
        "/auth/register",
        json={"name": "Login User", "email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    token = parse_qs(urlparse(sent[0][1]).fragment)["token"][0]
    return client, token


def test_login_checks_credentials_before_verification_status(client):
    _register_user(client)

    invalid = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    missing = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )
    valid_unverified = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": PASSWORD},
    )

    assert invalid.status_code == missing.status_code == 401
    assert invalid.json() == missing.json()
    assert valid_unverified.status_code == 403
    assert valid_unverified.json()["detail"] == "cuenta no verificada"


def test_verified_user_login_issues_sixty_minute_jwt(client, settings):
    _, verification_token = _register_user(client)
    client.post("/auth/verify", json={"token": verification_token})

    response = client.post(
        "/auth/login",
        json={"email": "LOGIN@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["expires_in"] == 3600
    assert response.json()["token_type"] == "bearer"
    claims = jwt.decode(
        response.json()["access_token"],
        settings.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
    )
    assert claims["exp"] - claims["iat"] == 3600


def test_logout_revokes_jwt_until_expiration(client, db_session, settings):
    _, verification_token = _register_user(client)
    client.post("/auth/verify", json={"token": verification_token})
    login = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": PASSWORD},
    )
    access_token = login.json()["access_token"]
    claims = jwt.decode(
        access_token,
        settings.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
    )

    logout = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    replay = client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )

    revoked = db_session.get(RevokedToken, claims["jti"])
    assert logout.status_code == 204
    assert replay.status_code == 401
    assert revoked is not None
    assert int(revoked.expires_at.replace(tzinfo=timezone.utc).timestamp()) == claims["exp"]


def test_disabled_user_cannot_log_in(client, db_session):
    _, verification_token = _register_user(client)
    client.post("/auth/verify", json={"token": verification_token})
    user = db_session.scalar(select(User))
    user.status = "DESHABILITADO"
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "cuenta deshabilitada"
