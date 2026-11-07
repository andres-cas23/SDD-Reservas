# Tasks

## 1. Frontend foundation

- [x] 1.1 Scaffold the React/Vite application under `frontend/`, add routing, responsive shell, configurable `/api` proxy/origin, npm scripts, and README setup instructions; verify dependency installation and production build succeed.

## 2. Identity flows

- [x] 2.1 Implement visitor registration; add tests for form submission and the API response, and verify the targeted tests pass.
- [x] 2.2 Implement email verification and resend; add tests for link-token handling and the API response, document the link configuration, and verify the targeted tests pass.
- [x] 2.3 Implement initial administrator activation from the seed link; add tests for token/password submission and the API response, document the link configuration, and verify the targeted tests pass.
- [x] 2.4 Implement login/logout and session-scoped bearer-token handling, including clearing the session and returning to login on 401 and showing the unverified-account response on login; add component tests for session and error behavior and verify them with the frontend test runner.

## 3. Enabled-user workflows

- [x] 3.1 Implement space listing, availability, and new-reservation screens using API responses; display 404, 409, and field-level 422 errors; add component tests for data and errors and document the user flow.
- [x] 3.2 Implement “Mis reservas” with own-reservation listing, cancellation, and history; add tests confirming the API results and available actions are displayed, document the flow, and verify the targeted tests pass.

## 4. Administration and integration

- [x] 4.1 Implement administrator screens for user status/role management, reservation approval/rejection/history, and space registration/listing; hide administration navigation for non-ADMIN roles, add component tests for role visibility and API actions, and document the screens.
- [x] 4.2 Add Playwright end-to-end coverage for visitor, enabled-user, and administrator journeys, including verification/activation link routes and desktop/mobile layouts; run the full frontend tests, browser tests, and production build and verify they pass.
