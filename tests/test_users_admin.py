from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.models import AccountHistory, User
from app.security import hash_password
from app.seed_admin import activate_seeded_admin, seed_admin


def _admin_token(client, db_session, settings, repository_root: Path):
    activation_file = seed_admin(db_session, settings, repository_root)
    activation_token = parse_qs(
        urlparse(activation_file.read_text(encoding="utf-8")).fragment
    )["token"][0]
    activate_seeded_admin(
        db_session, activation_token, "admin-password-123", settings
    )
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "admin-password-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_user(db_session, email: str, status: str, role: str = "USER") -> User:
    user = User(
        name="Target",
        email=email,
        password_hash=hash_password("user-password-123"),
        status=status,
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_admin_can_make_all_allowed_enablement_transitions(
    client, db_session, settings, repository_root: Path
):
    admin_jwt = _admin_token(client, db_session, settings, repository_root)
    target = _create_user(db_session, "target@example.com", "VERIFICADO")
    headers = {"Authorization": f"Bearer {admin_jwt}"}

    for next_status in ("HABILITADO", "DESHABILITADO", "HABILITADO"):
        response = client.patch(
            f"/users/{target.id}/status",
            headers=headers,
            json={"status": next_status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == next_status

    history_response = client.get(
        f"/users/{target.id}/history", headers=headers
    )
    assert history_response.status_code == 200
    assert all(
        item["target_user_id"] == str(target.id)
        and item["actor_user_id"] is not None
        and item["created_at"]
        for item in history_response.json()
    )

    changes = db_session.scalars(
        select(AccountHistory)
        .where(
            AccountHistory.target_user_id == target.id,
            AccountHistory.change_type == "STATE",
        )
        .order_by(AccountHistory.created_at, AccountHistory.id)
    ).all()
    assert [(change.old_value, change.new_value) for change in changes] == [
        ("VERIFICADO", "HABILITADO"),
        ("HABILITADO", "DESHABILITADO"),
        ("DESHABILITADO", "HABILITADO"),
    ]


def test_non_admin_gets_403_and_admin_invalid_transitions_get_409(
    client, db_session, settings, repository_root: Path
):
    admin_jwt = _admin_token(client, db_session, settings, repository_root)
    target = _create_user(db_session, "target@example.com", "VERIFICADO")
    user = _create_user(
        db_session, "regular@example.com", "VERIFICADO"
    )
    regular_login = client.post(
        "/auth/login",
        json={"email": user.email, "password": "user-password-123"},
    )
    regular_headers = {
        "Authorization": f"Bearer {regular_login.json()['access_token']}"
    }

    forbidden = client.patch(
        f"/users/{target.id}/status",
        headers=regular_headers,
        json={"status": "HABILITADO"},
    )
    invalid = client.patch(
        f"/users/{target.id}/status",
        headers={"Authorization": f"Bearer {admin_jwt}"},
        json={"status": "DESHABILITADO"},
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 409
    assert db_session.get(User, target.id).status == "VERIFICADO"


def test_admin_cannot_enable_pending_verification_user(
    client, db_session, settings, repository_root: Path
):
    admin_jwt = _admin_token(client, db_session, settings, repository_root)
    target = _create_user(
        db_session, "pending@example.com", "PENDIENTE_VERIFICACION"
    )

    response = client.patch(
        f"/users/{target.id}/status",
        headers={"Authorization": f"Bearer {admin_jwt}"},
        json={"status": "HABILITADO"},
    )

    assert response.status_code == 409
    assert db_session.get(User, target.id).status == "PENDIENTE_VERIFICACION"


def test_admin_can_promote_verified_user_and_audit_role_change(
    client, db_session, settings, repository_root: Path
):
    admin_jwt = _admin_token(client, db_session, settings, repository_root)
    admin = db_session.scalar(select(User).where(User.role == "ADMIN"))
    target = _create_user(db_session, "target@example.com", "VERIFICADO")

    response = client.patch(
        f"/users/{target.id}/role",
        headers={"Authorization": f"Bearer {admin_jwt}"},
        json={"role": "ADMIN"},
    )

    history = db_session.scalar(
        select(AccountHistory).where(
            AccountHistory.target_user_id == target.id,
            AccountHistory.change_type == "ROLE",
        )
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert history.actor_user_id == admin.id
    assert (history.old_value, history.new_value) == ("USER", "ADMIN")


def test_admin_cannot_promote_themselves_or_unverified_users(
    client, db_session, settings, repository_root: Path
):
    admin_jwt = _admin_token(client, db_session, settings, repository_root)
    admin = db_session.scalar(select(User).where(User.role == "ADMIN"))
    pending = _create_user(
        db_session, "pending@example.com", "PENDIENTE_VERIFICACION"
    )
    headers = {"Authorization": f"Bearer {admin_jwt}"}

    self_promotion = client.patch(
        f"/users/{admin.id}/role", headers=headers, json={"role": "ADMIN"}
    )
    unverified_promotion = client.patch(
        f"/users/{pending.id}/role", headers=headers, json={"role": "ADMIN"}
    )

    assert self_promotion.status_code == 409
    assert unverified_promotion.status_code == 409
    assert db_session.get(User, admin.id).role == "ADMIN"
    assert db_session.get(User, pending.id).role == "USER"


def test_last_active_admin_role_cannot_be_revoked(
    client, db_session, settings, repository_root: Path
):
    admin_jwt = _admin_token(client, db_session, settings, repository_root)
    admin = db_session.scalar(select(User).where(User.role == "ADMIN"))

    response = client.patch(
        f"/users/{admin.id}/role",
        headers={"Authorization": f"Bearer {admin_jwt}"},
        json={"role": "USER"},
    )

    assert response.status_code == 409
    assert db_session.get(User, admin.id).role == "ADMIN"


def test_non_admin_cannot_manage_roles(client, db_session):
    target = _create_user(db_session, "target@example.com", "VERIFICADO")
    regular = _create_user(db_session, "regular@example.com", "VERIFICADO")
    regular_token = client.post(
        "/auth/login",
        json={"email": regular.email, "password": "user-password-123"},
    ).json()["access_token"]

    response = client.patch(
        f"/users/{target.id}/role",
        headers={"Authorization": f"Bearer {regular_token}"},
        json={"role": "ADMIN"},
    )

    assert response.status_code == 403
    assert db_session.get(User, target.id).role == "USER"
