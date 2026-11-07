from app.models import User
from app.security import hash_password


def _create_user(db_session, email: str, role: str) -> User:
    user = User(
        name="Profile User",
        email=email,
        password_hash=hash_password("profile-password-123"),
        status="HABILITADO",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _login(client, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "profile-password-123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_authenticated_user_receives_only_their_role(client, db_session):
    _create_user(db_session, "profile-user@example.com", "USER")
    headers = _login(client, "profile-user@example.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"role": "USER"}


def test_authenticated_admin_receives_admin_role(client, db_session):
    _create_user(db_session, "profile-admin@example.com", "ADMIN")
    headers = _login(client, "profile-admin@example.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"role": "ADMIN"}


def test_profile_endpoint_rejects_missing_or_invalid_bearer_token(client):
    missing_token = client.get("/auth/me")
    invalid_token = client.get(
        "/auth/me", headers={"Authorization": "Bearer invalid-token"}
    )

    assert missing_token.status_code == 401
    assert invalid_token.status_code == 401
