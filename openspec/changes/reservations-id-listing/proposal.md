# Proposal

## Why

`GET /reservations` omits each reservation's identifier, so clients cannot use a listed item to address its cancellation or history endpoints. Adding `id` to each item makes those existing reservation-specific operations addressable without changing RF-18's visibility or authorization rules.

## What Changes

- Add the reservation `id` to every item returned by `GET /reservations`.
- Keep RF-18's requester/admin filtering, permission responses, and existing status, space, date, and schedule fields unchanged.

## Capabilities

### New Capabilities

### Modified Capabilities

- `reservations`: Modify RF-18 to require the reservation identifier in each list item.

## Impact

- API response schema and implementation for `GET /reservations`.
- API tests for requester and administrator reservation listings.
- No change to reservation operations, authorization rules, persistence, or frontend behavior in this change.
