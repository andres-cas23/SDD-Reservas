# Spec Delta

## ADDED Requirements

### Requirement: RF-18 — Users can list reservations according to their permissions
The system SHALL provide GET /reservations so a requester can list only their own reservations and an administrator can list all reservations. Each reservation includes its status, space, date, and schedule. A user without permission is either unauthenticated or authenticated without HABILITADO status: unauthenticated users receive 401, and authenticated users without HABILITADO status receive 403.

#### Scenario: Requester receives only their own reservations
- **WHEN** an authorized requester requests GET /reservations
- **THEN** the system returns only that requester's reservations, each with status, space, date, and schedule

#### Scenario: Administrator receives all reservations
- **WHEN** an administrator requests GET /reservations
- **THEN** the system returns all reservations, each with status, space, date, and schedule

#### Scenario: User without permission cannot list reservations
- **WHEN** a user without permission requests GET /reservations
- **THEN** the system responds with 403
