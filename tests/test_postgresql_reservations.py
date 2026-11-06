from datetime import date, time
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import create_app
from app.models import AcademicSpace, Reservation, ReservationHistory, User
from app.security import hash_password

pytestmark = pytest.mark.postgresql


def _migration_command(postgresql_engine, action: str, revision: str) -> None:
    database_url = postgresql_engine.url.render_as_string(hide_password=False)
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        getattr(command, action)(Config("alembic.ini"), revision)
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


def test_00_migrations_upgrade_and_downgrade_only_the_test_database(
    postgresql_engine,
):
    assert postgresql_engine.url.database == "reservas_test"
    assert postgresql_engine.url.port == 5433
    _migration_command(postgresql_engine, "downgrade", "base")
    _migration_command(postgresql_engine, "upgrade", "head")

    with postgresql_engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == "0002_spaces_reservations"


def _create_space_and_user(session):
    user = User(
        name="PostgreSQL Test",
        email=f"{uuid4()}@example.com",
        status="HABILITADO",
    )
    space = AcademicSpace(
        name="PostgreSQL Lab",
        type="LABORATORIO",
        capacity=20,
        status="ACTIVO",
    )
    session.add_all((user, space))
    session.flush()
    return user, space


def _create_login_user(session, email: str, role: str, state: str) -> User:
    user = User(
        name="PostgreSQL API User",
        email=email,
        password_hash=hash_password("postgresql-password"),
        role=role,
        status=state,
    )
    session.add(user)
    session.commit()
    return user


def _login(client, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "postgresql-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _reservation(user, space, start: time, end: time, state: str):
    return Reservation(
        space_id=space.id,
        requester_user_id=user.id,
        booking_date=date(2026, 11, 10),
        start_time=start,
        end_time=end,
        status=state,
    )


def test_postgresql_exclude_constraint_blocks_only_approved_overlaps(
    postgresql_engine, postgresql_session
):
    user, space = _create_space_and_user(postgresql_session)
    approved = _reservation(user, space, time(10), time(12), "APROBADA")
    postgresql_session.add(approved)
    postgresql_session.commit()

    overlapping_approved = _reservation(user, space, time(11), time(13), "APROBADA")
    postgresql_session.add(overlapping_approved)
    with pytest.raises(IntegrityError):
        postgresql_session.commit()
    postgresql_session.rollback()

    postgresql_session.add_all(
        [
            _reservation(user, space, time(11), time(13), "PENDIENTE"),
            _reservation(user, space, time(12), time(14), "APROBADA"),
        ]
    )
    postgresql_session.commit()

    approved_rows = postgresql_session.scalars(
        select(Reservation).where(Reservation.status == "APROBADA")
    ).all()
    assert len(approved_rows) == 2


def test_postgresql_reservation_request_conflicts_and_approval_resolution(
    postgresql_client, postgresql_session
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    admin = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "ADMIN", "HABILITADO"
    )
    space = AcademicSpace(
        name="API Reservation Space", type="AUDITORIO", capacity=80
    )
    postgresql_session.add(space)
    postgresql_session.commit()
    requester_headers = _login(postgresql_client, requester.email)
    admin_headers = _login(postgresql_client, admin.email)
    base = {
        "space_id": str(space.id),
        "date": "2026-11-10",
        "start_time": "10:00",
        "end_time": "12:00",
    }

    pending_one = postgresql_client.post(
        "/reservations", headers=requester_headers, json=base
    )
    pending_two = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**base, "start_time": "11:00", "end_time": "13:00"},
    )
    assert pending_one.status_code == 201
    assert pending_two.status_code == 201

    approved = postgresql_client.post(
        f"/reservations/{pending_one.json()['id']}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APROBADA"

    conflicting = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**base, "start_time": "11:30", "end_time": "12:30"},
    )
    adjacent = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**base, "start_time": "12:00", "end_time": "14:00"},
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["detail"]["reservation_id"] == pending_one.json()["id"]
    assert adjacent.status_code == 201
    assert adjacent.json()["status"] == "PENDIENTE"

    history = postgresql_client.get(
        f"/reservations/{pending_two.json()['id']}/history",
        headers=requester_headers,
    )
    assert history.status_code == 200
    assert [entry["new_status"] for entry in history.json()] == [
        "PENDIENTE",
        "RECHAZADA",
    ]
    assert history.json()[1]["reason"] == "conflicto con reserva aprobada"


def test_postgresql_reservation_schedule_and_inactive_space_validation(
    postgresql_client, postgresql_session
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    verified_user = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "VERIFICADO"
    )
    active_space = AcademicSpace(
        name="Schedule Space", type="LABORATORIO", capacity=8, status="ACTIVO"
    )
    inactive_space = AcademicSpace(
        name="Inactive Space", type="SALA_COMPUTO", capacity=8, status="INACTIVO"
    )
    postgresql_session.add_all((active_space, inactive_space))
    postgresql_session.commit()
    headers = _login(postgresql_client, requester.email)
    verified_headers = _login(postgresql_client, verified_user.email)
    base = {"date": "2026-11-10", "start_time": "10:00", "end_time": "12:00"}

    for start, end in (("06:59", "08:00"), ("20:00", "21:01"), ("10:00", "10:00")):
        response = postgresql_client.post(
            "/reservations",
            headers=headers,
            json={**base, "space_id": str(active_space.id), "start_time": start, "end_time": end},
        )
        assert response.status_code == 422

    inactive = postgresql_client.post(
        "/reservations",
        headers=headers,
        json={**base, "space_id": str(inactive_space.id)},
    )
    assert inactive.status_code == 409
    unenabled = postgresql_client.post(
        "/reservations",
        headers=verified_headers,
        json={**base, "space_id": str(active_space.id)},
    )
    assert unenabled.status_code == 403


def test_postgresql_administrator_only_approval_and_rejection_reasons(
    postgresql_client, postgresql_session
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    admin = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "ADMIN", "HABILITADO"
    )
    space = AcademicSpace(name="Decisions Space", type="AUDITORIO", capacity=40)
    postgresql_session.add(space)
    postgresql_session.commit()
    requester_headers = _login(postgresql_client, requester.email)
    admin_headers = _login(postgresql_client, admin.email)
    payload = {
        "space_id": str(space.id),
        "date": "2026-11-10",
        "start_time": "10:00",
        "end_time": "11:00",
    }
    pending = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**payload, "start_time": "13:00", "end_time": "14:00"},
    )
    assert pending.status_code == 201
    reservation_id = pending.json()["id"]

    forbidden = postgresql_client.post(
        f"/reservations/{reservation_id}/approve", headers=requester_headers
    )
    missing_reason = postgresql_client.post(
        f"/reservations/{reservation_id}/reject",
        headers=admin_headers,
        json={"reason": "  "},
    )
    rejected = postgresql_client.post(
        f"/reservations/{reservation_id}/reject",
        headers=admin_headers,
        json={"reason": "No disponible"},
    )
    repeated = postgresql_client.post(
        f"/reservations/{reservation_id}/approve", headers=admin_headers
    )

    assert forbidden.status_code == 403
    assert missing_reason.status_code == 422
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "RECHAZADA"
    assert repeated.status_code == 409


def test_postgresql_requester_cancellation_releases_time_and_history_is_authorized(
    postgresql_client, postgresql_session
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    another_user = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    admin = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "ADMIN", "HABILITADO"
    )
    space = AcademicSpace(name="Cancellation Space", type="AUDITORIO", capacity=45)
    postgresql_session.add(space)
    postgresql_session.commit()
    requester_headers = _login(postgresql_client, requester.email)
    another_headers = _login(postgresql_client, another_user.email)
    admin_headers = _login(postgresql_client, admin.email)
    payload = {
        "space_id": str(space.id),
        "date": "2026-11-10",
        "start_time": "10:00",
        "end_time": "12:00",
    }

    pending = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**payload, "start_time": "13:00", "end_time": "14:00"},
    )
    approved = postgresql_client.post(
        "/reservations", headers=requester_headers, json=payload
    )
    approved_decision = postgresql_client.post(
        f"/reservations/{approved.json()['id']}/approve", headers=admin_headers
    )
    forbidden_cancel = postgresql_client.post(
        f"/reservations/{approved.json()['id']}/cancel",
        headers=another_headers,
        json={"reason": "No soy el solicitante"},
    )
    cancelled_pending = postgresql_client.post(
        f"/reservations/{pending.json()['id']}/cancel",
        headers=requester_headers,
        json={"reason": "Cambio de planes"},
    )
    cancelled_approved = postgresql_client.post(
        f"/reservations/{approved.json()['id']}/cancel",
        headers=requester_headers,
        json={"reason": "Cambio de planes"},
    )
    repeated_cancel = postgresql_client.post(
        f"/reservations/{approved.json()['id']}/cancel",
        headers=requester_headers,
        json={"reason": "Segundo intento"},
    )
    replacement = postgresql_client.post(
        "/reservations", headers=another_headers, json=payload
    )
    own_history = postgresql_client.get(
        f"/reservations/{approved.json()['id']}/history",
        headers=requester_headers,
    )
    other_history = postgresql_client.get(
        f"/reservations/{approved.json()['id']}/history",
        headers=another_headers,
    )
    admin_history = postgresql_client.get(
        f"/reservations/{approved.json()['id']}/history",
        headers=admin_headers,
    )

    assert approved_decision.status_code == 200
    assert forbidden_cancel.status_code == 403
    assert cancelled_pending.status_code == 200
    assert cancelled_approved.status_code == 200
    assert cancelled_approved.json()["status"] == "CANCELADA"
    assert repeated_cancel.status_code == 409
    assert replacement.status_code == 201
    assert own_history.status_code == 200
    assert [entry["new_status"] for entry in own_history.json()] == [
        "PENDIENTE",
        "APROBADA",
        "CANCELADA",
    ]
    assert own_history.json()[0]["old_status"] is None
    assert own_history.json()[0]["actor_user_id"] == str(requester.id)
    assert own_history.json()[0]["created_at"].endswith("Z")
    assert own_history.json()[-1]["reason"] == "Cambio de planes"
    assert own_history.json()[-1]["actor_user_id"] == str(requester.id)
    assert other_history.status_code == 403
    assert admin_history.status_code == 200


def test_postgresql_disabling_user_cancels_pending_and_future_approved_reservations(
    postgresql_client, postgresql_session
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    replacement_user = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    admin = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "ADMIN", "HABILITADO"
    )
    space = AcademicSpace(name="Disablement Space", type="LABORATORIO", capacity=16)
    postgresql_session.add(space)
    postgresql_session.commit()
    requester_headers = _login(postgresql_client, requester.email)
    replacement_headers = _login(postgresql_client, replacement_user.email)
    admin_headers = _login(postgresql_client, admin.email)
    base = {"space_id": str(space.id), "date": "2026-11-10"}

    pending = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**base, "start_time": "10:00", "end_time": "11:00"},
    )
    approved = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={**base, "start_time": "13:00", "end_time": "14:00"},
    )
    assert pending.status_code == approved.status_code == 201
    assert (
        postgresql_client.post(
            f"/reservations/{approved.json()['id']}/approve",
            headers=admin_headers,
        ).status_code
        == 200
    )

    disabled = postgresql_client.patch(
        f"/users/{requester.id}/status",
        headers=admin_headers,
        json={"status": "DESHABILITADO"},
    )
    assert disabled.status_code == 200

    pending_history = postgresql_client.get(
        f"/reservations/{pending.json()['id']}/history", headers=admin_headers
    )
    approved_history = postgresql_client.get(
        f"/reservations/{approved.json()['id']}/history", headers=admin_headers
    )
    replacement = postgresql_client.post(
        "/reservations",
        headers=replacement_headers,
        json={**base, "start_time": "13:00", "end_time": "14:00"},
    )

    assert pending_history.json()[-1]["new_status"] == "CANCELADA"
    assert pending_history.json()[-1]["reason"] == "usuario deshabilitado"
    assert approved_history.json()[-1]["new_status"] == "CANCELADA"
    assert approved_history.json()[-1]["reason"] == "usuario deshabilitado"
    assert approved_history.json()[-1]["actor_user_id"] == str(admin.id)
    assert replacement.status_code == 201


def test_postgresql_disablement_rolls_back_if_reservation_history_insert_fails(
    postgresql_engine, postgresql_client, postgresql_session
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    admin = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "ADMIN", "HABILITADO"
    )
    space = AcademicSpace(name="Rollback Space", type="LABORATORIO", capacity=10)
    postgresql_session.add(space)
    postgresql_session.commit()
    admin_headers = _login(postgresql_client, admin.email)
    requester_headers = _login(postgresql_client, requester.email)
    created = postgresql_client.post(
        "/reservations",
        headers=requester_headers,
        json={
            "space_id": str(space.id),
            "date": "2026-11-10",
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert created.status_code == 201

    with postgresql_engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE FUNCTION reject_test_reservation_history() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'injected reservation history failure';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TRIGGER reject_test_reservation_history
            BEFORE INSERT ON reservation_history
            FOR EACH ROW EXECUTE FUNCTION reject_test_reservation_history()
            """
        )
    try:
        with pytest.raises(DBAPIError, match="injected reservation history failure"):
            postgresql_client.patch(
                f"/users/{requester.id}/status",
                headers=admin_headers,
                json={"status": "DESHABILITADO"},
            )
    finally:
        with postgresql_engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER IF EXISTS reject_test_reservation_history ON reservation_history"
            )
            connection.exec_driver_sql(
                "DROP FUNCTION IF EXISTS reject_test_reservation_history()"
            )

    postgresql_session.rollback()
    postgresql_session.expire_all()
    assert postgresql_session.get(User, requester.id).status == "HABILITADO"
    assert postgresql_session.get(Reservation, created.json()["id"]).status == "PENDIENTE"


def test_postgresql_approval_serializes_concurrent_overlapping_requests(
    postgresql_engine, postgresql_client, postgresql_session, settings
):
    requester = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "USER", "HABILITADO"
    )
    admin = _create_login_user(
        postgresql_session, f"{uuid4()}@example.com", "ADMIN", "HABILITADO"
    )
    space = AcademicSpace(name="Concurrent Space", type="LABORATORIO", capacity=12)
    postgresql_session.add(space)
    postgresql_session.commit()
    requester_headers = _login(postgresql_client, requester.email)
    admin_headers = _login(postgresql_client, admin.email)
    request_payload = {
        "space_id": str(space.id),
        "date": "2026-11-10",
        "start_time": "10:00",
        "end_time": "12:00",
    }
    reservations = [
        postgresql_client.post(
            "/reservations",
            headers=requester_headers,
            json={**request_payload, "start_time": start, "end_time": end},
        )
        for start, end in (("10:00", "12:00"), ("11:00", "13:00"))
    ]
    assert all(response.status_code == 201 for response in reservations)

    application = create_app(settings)

    def override_get_db():
        with Session(postgresql_engine, autoflush=False, expire_on_commit=False) as db:
            yield db

    application.dependency_overrides[get_db] = override_get_db
    barrier = Barrier(2)

    def approve(reservation_id: str):
        barrier.wait(timeout=10)
        return concurrent_client.post(
            f"/reservations/{reservation_id}/approve",
            headers=admin_headers,
        )

    with TestClient(application) as concurrent_client:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    approve, [response.json()["id"] for response in reservations]
                )
            )

    assert sorted(response.status_code for response in responses) == [200, 409]
    postgresql_session.expire_all()
    states = postgresql_session.scalars(
        select(Reservation.status).where(
            Reservation.id.in_([response.json()["id"] for response in reservations])
        )
    ).all()
    assert sorted(states) == ["APROBADA", "RECHAZADA"]


def test_postgresql_enforces_space_and_reservation_fields(postgresql_session):
    user, space = _create_space_and_user(postgresql_session)
    postgresql_session.commit()

    invalid_spaces = [
        AcademicSpace(name="Bad Type", type="CLASSROOM", capacity=20),
        AcademicSpace(name="Bad Capacity", type="AUDITORIO", capacity=0),
        AcademicSpace(name="Bad Status", type="AUDITORIO", capacity=20, status="CLOSED"),
    ]
    for invalid_space in invalid_spaces:
        postgresql_session.add(invalid_space)
        with pytest.raises(IntegrityError):
            postgresql_session.commit()
        postgresql_session.rollback()

    missing_space = AcademicSpace(type="AUDITORIO", capacity=20)
    postgresql_session.add(missing_space)
    with pytest.raises(IntegrityError):
        postgresql_session.commit()
    postgresql_session.rollback()

    invalid_reference = Reservation(
        space_id=uuid4(),
        requester_user_id=user.id,
        booking_date=date(2026, 11, 10),
        start_time=time(10),
        end_time=time(11),
    )
    postgresql_session.add(invalid_reference)
    with pytest.raises(IntegrityError):
        postgresql_session.commit()
    postgresql_session.rollback()

    invalid_order = _reservation(user, space, time(11), time(10), "PENDIENTE")
    postgresql_session.add(invalid_order)
    with pytest.raises(IntegrityError):
        postgresql_session.commit()
    postgresql_session.rollback()


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_postgresql_history_triggers_reject_direct_mutations(
    operation, postgresql_engine, postgresql_session
):
    user, space = _create_space_and_user(postgresql_session)
    reservation = _reservation(user, space, time(10), time(11), "PENDIENTE")
    postgresql_session.add(reservation)
    postgresql_session.flush()
    entry = ReservationHistory(
        reservation_id=reservation.id,
        actor_user_id=user.id,
        old_status=None,
        new_status="PENDIENTE",
    )
    postgresql_session.add(entry)
    postgresql_session.commit()

    with pytest.raises(DBAPIError, match="append-only"):
        if operation == "UPDATE":
            postgresql_session.execute(
                text(
                    "UPDATE reservation_history SET reason = 'tampered' WHERE id = :id"
                ),
                {"id": entry.id},
            )
        else:
            postgresql_session.execute(
                text("DELETE FROM reservation_history WHERE id = :id"),
                {"id": entry.id},
            )
            postgresql_session.commit()
    postgresql_session.rollback()
    assert postgresql_session.get(ReservationHistory, entry.id) is not None


def test_reservation_history_orm_rejects_updates_and_deletes(postgresql_session):
    user, space = _create_space_and_user(postgresql_session)
    reservation = _reservation(user, space, time(10), time(11), "PENDIENTE")
    postgresql_session.add(reservation)
    postgresql_session.flush()
    entry = ReservationHistory(
        reservation_id=reservation.id,
        actor_user_id=user.id,
        old_status=None,
        new_status="PENDIENTE",
    )
    postgresql_session.add(entry)
    postgresql_session.commit()

    entry.reason = "mutación"
    with pytest.raises(ValueError, match="append-only"):
        postgresql_session.commit()
    postgresql_session.rollback()
    postgresql_session.delete(postgresql_session.get(ReservationHistory, entry.id))
    with pytest.raises(ValueError, match="append-only"):
        postgresql_session.commit()
    postgresql_session.rollback()
