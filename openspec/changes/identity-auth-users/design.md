# Design

## Context

See proposal.md - Why. This stage introduces the identity boundary for registration, verification, authentication, authorization, role management, and immutable audit history. The system must remain API-first and must not include UI or reservation work.

## Goals / Non-Goals

**Goals:**
- Enforce a consistent user lifecycle from registration through enablement.
- Protect authentication and authorization flows with secure token handling and least-privilege policy.
- Keep admin operations auditable and reversible only by new state, never by modifying historical rows.

**Non-Goals:**
- UI screens for login, registration, and administration.
- Password reset flow, OAuth providers, payments, vehicles, or reservation logic.

## Decisions

- The API will use Python/FastAPI with PostgreSQL, SQLAlchemy, and Alembic; this stack was selected by the project owner after confirming the repository contains no existing application scaffold.
- Identity as a dedicated capability: keep all user lifecycle requirements in one contract so auth, user management, and audit remain aligned with the same behavior definitions.
- Password hashing with bcrypt: this meets the non-functional requirement and avoids plaintext or weak hashing for user credentials.
- JWTs with short expiry and explicit revocation: logout is modeled as revocation until expiration; this preserves stateless validation while making the logout event effective for in-flight tokens.
- JWT revocations will be persisted in PostgreSQL keyed by token ID, with each record expiring alongside its JWT; this avoids introducing a separate cache dependency for the current deployment.
- Single-use verification tokens with 24-hour TTL and resend cooldown: this balances user experience with security and prevents token replay or spammy verification requests.
- External secret storage for initial admin activation: writing the link to SECRETS_DIR outside the repository avoids accidental exposure through logs or code snapshots.
- Immutable history table for changes: the audit model stores before/after values and actor metadata, while rejecting edits or deletes to preserve trust and support compliance.

### Alternatives considered

- Using opaque session cookies instead of JWTs: rejected because the project requires a token-based API contract and explicit logout revocation semantics.
- Storing the activation link in the database: rejected because the requirement explicitly says it must live outside the repo in secret storage and never appear in logs.
- Allowing direct status transitions from any state: rejected due to strict state machine rules and 409 conflict handling.

## Risks / Trade-offs

- [Token revocation realism] → Use a revocation store keyed by token ID or jti, with expiry checks applied before acceptance.
- [Audit volume] → Keep a dedicated immutable history table with append-only writes and no soft-delete or update path.
- [Initial admin bootstrap] → Ensure the activation file is created once, removed after use, and is never logged or printed.
- [Generic auth responses] → Return the same error payload for invalid credentials to avoid email enumeration while still returning specific verification errors when the user is known but unverified.

## Migration Plan

1. Add the identity schema and migrations for users, roles, statuses, and audit tables.
2. Seed the first admin using ADMIN_EMAIL and generate the activation file in SECRETS_DIR.
3. Deploy verification, login, logout, and admin endpoints behind API contracts and test them with contract tests.
4. Enable audit hooks for state/role changes and verify immutability in the data layer.
5. Roll out to production only after auth and users coverage exceeds 80% and security checks pass.
