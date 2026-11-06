from datetime import date, time

from app.models import AcademicSpace, Reservation, User
from app.security import hash_password

PASSWORD = "reservation-list-password"


def _create_user(db_session, email: str, role: str, account_status: str) -> User:
    user = User(
        name="Reservation Listing User",
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
        status=account_status,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _login(client, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_requester_lists_only_their_reservations_with_rf18_fields(
    client, db_session
):
    requester = _create_user(
        db_session, "listing-requester@example.com", "USER", "HABILITADO"
    )
    other_requester = _create_user(
        db_session, "listing-other@example.com", "USER", "HABILITADO"
    )
    own_space = AcademicSpace(
        name="Requester Hall",
        type="AUDITORIO",
        capacity=100,
        status="ACTIVO",
    )
    other_space = AcademicSpace(
        name="Other Lab",
        type="LABORATORIO",
        capacity=20,
        status="ACTIVO",
    )
    db_session.add_all((own_space, other_space))
    db_session.flush()
    db_session.add_all(
        (
            Reservation(
                space_id=own_space.id,
                requester_user_id=requester.id,
                booking_date=date(2026, 11, 10),
                start_time=time(10),
                end_time=time(12),
                status="PENDIENTE",
            ),
            Reservation(
                space_id=other_space.id,
                requester_user_id=other_requester.id,
                booking_date=date(2026, 11, 11),
                start_time=time(13),
                end_time=time(14),
                status="APROBADA",
            ),
        )
    )
    db_session.commit()

    response = client.get(
        "/reservations", headers=_login(client, requester.email)
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "status": "PENDIENTE",
            "space": "Requester Hall",
            "date": "2026-11-10",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        }
    ]


def test_admin_lists_all_reservations(client, db_session):
    requester = _create_user(
        db_session, "listing-admin-user@example.com", "USER", "HABILITADO"
    )
    admin = _create_user(
        db_session, "listing-admin@example.com", "ADMIN", "HABILITADO"
    )
    spaces = [
        AcademicSpace(
            name=name,
            type="AUDITORIO",
            capacity=80,
            status="ACTIVO",
        )
        for name in ("First Hall", "Second Hall")
    ]
    db_session.add_all(spaces)
    db_session.flush()
    db_session.add_all(
        (
            Reservation(
                space_id=spaces[0].id,
                requester_user_id=requester.id,
                booking_date=date(2026, 11, 10),
                start_time=time(9),
                end_time=time(10),
                status="PENDIENTE",
            ),
            Reservation(
                space_id=spaces[1].id,
                requester_user_id=admin.id,
                booking_date=date(2026, 11, 11),
                start_time=time(15),
                end_time=time(16),
                status="APROBADA",
            ),
        )
    )
    db_session.commit()

    response = client.get("/reservations", headers=_login(client, admin.email))

    assert response.status_code == 200
    assert response.json() == [
        {
            "status": "PENDIENTE",
            "space": "First Hall",
            "date": "2026-11-10",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
        {
            "status": "APROBADA",
            "space": "Second Hall",
            "date": "2026-11-11",
            "start_time": "15:00:00",
            "end_time": "16:00:00",
        },
    ]


def test_reservation_listing_rejects_unauthenticated_and_unenabled_users(
    client, db_session
):
    verified_user = _create_user(
        db_session, "listing-verified@example.com", "USER", "VERIFICADO"
    )

    assert client.get("/reservations").status_code == 401
    assert (
        client.get(
            "/reservations", headers=_login(client, verified_user.email)
        ).status_code
        == 403
    )
