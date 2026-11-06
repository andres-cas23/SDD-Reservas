# Tasks

## 1. Persistence and migration

- [x] 1.1 Add SQLAlchemy models and database constraints, including the partial PostgreSQL EXCLUDE constraint for overlapping APROBADA reservations; verify enum values, required fields, foreign keys, the EXCLUDE constraint, and reservation-history UPDATE/DELETE triggers against real PostgreSQL `reservas_test` on port 5433. Mark integration tests `postgresql`, run them explicitly with `pytest -m postgresql`, and fail rather than skip if the test database is unavailable.
- [x] 1.2 Add the Alembic migration after `0001_identity_schema` for the new tables, indexes, constraints, and PostgreSQL triggers that prevent UPDATE and DELETE on reservation history; verify migration upgrade and downgrade only against `reservas_test` on port 5433, never the development database.

## 2. Space administration and availability

- [x] 2.1 Add typed space request/response schemas, the administrator-only `POST /spaces` endpoint, and `GET /spaces` for HABILITADO users; test valid registration, invalid names/capacities/types/statuses returning 422, non-administrator registration returning 403, a HABILITADO user receiving the space list, and a non-enabled user receiving 403.
- [x] 2.2 Add the authenticated `GET /spaces/{space_id}/availability` endpoint for a date in `America/Bogota`; test HABILITADO authorization, unknown-space 404, approved occupied intervals, free gaps, empty days, and the 07:00–21:00 boundaries.
- [x] 2.3 Document space registration and availability request/response contracts in README.md; verify the documented paths, fields, and error cases match the API schemas.

## 3. Reservation request and resolution

- [x] 3.1 Implement reservation creation for HABILITADO users and ACTIVO spaces, validating time order and the 07:00–21:00 schedule; test 422 boundaries, inactive spaces, pending creation, pending overlaps, half-open adjacent intervals, and 409 conflicts that identify the approved reservation against real PostgreSQL `reservas_test` on port 5433. Mark the integration tests `postgresql` and fail rather than skip if the database is unavailable.
- [x] 3.2 Implement administrator approval and rejection with per-space transaction locking; test forbidden non-admin requests, invalid state transitions, mandatory rejection reasons, automatic rejection of overlapping pending requests with the exact reason, and concurrent approvals preserving non-overlap under the PostgreSQL EXCLUDE constraint against real `reservas_test` on port 5433. Mark the integration tests `postgresql` and fail rather than skip if the database is unavailable.
- [x] 3.3 Document reservation creation and administrator decision endpoints in README.md; verify examples and documented state/error behavior against the implemented schemas.

## 4. Cancellation, user disablement, and history

- [x] 4.1 Implement requester-owned cancellation for PENDIENTE and APROBADA reservations with mandatory reasons; test ownership, final-state 409 responses, and immediate availability after canceling an approved reservation.
- [x] 4.2 Record initial and subsequent state transitions with actor, UTC timestamp, before/after states, and required reasons; implement admin/requester history access and append-only enforcement, then test access boundaries, ordering, and recorded metadata. Mark PostgreSQL integration tests `postgresql` and verify the database triggers reject direct UPDATE and DELETE against real `reservas_test` on port 5433; fail rather than skip if the database is unavailable.
- [x] 4.3 Integrate reservation cancellation into user disablement in the same transaction; test cancellation of PENDIENTE requests and future APROBADA reservations in America/Bogota, exact reason/actor/history, rollback on failure, and availability of released time against real PostgreSQL `reservas_test` on port 5433. Mark the integration tests `postgresql` and fail rather than skip if the database is unavailable.
- [x] 4.4 Document approval, rejection, cancellation, history access, and disablement effects in README.md; verify the documented authorization and reason requirements match the API.

## 5. Integration verification

- [x] 5.1 Run the complete pytest suite with the configured coverage threshold and verify it passes.
- [x] 5.2 Run `openspec validate spaces-and-bookings --strict` and resolve any specification-format errors.
