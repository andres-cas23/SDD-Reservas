# Design

## Context

See proposal.md - Why. The existing reservations API uses a FastAPI router under `/reservations`, SQLAlchemy queries, and the authenticated-user, enabled-user, and administrator dependencies. It supports creating and acting on individual reservations but has no collection GET route.

## Goals / Non-Goals

**Goals:**
- Add a read-only collection endpoint whose query scope is determined by the authenticated role and requester identity.
- Return only the RF-18 fields: status, space, date, and schedule.

**Non-Goals:**
- Change reservation creation, state transitions, cancellation, overlap handling, or history behavior.
- Add pagination, search, filtering, UI, or new authorization roles.

## Decisions

- **Use one `GET /reservations` endpoint.** For an HABILITADO requester, filter the query by their authenticated user ID; for an administrator, do not apply the requester filter. This keeps the read operation in the existing reservations API and makes the access policy explicit.
- **Reuse existing authorization dependencies.** Require HABILITADO status for requester listing and the existing administrator dependency for the all-reservations listing. Authenticated users without either permission receive 403.
- **Return a list with status, space name, date, start time, and end time.** These fields represent RF-18's state, space, date, and schedule without introducing additional behavior.
- **Keep the endpoint read-only.** It does not update reservation state or alter any booking rules.

## Risks / Trade-offs

- [An incorrectly scoped requester query could reveal another user's reservations] → Test that requester results contain only records owned by that identity and that unauthorized roles receive 403.
- [Returning unnecessary reservation data could expand the contract beyond RF-18] → Restrict the response schema to status, space, date, and schedule.

## Migration Plan

No database migration is needed. Deploy the additive API endpoint with its response schema and authorization tests.
