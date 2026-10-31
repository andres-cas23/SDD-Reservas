# Spec Delta

## Purpose

Esta capacidad define la identidad del sistema: quién puede registrarse, verificar su cuenta, autenticarse, ser habilitado por administradores y mantener un historial auditable de cambios de estado y rol.

## ADDED Requirements

### Requirement: RF-01 — Visitor can register with a valid account
The system SHALL create a user record only when the provided name, email, and password satisfy the registration rules for this stage.

#### Scenario: Successful registration
- **WHEN** a visitor submits a name, a unique normalized email, and a password with at least 12 characters
- **THEN** the system creates the user in PENDIENTE_VERIFICACION and sends a verification link for the new account

#### Scenario: Duplicate email rejected
- **WHEN** an email is already registered without considering case differences
- **THEN** the system rejects the request and returns a conflict response without creating a second user

### Requirement: RF-01 — User receives a single-use verification link
The system SHALL send a verification link that expires in 24 hours, contains a token of at least 256 bits, and cannot be reused after the first successful validation.

#### Scenario: Verification succeeds once
- **WHEN** a user clicks a valid verification link before expiry
- **THEN** the system marks the account as VERIFICADO and invalidates that token for all future attempts

#### Scenario: Verification link expires or is reused
- **WHEN** the token is expired or already consumed
- **THEN** the system rejects the verification attempt and does not change the account state

### Requirement: RF-01 — User can request another verification email
The system SHALL allow only an unverified user to request a resend after a cooldown period of 2 minutes, and it SHALL invalidate any prior verification link for that user.

#### Scenario: Verified user cannot request another verification email
- **WHEN** a verified user requests another verification email
- **THEN** the system rejects the request

#### Scenario: Verification resend before cooldown is rejected
- **WHEN** an unverified user requests a new verification email before the cooldown expires
- **THEN** the system rejects the request until the cooldown elapses

#### Scenario: New send replaces previous token
- **WHEN** the cooldown has elapsed and an unverified user requests a resend
- **THEN** the system revokes the previous verification token and issues a new one

### Requirement: RF-02 — User can log in only with valid credentials and verified status
The system SHALL authenticate users by checking credentials first and only then evaluating verification status, returning a generic error for invalid credentials and a specific 403 for unverified accounts.

#### Scenario: Valid verified user logs in
- **WHEN** a user enters the correct email and password and the account is VERIFICADO
- **THEN** the system issues a JWT valid for 60 minutes

#### Scenario: Unverified user is blocked
- **WHEN** a user enters valid credentials but the account is not yet verified
- **THEN** the system returns 403 with the message "cuenta no verificada"

#### Scenario: Invalid credentials remain generic
- **WHEN** a user provides an incorrect email or password
- **THEN** the system returns the same generic authentication error regardless of whether the email exists

### Requirement: RF-03 — User can log out and revoke active token
The system SHALL revoke a JWT immediately upon logout and reject any subsequent request carrying that token until it naturally expires.

#### Scenario: Active token is rejected after logout
- **WHEN** a user logs out and then sends a request with the same JWT
- **THEN** the system responds with 401 and denies access

### Requirement: RF-04 — Administrators manage user enablement
The system SHALL allow only administrators to change user enablement status and SHALL accept only the allowed state transitions for this stage.

#### Scenario: Valid enablement transition
- **WHEN** an administrator changes a VERIFICADO user to HABILITADO
- **THEN** the system updates the user status and records the change in the audit history

#### Scenario: Non-admin cannot change user enablement
- **WHEN** a non-administrator attempts to change a user's enablement status
- **THEN** the system returns 403 and preserves the prior state

#### Scenario: Administrator cannot make an invalid transition
- **WHEN** an administrator attempts a disallowed transition such as PENDIENTE_VERIFICACION to HABILITADO or DESHABILITADO to VERIFICADO
- **THEN** the system returns 409 and preserves the prior state

### Requirement: RF-05 — Administrators manage roles safely
The system SHALL allow only administrators to promote or revoke roles, SHALL prevent self-promotion, and SHALL preserve at least one active administrator in the system.

#### Scenario: Admin promotes a verified user
- **WHEN** an active administrator promotes a verified user to admin role
- **THEN** the system updates the role and records who performed the change

#### Scenario: Self-promotion is rejected
- **WHEN** an administrator attempts to promote themselves
- **THEN** the system rejects the operation and preserves the current role

#### Scenario: Last admin cannot be revoked
- **WHEN** the final active administrator is selected for role revocation
- **THEN** the system rejects the operation and keeps the configuration unchanged

### Requirement: RF-06 — Initial admin is seeded and activated securely
The system SHALL create the first administrator from seed data using ADMIN_EMAIL, create an activation link for that account that expires after 24 hours, and write the link outside the repository in SECRETS_DIR without exposing it in console output or logs.

#### Scenario: Seeded admin receives activation path outside repo
- **WHEN** the application initializes with ADMIN_EMAIL configured
- **THEN** the system creates the admin account with an activation link stored in the configured secrets directory and removes the file after it is used

#### Scenario: Seeded admin sets password when activating
- **WHEN** the seeded administrator activates the account using the link before it expires
- **THEN** the system requires the administrator to define a password of at least 12 characters

#### Scenario: Secret is not exposed in logs
- **WHEN** the activation link is generated
- **THEN** the system does not print or log the token value in any console or application log

### Requirement: RF-07 — User state and role changes are immutably audited
The system SHALL store every relevant account change with affected user, responsible actor, UTC timestamp, previous value, and new value, without allowing edits or deletions of audit records.

#### Scenario: State change is recorded
- **WHEN** a user is created, verified, enabled, or disabled
- **THEN** the system appends an immutable audit record with the current and previous values

#### Scenario: Role change is recorded
- **WHEN** an administrator promotes or revokes a role
- **THEN** the system writes a separate immutable role-history entry with actor, target, before, and after values
