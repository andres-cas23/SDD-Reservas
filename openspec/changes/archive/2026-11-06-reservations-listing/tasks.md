# Tasks

## 1. Reservation listing

- [x] 1.1 Add GET /reservations with the RF-18 response fields and requester/admin authorization; add API tests proving requesters see only their own reservations, administrators see all reservations, and users without permission receive 403.
- [x] 1.2 Run the complete pytest suite and `openspec validate reservations-listing --strict`; verify both pass.
