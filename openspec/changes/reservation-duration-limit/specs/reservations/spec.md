# Spec Delta

## ADDED Requirements

### Requirement: RF-17 — Límite de duración de las reservas
Ninguna reserva puede durar más de cuatro horas consecutivas. Una solicitud que lo exceda responde 422 con un mensaje que indica que la reserva no puede superar cuatro horas consecutivas.

The reservation service SHALL apply this inclusive limit only to new requests, calculating duration as the difference between end time and start time.

#### Scenario: A — Solicitud de exactamente cuatro horas
- **WHEN** un usuario habilitado solicita un espacio activo de 9:00 a 13:00
- **THEN** la solicitud se acepta y la reserva se crea en estado PENDIENTE

#### Scenario: B — Solicitud de cuatro horas y un minuto
- **WHEN** un usuario habilitado solicita un espacio activo de 9:00 a 13:01
- **THEN** la solicitud se rechaza con 422, indica que la reserva no puede superar cuatro horas consecutivas y no crea una reserva

#### Scenario: C — Solicitud de cinco horas
- **WHEN** un usuario habilitado solicita un espacio activo de 9:00 a 14:00
- **THEN** la solicitud se rechaza con 422, indica que la reserva no puede superar cuatro horas consecutivas y no crea una reserva

#### Scenario: D — Duración cero o negativa
- **WHEN** un usuario habilitado envía una solicitud cuya hora de fin es igual o anterior a la hora de inicio
- **THEN** la solicitud se rechaza con 422 por la validación existente de RF-10, no por RF-17, y no crea una reserva

#### Scenario: E — Reserva existente que supera cuatro horas
- **WHEN** una reserva existente dura más de cuatro horas
- **THEN** no se revalida ni modifica, porque el límite de RF-17 aplica solo a solicitudes nuevas
