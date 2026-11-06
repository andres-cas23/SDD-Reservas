# reservations Specification

## Purpose

Define el ciclo de vida de las solicitudes de reserva, la resolución de conflictos y el historial auditable que permite consultar quién cambió cada reserva y cuándo.

## Requirements

### Requirement: Enabled users can request an academic space
The system SHALL accept a reservation request from an enabled user for an active space and create it in PENDIENTE.

#### Scenario: Create a pending reservation
- **WHEN** an enabled user requests an active space with a date and a start and end time between 07:00 and 21:00, with start before end
- **THEN** the system creates the reservation in PENDIENTE

#### Scenario: Reject a request outside operating hours
- **WHEN** a request starts before 07:00 or ends after 21:00 in America/Bogota
- **THEN** the system responds with 422 and does not create the reservation

#### Scenario: Reject an invalid time interval
- **WHEN** a request has a start time equal to or later than its end time
- **THEN** the system responds with 422 and does not create the reservation

#### Scenario: Inactive space cannot be reserved
- **WHEN** an enabled user requests a space whose status is INACTIVO
- **THEN** the system rejects the request and does not create the reservation

#### Scenario: User who is not enabled cannot request a reservation
- **WHEN** a user whose account is not HABILITADO requests a reservation
- **THEN** the system responds with 403 and does not create the reservation

### Requirement: Approved reservations are the only requests that block a new request
The system SHALL reject a new request only when its time interval overlaps an APROBADA reservation for the same space.

#### Scenario: Reject overlap with an approved reservation
- **WHEN** a request overlaps an APROBADA reservation for the same space
- **THEN** the system responds with 409 and identifies the conflicting reservation

#### Scenario: Pending requests may overlap
- **WHEN** two requests for the same space overlap and neither is APROBADA
- **THEN** the system accepts both requests in PENDIENTE

#### Scenario: Adjacent intervals do not overlap
- **WHEN** one reservation ends at the exact time another reservation starts
- **THEN** the system treats the intervals as non-overlapping

### Requirement: Administrators can approve or reject pending reservations
The system SHALL allow an administrator to approve or reject only a PENDIENTE reservation.

#### Scenario: Approve a pending reservation
- **WHEN** an administrator approves a PENDIENTE reservation
- **THEN** the reservation changes to APROBADA

#### Scenario: Reject a pending reservation with a reason
- **WHEN** an administrator rejects a PENDIENTE reservation and provides a non-empty reason
- **THEN** the reservation changes to RECHAZADA and the reason is recorded

#### Scenario: Reject without a reason
- **WHEN** an administrator attempts to reject a pending reservation without a non-empty reason
- **THEN** the system responds with 422 and leaves the reservation unchanged

#### Scenario: Approval rejects overlapping pending requests
- **WHEN** an administrator approves a reservation while other PENDIENTE reservations overlap it for the same space
- **THEN** each overlapping pending reservation changes to RECHAZADA with reason "conflicto con reserva aprobada"

#### Scenario: Non-administrator cannot approve or reject
- **WHEN** a non-administrator attempts to approve or reject a reservation
- **THEN** the system responds with 403 and leaves the reservation unchanged

#### Scenario: Final reservation cannot be approved or rejected again
- **WHEN** an administrator attempts to approve or reject a reservation that is not PENDIENTE
- **THEN** the system responds with 409 and leaves the reservation unchanged

### Requirement: Requesters can cancel their own pending or approved reservations
The system SHALL allow the requester to cancel their PENDIENTE or APROBADA reservation by providing a non-empty reason.

#### Scenario: Cancel a pending reservation
- **WHEN** the requester cancels their PENDIENTE reservation with a non-empty reason
- **THEN** the reservation changes to CANCELADA and the reason is recorded

#### Scenario: Cancel an approved reservation
- **WHEN** the requester cancels their APROBADA reservation with a non-empty reason
- **THEN** the reservation changes to CANCELADA, the reason is recorded, and its time is immediately available for new requests

#### Scenario: Cannot cancel a final reservation
- **WHEN** the requester attempts to cancel a RECHAZADA or CANCELADA reservation
- **THEN** the system responds with 409 and leaves the reservation unchanged

#### Scenario: Another user cannot cancel the reservation
- **WHEN** a user who is not the requester attempts to cancel the reservation
- **THEN** the system responds with 403 and leaves the reservation unchanged

#### Scenario: Reject cancellation without a reason
- **WHEN** the requester attempts cancellation without a non-empty reason
- **THEN** the system responds with 422 and leaves the reservation unchanged

### Requirement: Disabling a user cancels their applicable reservations
The system SHALL cancel a disabled user's PENDIENTE reservations and future APROBADA reservations as part of the disablement operation.

#### Scenario: Disable user with pending and future approved reservations
- **WHEN** an administrator disables a user who has PENDIENTE reservations or APROBADA reservations whose scheduled start is in the future in America/Bogota
- **THEN** each applicable reservation changes to CANCELADA with reason "usuario deshabilitado"

#### Scenario: Started approved reservation is not canceled by disablement
- **WHEN** an administrator disables a user whose APROBADA reservation has already started in America/Bogota
- **THEN** the reservation remains APROBADA

### Requirement: Reservation state changes are recorded in immutable history
The system SHALL append a history record for every reservation state change, including the actor, UTC timestamp, previous and new state, and any required reason.

#### Scenario: Record initial reservation state
- **WHEN** a reservation is created in PENDIENTE
- **THEN** the system records the initial state change and its requester as actor

#### Scenario: Record approval, rejection, or cancellation
- **WHEN** a reservation changes state through approval, rejection, or cancellation
- **THEN** the system records the actor, UTC timestamp, previous state, new state, and the required reason for rejection or cancellation

#### Scenario: Record automatic state changes
- **WHEN** an approval or user disablement automatically changes other reservations
- **THEN** the system records each change with the administrator responsible, UTC timestamp, previous state, new state, and required reason

#### Scenario: History cannot be edited or deleted
- **WHEN** a client attempts to edit or delete a reservation history record
- **THEN** the system rejects the operation and preserves the record

### Requirement: Users can only view authorized reservation history
The system SHALL allow administrators to query any reservation history and requesters to query only their own reservation history.

#### Scenario: Administrator queries any reservation history
- **WHEN** an administrator requests the history of an existing reservation
- **THEN** the system returns its history ordered from oldest to newest

#### Scenario: Requester queries their own reservation history
- **WHEN** a requester asks for the history of their reservation
- **THEN** the system returns that reservation's history ordered from oldest to newest

#### Scenario: Requester cannot query another user's reservation history
- **WHEN** a requester asks for the history of a reservation they do not own
- **THEN** the system responds with 403
