from datetime import date, time

from sqlalchemy import select

from app.models import AcademicSpace, Reservation, User
from app.security import hash_password


def _create_user(db_session, email: str, role: str, account_status: str) -> User:
    user = User(
        name="Space Test User",
        email=email,
        password_hash=hash_password("user-password-123"),
        role=role,
        status=account_status,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _token(client, email: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "user-password-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_creates_space_and_enabled_user_lists_spaces(client, db_session):
    admin = _create_user(db_session, "space-admin@example.com", "ADMIN", "HABILITADO")
    enabled = _create_user(db_session, "space-user@example.com", "USER", "HABILITADO")
    admin_headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    user_headers = {"Authorization": f"Bearer {_token(client, enabled.email)}"}

    created = client.post(
        "/spaces",
        headers=admin_headers,
        json={
            "name": "Laboratorio A",
            "type": "LABORATORIO",
            "capacity": 24,
            "status": "ACTIVO",
        },
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Laboratorio A"
    assert created.json()["status"] == "ACTIVO"

    listed = client.get("/spaces", headers=user_headers)
    assert listed.status_code == 200
    assert [space["id"] for space in listed.json()] == [created.json()["id"]]


def test_space_endpoints_reject_non_admin_and_non_enabled_users(client, db_session):
    regular = _create_user(db_session, "space-regular@example.com", "USER", "HABILITADO")
    verified = _create_user(db_session, "space-verified@example.com", "USER", "VERIFICADO")
    regular_headers = {"Authorization": f"Bearer {_token(client, regular.email)}"}
    verified_headers = {"Authorization": f"Bearer {_token(client, verified.email)}"}
    payload = {
        "name": "Auditorio",
        "type": "AUDITORIO",
        "capacity": 100,
        "status": "ACTIVO",
    }

    assert client.post("/spaces", headers=regular_headers, json=payload).status_code == 403
    assert client.get("/spaces", headers=verified_headers).status_code == 403
    assert (
        client.get(
            f"/spaces/{'00000000-0000-0000-0000-000000000001'}/availability?date=2026-11-10",
            headers=verified_headers,
        ).status_code
        == 403
    )


def test_invalid_space_payloads_return_422(client, db_session):
    admin = _create_user(db_session, "space-invalid-admin@example.com", "ADMIN", "HABILITADO")
    headers = {"Authorization": f"Bearer {_token(client, admin.email)}"}
    base = {
        "name": "Valid Space",
        "type": "LABORATORIO",
        "capacity": 10,
        "status": "ACTIVO",
    }

    for invalid in (
        {**base, "name": "   "},
        {**base, "capacity": 0},
        {**base, "type": "CLASSROOM"},
        {**base, "status": "CLOSED"},
    ):
        response = client.post("/spaces", headers=headers, json=invalid)
        assert response.status_code == 422

    assert db_session.scalar(select(AcademicSpace)) is None


def test_availability_returns_approved_occupied_and_complementary_free_intervals(
    client, db_session
):
    user = _create_user(db_session, "availability-user@example.com", "USER", "HABILITADO")
    token = _token(client, user.email)
    space = AcademicSpace(
        name="Availability Hall",
        type="AUDITORIO",
        capacity=120,
        status="ACTIVO",
    )
    db_session.add(space)
    db_session.flush()
    db_session.add_all(
        [
            Reservation(
                space_id=space.id,
                requester_user_id=user.id,
                booking_date=date(2026, 11, 10),
                start_time=time(9),
                end_time=time(10),
                status="APROBADA",
            ),
            Reservation(
                space_id=space.id,
                requester_user_id=user.id,
                booking_date=date(2026, 11, 10),
                start_time=time(13),
                end_time=time(15),
                status="APROBADA",
            ),
            Reservation(
                space_id=space.id,
                requester_user_id=user.id,
                booking_date=date(2026, 11, 10),
                start_time=time(11),
                end_time=time(12),
                status="PENDIENTE",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/spaces/{space.id}/availability?date=2026-11-10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["occupied"] == [
        {"start": "09:00:00", "end": "10:00:00"},
        {"start": "13:00:00", "end": "15:00:00"},
    ]
    assert response.json()["free"] == [
        {"start": "07:00:00", "end": "09:00:00"},
        {"start": "10:00:00", "end": "13:00:00"},
        {"start": "15:00:00", "end": "21:00:00"},
    ]


def test_empty_day_availability_and_unknown_space(client, db_session):
    user = _create_user(db_session, "empty-availability@example.com", "USER", "HABILITADO")
    token = _token(client, user.email)
    space = AcademicSpace(
        name="Empty Hall", type="AUDITORIO", capacity=50, status="ACTIVO"
    )
    db_session.add(space)
    db_session.commit()
    headers = {"Authorization": f"Bearer {token}"}

    empty = client.get(
        f"/spaces/{space.id}/availability?date=2026-11-10", headers=headers
    )
    unknown = client.get(
        "/spaces/00000000-0000-0000-0000-000000000001/availability?date=2026-11-10",
        headers=headers,
    )

    assert empty.status_code == 200
    assert empty.json()["occupied"] == []
    assert empty.json()["free"] == [{"start": "07:00:00", "end": "21:00:00"}]
    assert unknown.status_code == 404
