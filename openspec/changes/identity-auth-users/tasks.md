# Tasks

## 1. Data model and seed setup

- [x] 1.1 Define the user, role, status, and audit schema and verify the migrations cover creation, verification, enablement, deshabilitación, and role changes.
- [x] 1.2 Implement initial admin seed logic with ADMIN_EMAIL, secret file generation in SECRETS_DIR, and verification that the file is removed after activation use.

## 2. Registration and verification flow

- [x] 2.1 Implement registration validation for email normalization, password length, uniqueness, and PENDIENTE_VERIFICACION creation; verify the API rejects duplicate emails and weak passwords.
- [x] 2.2 Implement single-use verification tokens with 24-hour expiry and 2-minute resend cooldown; verify the token is invalidated after first use and a resend replaces the old token.

## 3. Authentication and session control

- [x] 3.1 Implement login with credential validation first and verification-status check second; verify correct credentials return a 60-minute JWT and unverified users return 403 with "cuenta no verificada".
- [x] 3.2 Implement logout token revocation and verify subsequent requests with the same JWT return 401 until expiry.

## 4. Administration and authorization enforcement

- [x] 4.1 Implement admin-only enablement transitions with valid state machine enforcement and 409 for invalid transitions; verify VERIFICADO → HABILITADO and HABILITADO ⇄ DESHABILITADO work as specified. Un no administrador recibe 403.
- [x] 4.2 Implement admin-only role management with self-promotion prevention and last-admin protection; verify invalid role changes are rejected.

## 5. Audit and quality gates

- [x] 5.1 Implement immutable audit history for state and role changes, verifying value-before/value-after and actor metadata are stored without edits or deletes.
- [x] 5.2 Add security-focused tests for bcrypt hashing, secret redaction, and generic auth errors; verify no passwords or tokens are logged.
- [x] 5.3 Run the auth and users test suite and verify coverage is at least 80% for the affected modules.
