# Design

## Context

See proposal.md - Why. The repository currently has a FastAPI API and no `frontend/` directory. The API routes are grouped under `/auth`, `/users`, `/spaces`, and `/reservations`; the email and initial-admin links are built from `APP_BASE_URL` with paths `/auth/verify` and `/auth/activate-admin`. The API returns field locations in 422 responses and returns either string or structured details for 409 responses.

## Goals / Non-Goals

**Goals:**
- Keep the client presentation-only: send commands and display API results, while the API owns authentication, authorization, validation, and reservation state transitions.
- Make the current verification and seed activation links open client routes while keeping API requests addressable separately.
- Verify the key visitor, enabled-user, and administrator journeys on desktop and mobile.

**Non-Goals:**
- Modify the backend domain rules, persistence, or API response contracts.
- Add features excluded by proposal.md.

## Decisions

- **Place a React/Vite single-page application in `frontend/`.** Use client-side routes for the named screens, with shared navigation that exposes administration options only when the authenticated user's role is ADMIN. A separate server-rendered application would duplicate the existing API-oriented architecture.
- **Keep link routes and API routes distinct.** Configure `APP_BASE_URL` to the frontend origin so the existing generated URLs `/auth/verify#token=...` and `/auth/activate-admin#token=...` load the SPA. The client submits those tokens to `/api/auth/verify` and `/api/auth/activate-admin`. Vite proxies `/api` to the FastAPI origin during development; deployment must route `/api/*` to FastAPI and serve the SPA for client routes. This avoids changing token generation or colliding SPA GET routes with API POST routes.
- **Use one API client and a session-scoped bearer token.** Store the JWT in `sessionStorage`, attach it to authenticated requests, and clear it on logout or 401 before returning to login. This supports browser refreshes without persisting the token after the tab's session; in-memory-only state would be lost on refresh, while long-lived local storage unnecessarily extends persistence.
- **Centralize API error presentation.** On 401 clear the session and navigate to login; on 403 show the API message or the unverified-account message on login; on 404 show the space-not-found message for availability; on 409 display the string detail or structured `message`; on 422 map FastAPI field locations to the corresponding form controls. The client does not retry or reinterpret business-rule outcomes.
- **Separate reusable feature screens and responsive layouts.** Use forms and tables on desktop and adapt dense lists to mobile-friendly cards or scrollable regions so status, schedule, and actions remain usable at narrow widths.
- **Use component-level tests plus Playwright flows.** Component tests cover form/error rendering and role-based navigation; Playwright verifies representative end-to-end flows against the API, including link-token routes, user isolation as returned by the API, administrator actions, and desktop/mobile viewports.

## Risks / Trade-offs

- [An incorrect `APP_BASE_URL` or `/api` proxy can send verification links or API requests to the wrong service] → Document the separate frontend origin and API proxy settings and verify both email-link routes in an end-to-end test.
- [Frontend-only role gating can be mistaken for security enforcement] → Keep all protected operations behind the existing API authorization and test forbidden API responses independently of hidden navigation.
- [Bearer tokens are accessible to same-origin JavaScript] → Keep the token session-scoped, never render or log it, clear it on logout/401, and avoid unsafe HTML rendering.
- [Small screens can hide table actions or validation feedback] → Verify representative screens at mobile viewport sizes in Playwright.

## Migration Plan

Create and install the frontend project under `frontend/`, configure its development proxy and production API origin, and set `APP_BASE_URL` to the frontend origin for generated links. Keep the existing API available under the proxied `/api` prefix. Rollback consists of stopping or removing the frontend deployment and restoring the prior `APP_BASE_URL`; no database migration is required.
