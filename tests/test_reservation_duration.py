from datetime import date, time

from sqlalchemy import select

from app.models import AcademicSpace, Reservation, User
from app.security import hash_password

PASSWORD = "reservation-duration-password"
DURATION_ERROR = "La reserva no puede superar cuatro horas consecutivas."


def _create_user(db_session) -> User:
    user = User(
        name="Reservation Duration User",
        email="reservation-duration@example.com",
        password_hash=hash_password(PASSWORD),
        role="USER",
        status="HABILITADO",
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


def _space(db_session) -> AcademicSpace:
    space = AcademicSpace(
        name="Duration Test Hall",
        type="AUDITORIO",
        capacity=100,
        status="ACTIVO",
    )
    db_session.add(space)
    db_session.commit()
    return space


def _payload(space: AcademicSpace, start: str, end: str) -> dict[str, str]:
    return {
        "space_id": str(space.id),
        "date": "2026-11-10",
        "start_time": start,
        "end_time": end,
    }


def test_request_at_exactly_four_hours_is_created_pending(client, db_session):
    user = _create_user(db_session)
    space = _space(db_session)

    response = client.post(
        "/reservations",
        headers=_login(client, user.email),
        json=_payload(space, "09:00", "13:00"),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDIENTE"
    reservation = db_session.scalar(select(Reservation))
    assert reservation is not None
    assert reservation.start_time == time(9)
    assert reservation.end_time == time(13)


def test_request_four_hours_and_one_minute_over_is_rejected(client, db_session):
    user = _create_user(db_session)
    space = _space(db_session)

    response = client.post(
        "/reservations",
        headers=_login(client, user.email),
        json=_payload(space, "09:00", "13:01"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == DURATION_ERROR
    assert db_session.scalars(select(Reservation)).all() == []


def test_five_hour_request_is_rejected(client, db_session):
    user = _create_user(db_session)
    space = _space(db_session)

    response = client.post(
        "/reservations",
        headers=_login(client, user.email),
        json=_payload(space, "09:00", "14:00"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == DURATION_ERROR
    assert db_session.scalars(select(Reservation)).all() == []


def test_zero_or_negative_interval_is_rejected_by_existing_schedule_validation(
    client, db_session
):
    user = _create_user(db_session)
    space = _space(db_session)
    headers = _login(client, user.email)

    for start, end in (("09:00", "09:00"), ("10:00", "09:00")):
        response = client.post(
            "/reservations",
            headers=headers,
            json=_payload(space, start, end),
        )

        assert response.status_code == 422
        assert "la hora de inicio debe preceder a la hora de fin" in response.json()[
            "detail"
        ]
        assert response.json()["detail"] != DURATION_ERROR

    assert db_session.scalars(select(Reservation)).all() == []


def test_reservations_over_four_hours_can_exist_without_revalidation(
    client, db_session
):
    user = _create_user(db_session)
    space = _space(db_session)
    existing = Reservation(
        space_id=space.id,
        requester_user_id=user.id,
        booking_date=date(2026, 11, 10),
        start_time=time(9),
        end_time=time(14),
        status="PENDIENTE",
    )
    db_session.add(existing)
    db_session.commit()

    stored = db_session.get(Reservation, existing.id)

    assert stored is not None
    assert stored.start_time == time(9)
    assert stored.end_time == time(14)
    assert stored.status == "PENDIENTE"
