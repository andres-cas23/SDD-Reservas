# Tasks

## 1. RF-17 implementation and tests

- [x] 1.1 Implement the inclusive four-hour maximum in the reservation service, not in the endpoint or database; add tests proving 9:00–13:00 creates a PENDIENTE reservation, 9:00–13:01 and 9:00–14:00 return 422 with the required message and create no reservation, and zero/negative durations remain rejected by RF-10; verify with `python -m pytest tests/test_reservation_duration.py`.
- [x] 1.2 Only after all RF-17 tests pass, update only the RF-17 row in the `PLAN_INGENIERIA.md` verification matrix to `Verificado`; verify no other requirement row changed.

## 2. Regression

- [x] 2.1 After implementing RF-17, run the complete backend test suite to verify RF-01 through RF-16 still pass; verify with `python -m pytest` and do not mark this task complete if any test fails.
