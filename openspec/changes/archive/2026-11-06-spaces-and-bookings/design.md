# Design

## Context

See proposal.md - Why. The API uses FastAPI routers, SQLAlchemy models, Alembic migrations, bearer authentication, and a shared `get_db` dependency. `require_admin` enforces administrator access; user disablement currently updates the user and account history in one transaction. Tests create the SQLAlchemy metadata in SQLite, while migrations target PostgreSQL. There is no existing OpenSpec capability spec to modify.

## Goals / Non-Goals

**Goals:**
- Keep booking authorization consistent with the existing authenticated-user and administrator dependencies.
- Persist every state transition and its reason atomically with the reservation change.
- Ensure concurrent requests and approvals cannot produce overlapping approved reservations for one space.
- Keep API tests runnable with the repository's existing SQLite test setup and add PostgreSQL migration-level immutability enforcement.

**Non-Goals:**
- Add a configurable scheduling timezone; academic dates and times use `America/Bogota`.
- Add a time-slot grid; free intervals are the maximal gaps between approved reservations within the daily operating window.
- Change the stage 1 identity state machine or add booking notifications.

## Decisions

- **Separate `spaces` and `reservations` capabilities.** Space lifecycle and availability have a distinct long-lived contract from reservation lifecycle and history. The existing project has no main specs, so both are new capabilities.
- **Store booking schedule as local calendar date and wall-clock start/end times.** API date and time inputs have no UTC offset, so treating them as `America/Bogota` reflects the academic schedule. Compare a reservation's local start against the current time in that zone during user disablement. Store history timestamps as timezone-aware UTC instants using the project's `utc_now` convention.
- **Use UUID-backed `AcademicSpace`, `Reservation`, and `ReservationHistory` models.** Reservations reference their requester and space with restrictive foreign keys. Keep the reservation's current state on its row and write transition reasons to the append-only history, avoiding a second mutable copy of the current reason.
- **Enforce approved-reservation non-overlap in PostgreSQL and serialize booking writes.** Add a partial PostgreSQL EXCLUDE constraint for the same space and overlapping half-open date/time ranges, applying only to APROBADA reservations; enable `btree_gist` for the space equality operator. Keep the per-space transaction lock for deterministic conflict responses and for approving one pending request while rejecting its overlapping pending peers. Pending requests remain unrestricted by the EXCLUDE constraint. Keep state updates and all related history inserts in the same transaction.
- **Integrate disablement in the existing user-status transaction.** When the status changes to DESHABILITADO, lock and cancel the user's pending reservations and approved reservations whose local start is still in the future, append their booking history, and commit all changes with the account status/history. A failure must roll back the entire operation.
- **Enforce and verify append-only history at both application and database layers.** Follow the existing `AccountHistory` pattern with an ORM guard and PostgreSQL migration triggers for update/delete. Mark PostgreSQL integration tests with a dedicated `postgresql` pytest marker and run them against the isolated `reservas_test` database on port 5433; selected tests must fail if that database is unavailable and must never silently skip. Verify the EXCLUDE constraint and both history triggers through PostgreSQL itself, in addition to ORM-level tests.
- **Expose API operations through focused routers.** Use `POST /spaces` to register; `GET /spaces/{space_id}/availability?date=YYYY-MM-DD` to query; `POST /reservations` to request; `POST /reservations/{reservation_id}/approve`, `/reject`, and `/cancel` to change state; and `GET /reservations/{reservation_id}/history` to query history. Include the conflicting reservation identifier in the 409 response. These endpoints use the existing authentication patterns and typed Pydantic request/response models.
- **Treat an inactive space as unavailable for new reservations.** Availability remains queryable for a known space, but request creation requires ACTIVO. Require a non-empty name and positive capacity when creating a space; invalid values return 422.

### Alternatives considered

- **Represent schedules as UTC timestamps:** rejected because requests provide campus-local date and time without an offset; converting them as UTC would shift the intended academic schedule.
- **Use a slot grid for availability:** rejected because no slot length is specified. Returning exact occupied intervals and maximal free gaps avoids inventing a grid.
- **Allow concurrent approval with only a pre-check:** rejected because two transactions could both observe no approved conflict and commit overlapping approvals. Locking the shared space row serializes this decision.
- **Store transition history in a mutable JSON field:** rejected because it cannot provide reliable append-only audit records or efficient per-reservation history queries.

## Risks / Trade-offs

- [SQLite does not enforce PostgreSQL EXCLUDE constraints, triggers, or row-locking semantics] → Run explicitly selected PostgreSQL integration tests against `reservas_test` on port 5433; fail those tests on connection errors instead of skipping them.
- [A database or history-write failure during disablement could leave account and booking states inconsistent] → Perform all account and reservation changes in one transaction and test rollback behavior.
- [The academic timezone is fixed for this stage] → Use the agreed `America/Bogota` zone consistently and avoid configuration that could make comparisons differ across servers.
- [Downgrading the additive migration would remove stage 2 data] → Treat downgrade as an operational rollback only before production data is accepted, or after an explicit database backup.

## Migration Plan

1. Add an Alembic migration after `0001_identity_schema` for spaces, reservations, reservation history, constraints, indexes, foreign keys, the partial EXCLUDE constraint, and PostgreSQL append-only triggers.
2. Verify migration upgrade/downgrade and PostgreSQL-marked EXCLUDE, history-trigger, and reservation-flow tests only against the isolated `reservas_test` database on port 5433; fail selected tests if PostgreSQL is unavailable.
3. Deploy the migration before the API version that exposes the new routes.
4. Keep the migration additive; existing users and account history remain unchanged.
5. If rolling back, first disable the stage 2 routes and confirm the new data can be discarded or restored from backup, then downgrade only the test database during migration verification.

## Open Questions

None. The academic timezone was confirmed as `America/Bogota`.
