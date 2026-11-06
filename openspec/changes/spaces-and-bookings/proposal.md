# Proposal

## Why

La API ya proporciona identidad, autenticación y administración de usuarios, pero todavía no permite administrar espacios académicos ni gestionar reservas. Esta etapa agrega el flujo API esencial para consultar disponibilidad, solicitar y resolver reservas, y conservar evidencia inmutable de cada cambio.

## What Changes

- Agregar el registro y administración de espacios con nombre, tipo, capacidad y estado.
- Agregar consulta de disponibilidad por espacio y fecha, limitada al horario de 07:00 a 21:00, con franjas ocupadas y libres.
- Permitir a usuarios habilitados solicitar reservas, sin bloquear solicitudes pendientes que se traslapen; rechazar solicitudes que se traslapen con reservas aprobadas e identificar el conflicto.
- Permitir que administradores aprueben o rechacen solicitudes pendientes; al aprobar, rechazar las solicitudes pendientes traslapadas del mismo espacio.
- Permitir que el solicitante cancele sus reservas pendientes o aprobadas y evitar la cancelación de estados finales.
- Registrar un historial append-only de cada cambio de estado, con actor, instante UTC, estado anterior y nuevo, y motivo obligatorio cuando corresponda.
- Al deshabilitar un usuario, cancelar sus solicitudes pendientes y sus reservas aprobadas futuras con el motivo requerido.
- Exponer los endpoints como API; no incluye interfaz gráfica.

## Capabilities

### New Capabilities
- `spaces`: administración de espacios académicos y consulta de disponibilidad por fecha.
- `reservations`: solicitudes, aprobación, rechazo, cancelación, resolución de conflictos e historial de reservas.

### Modified Capabilities

## Impact

- API FastAPI: nuevos endpoints y autorización basada en la identidad existente.
- Persistencia: modelos SQLAlchemy y migraciones Alembic para espacios, reservas e historial inmutable.
- Administración de usuarios: la deshabilitación debe cancelar las reservas aplicables en la misma operación lógica.
- Pruebas API y documentación de endpoints/contratos.
- No incluye el límite de cuatro horas por reserva (RF-17, etapa 4), interfaz gráfica (etapa 3), recurrencia, notificaciones por correo, integración académica ni reportes de ocupación.
