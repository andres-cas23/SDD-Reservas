# Proposal

## Why

The current login response and access token do not expose the authenticated user's role, while the web interface needs that role to show administrator navigation only to ADMIN users. A minimal authenticated profile endpoint lets the client identify the current user's role without inferring authorization from client-controlled data.

## What Changes

- Add `GET /auth/me` to return the authenticated caller's role.
- Require a valid bearer token and return only the caller's profile role; do not expose other users' data.
- Keep authorization enforcement for protected actions in their existing API endpoints.

## Capabilities

### New Capabilities

- `user-profile`: authenticated users can retrieve their own role for role-appropriate client presentation.

### Modified Capabilities

## Impact

- FastAPI authentication route and response schema.
- Backend tests for role retrieval and authentication failures.
- The frontend can consume this endpoint to show administrator navigation based on the authenticated user's role; no role is trusted from client-supplied values.
