# Spec Delta

## Purpose

Define la interfaz web para que visitantes, usuarios habilitados y administradores utilicen las funciones existentes del sistema desde navegadores modernos de escritorio y móvil.

## ADDED Requirements

### Requirement: Visitors and account holders can complete identity flows in the web interface
The system SHALL provide interface flows for registration, email verification and resend, login and logout, and initial administrator activation using the existing API.

#### Scenario: Visitor registers
- **WHEN** a visitor submits a valid name, email, and password in the registration screen
- **THEN** the interface sends the registration request to the API and displays its result

#### Scenario: User verifies or resends email verification
- **WHEN** a user opens the verification link in the web interface or requests a verification resend
- **THEN** the interface submits the token or email to the API and displays the returned result

#### Scenario: User logs in and logs out
- **WHEN** a user submits credentials or chooses logout from the authenticated menu
- **THEN** the interface calls the corresponding API operation and reflects the resulting session state

#### Scenario: Initial administrator activates account
- **WHEN** the initial administrator opens the seed activation link in the web interface and submits a new password
- **THEN** the interface sends the activation token and password to the API and displays the result

### Requirement: Enabled users can use space and personal reservation screens
The system SHALL provide HABILITADO users with screens to consult spaces and availability, create requests, and view, cancel, and inspect the history of their own reservations.

#### Scenario: User consults space availability
- **WHEN** an enabled user selects a space and date
- **THEN** the interface displays the space list and the occupied and free intervals returned by the API. The space list comes from GET /spaces, which only HABILITADO users can access.

#### Scenario: User submits a reservation request
- **WHEN** an enabled user submits a space, date, start time, and end time
- **THEN** the interface sends the request to the API and displays the resulting reservation or API error without applying reservation business rules locally

#### Scenario: User manages personal reservations
- **WHEN** an enabled user opens “Mis reservas” and chooses the cancel action only when the status is PENDIENTE or APROBADA, and the history action always for one of their reservations
- **THEN** the interface displays only their reservations and submits the selected action to the corresponding API endpoint

### Requirement: Administrators can use administration screens
The system SHALL provide role-appropriate screens for administrators to manage users, reservations, and spaces while leaving authorization and state transitions to the API.

#### Scenario: Administrator manages users
- **WHEN** an administrator opens user administration and changes a user's enabled status or role
- **THEN** the interface submits the action to the API and displays its result

#### Scenario: Administrator manages reservation requests
- **WHEN** an administrator opens reservation administration and approves, rejects, or inspects the history of a reservation
- **THEN** the interface submits the action to the API and displays its result

#### Scenario: Administrator manages spaces
- **WHEN** an administrator opens space administration
- **THEN** the interface allows registering a space and viewing the space list through the API

#### Scenario: Non-administrator does not see administration options
- **WHEN** a user whose role is not ADMIN views the authenticated interface
- **THEN** administration options are not shown, and the API remains responsible for rejecting unauthorized operations

### Requirement: The interface presents API errors according to their status
The system SHALL translate API responses into the specified user-facing behavior without replacing backend validation or authorization.

#### Scenario: Authentication token is missing, invalid, or revoked
- **WHEN** an API request responds with 401
- **THEN** the interface returns the user to the login screen

#### Scenario: User lacks permission or is unverified
- **WHEN** an API request responds with 403
- **THEN** the interface shows access denied, or shows “cuenta no verificada” when the response is from login

#### Scenario: Space does not exist
- **WHEN** a space request responds with 404
- **THEN** the interface displays a space-not-found message

#### Scenario: API rejects a conflict or invalid state transition
- **WHEN** an API request responds with 409
- **THEN** the interface displays the reason returned by the API

#### Scenario: API rejects invalid form data
- **WHEN** an API request responds with 422
- **THEN** the interface displays the validation message next to the corresponding field

### Requirement: The web interface works on desktop and mobile
The system SHALL provide usable layouts and interactions in modern desktop and mobile browsers.

#### Scenario: User operates the interface on a mobile browser
- **WHEN** a user opens and uses an in-scope screen in a modern mobile browser
- **THEN** the content and controls remain usable without requiring a desktop-width viewport

#### Scenario: User operates the interface on a desktop browser
- **WHEN** a user opens and uses an in-scope screen in a modern desktop browser
- **THEN** the screen presents its content and controls in a usable desktop layout
