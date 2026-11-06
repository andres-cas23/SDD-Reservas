# spaces Specification

## Purpose

Permite administrar los espacios académicos que pueden reservarse y consultar su disponibilidad diaria dentro del horario institucional.

## Requirements

### Requirement: Administrators can register academic spaces
The system SHALL allow an administrator to register a space with a name, type, capacity, and operational status.

#### Scenario: Register a valid space
- **WHEN** an administrator registers a space with a non-empty name, positive capacity, type LABORATORIO, AUDITORIO, or SALA_COMPUTO, and status ACTIVO or INACTIVO
- **THEN** the system stores the space with those values

#### Scenario: Reject invalid space data
- **WHEN** an administrator submits a space with an empty name, non-positive capacity, or an unsupported type or status
- **THEN** the system rejects the request with 422 and does not create the space

#### Scenario: Non-administrator cannot register a space
- **WHEN** a non-administrator attempts to register a space
- **THEN** the system responds with 403 and does not create the space

### Requirement: RF-08 — Enabled users can list spaces
The system SHALL provide GET /spaces to return the list of academic spaces only to users with HABILITADO account status.

#### Scenario: Enabled user receives the space list
- **WHEN** a user with HABILITADO account status requests GET /spaces
- **THEN** the system responds with 200 and returns the list of academic spaces

#### Scenario: User who is not enabled cannot list spaces
- **WHEN** a user whose account is not HABILITADO requests GET /spaces
- **THEN** the system responds with 403

### Requirement: Enabled users can consult daily space availability
The system SHALL return the occupied and free time intervals for a space on a requested date, limited to 07:00 through 21:00 in the academic timezone America/Bogota.

#### Scenario: Return occupied and free intervals
- **WHEN** an enabled user requests availability for a space and date
- **THEN** the response lists the approved reservations' occupied intervals and the complementary free intervals within 07:00 to 21:00

#### Scenario: Availability has no reservations
- **WHEN** an enabled user requests availability for a date with no approved reservations for the space
- **THEN** the occupied list is empty and the free list contains the interval from 07:00 to 21:00

#### Scenario: Availability excludes time outside operating hours
- **WHEN** a space has a reservation that occupies only part of its daily schedule
- **THEN** neither the occupied nor free intervals include time before 07:00 or after 21:00

#### Scenario: Reject availability request for an unknown space
- **WHEN** an enabled user requests availability for a space that does not exist
- **THEN** the system responds with 404

#### Scenario: Unenabled user cannot consult availability
- **WHEN** a user whose account is not HABILITADO requests availability
- **THEN** the system responds with 403
