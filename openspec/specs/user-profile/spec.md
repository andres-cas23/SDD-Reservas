# User Profile Specification

## Purpose

Provides an authenticated caller's own role to clients that need role-appropriate presentation without treating client-supplied data as authoritative.

## Requirements

### Requirement: Authenticated users can retrieve their own role
The system SHALL provide GET /auth/me to return only the role of the user authenticated by the request's valid bearer token.

#### Scenario: Authenticated user receives their own role
- **WHEN** an authenticated user requests GET /auth/me
- **THEN** the system returns that user's role and no other user's profile data

#### Scenario: Request without a valid bearer token is rejected
- **WHEN** a request without a valid bearer token calls GET /auth/me
- **THEN** the system responds with 401
