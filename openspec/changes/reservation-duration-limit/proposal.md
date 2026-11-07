# Proposal

## Why

Las solicitudes de reserva actualmente validan el orden del horario, el horario de operación y los conflictos, pero no limitan su duración. RF-17 establece un máximo inclusivo de cuatro horas consecutivas para cada solicitud nueva.

## What Changes

- Agregar RF-17 a la capacidad existente `reservations`: "Ninguna reserva puede durar más de cuatro horas consecutivas. Una solicitud que lo exceda responde 422 con un mensaje que indica que la reserva no puede superar cuatro horas consecutivas."
- Calcular la duración en el servicio de reservas como la diferencia entre la hora de fin y la hora de inicio. El límite es inclusivo: exactamente cuatro horas es válido.
- Validar únicamente solicitudes nuevas. Conservar la validación existente de RF-10 para duraciones cero o negativas y no revalidar reservas existentes.
- Ejecutar pruebas de RF-17 para exactamente cuatro horas, cuatro horas y un minuto, cinco horas y duración cero o negativa.
- Actualizar únicamente la fila de RF-17 en la matriz de verificación de `PLAN_INGENIERIA.md` a "Verificado" solo después de que pasen las pruebas de RF-17.
- Después de implementar RF-17, ejecutar las pruebas de regresión de RF-01 a RF-16; la tarea de regresión no se marca completa si alguna falla.
- No modificar `frontend/`, crear reservas recurrentes ni agregar excepciones por tipo de espacio o rol.

## Capabilities

### New Capabilities

### Modified Capabilities
- `reservations`: agrega RF-17 para limitar la duración de las solicitudes nuevas a cuatro horas consecutivas.

## Impact

- Servicio de reservas y pruebas del backend. La validación no se implementa en el endpoint ni en la base de datos.
- Matriz de verificación: solo se actualiza RF-17 cuando pasan sus pruebas.
- Especificación existente `openspec/specs/reservations/spec.md`.
- No se requieren cambios de esquema de base de datos ni de `frontend/`.
