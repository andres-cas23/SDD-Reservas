# Proposal

## Why

RF-18 requiere que solicitantes y administradores puedan consultar listados de reservas con sus datos principales. La API actual permite crear y gestionar reservas individuales, pero no ofrece un endpoint para listar reservas.

## What Changes

- Agregar `GET /reservations`: el solicitante consulta solo sus propias reservas y el administrador consulta todas.
- Cada elemento del listado incluye estado, espacio, fecha y horario.
- Responder `403` cuando un usuario no tenga permiso para consultar el listado.
- Limitar el cambio al requisito RF-18; no modifica reglas de negocio ni agrega interfaz.

## Capabilities

### New Capabilities

### Modified Capabilities
- `reservations`: agregar el requisito RF-18 para listar reservas con acceso según solicitante y administrador.

## Impact

- API de reservas: endpoint de lectura `GET /reservations` y datos de listado.
- Autorización existente de solicitantes y administradores.
- Pruebas API para listados propios, listados globales del administrador y acceso prohibido.
