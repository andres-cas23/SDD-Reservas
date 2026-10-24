# Plan de ingeniería: Sistema de reservas de espacios académicos

## 1. Análisis del problema

**1.1 Problemática.** Hoy las reservas de laboratorios, auditorios y salas de cómputo se hacen por correo y hojas de cálculo compartidas. Problemas concretos:

- La misma sala se solicita por varios canales y no queda claro cuál solicitud es válida.
- Dos docentes pueden quedar asignados a la Sala de Cómputo 2 el martes de 10:00 a 12:00 sin que nadie lo note hasta el día de la clase.
- Para saber si un auditorio está libre hay que revisar varios correos y hojas distintas.
- No hay registro de quién reservó, cuándo, ni de cancelaciones.

**1.2 Necesidades.**

- Una única fuente de verdad para todas las reservas.
- Imposibilidad de reservar un mismo espacio en horarios que se traslapan.
- Consulta de disponibilidad por espacio, fecha y franja horaria.
- Registro de autor, fecha de creación y cambios de cada reserva.
- Permisos por rol: solo el administrador aprueba o rechaza.

**1.3 Actores.**

| Actor | Qué hace en el sistema |
|---|---|
| Solicitante (docente o estudiante) | Consulta disponibilidad, crea solicitudes, cancela sus propias reservas. |
| Administrador de espacios | Aprueba o rechaza solicitudes, registra espacios. |
| Coordinador académico | Consulta reportes de ocupación (solo lectura). |
| Sistema | Valida conflictos y cambia estados automáticamente. |

**1.4 Alcance y limitaciones.**

- **Incluye:** CRUD de espacios, disponibilidad, solicitudes con aprobación, autenticación por rol, historial básico.
- **No incluye:** integración con el sistema de matrícula, pagos, reservas recurrentes tipo iCal, app móvil nativa, inventario de equipos.
- **Restricciones:** un desarrollador, un semestre, autenticación propia (la institución no tiene proveedor de identidad), despliegue en un servidor o hosting básico, navegadores modernos de escritorio y móvil.

---

## 2. Propuesta de solución

**2.1 Descripción.** Aplicación web donde los solicitantes ven la disponibilidad de cada espacio y envían solicitudes, y los administradores las aprueban. El sistema rechaza cualquier reserva que se traslape con una aprobada.

**2.2 Funcionalidades.**

| Prioridad | Funcionalidad |
|---|---|
| MVP | Login con roles · CRUD de espacios · Consulta de disponibilidad · Crear solicitud con validación de conflicto · Aprobar/rechazar · Cancelar |
| Opcional | Correo al cambiar estado · Bloqueo por mantenimiento · Reporte de ocupación mensual · Vista de calendario semanal |

**2.3 Módulos.**

1. `auth`: registro, login, roles.
2. `spaces`: espacios con tipo, capacidad, ubicación y estado activo/inactivo.
3. `bookings`: solicitudes, aprobación, cancelación y validación de traslapes.
4. `availability`: calcula franjas libres por espacio y día.
5. `reports` (opcional): ocupación por espacio y periodo.

**2.4 Desarrollo progresivo.** Primero `spaces` + `bookings` con validación de traslapes, porque sin eso el sistema no resuelve el problema. Luego `auth` para controlar quién aprueba. Al final, las funciones opcionales.

---

## 3. Arquitectura y tecnología

**3.1 Arquitectura.** Monolito modular por capas (API → servicios → repositorios). Un solo despliegue, sin microservicios: con un desarrollador, la complejidad operativa de los microservicios no se justifica.

**3.2 Stack.**

| Área | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Backend | FastAPI + Pydantic |
| ORM y migraciones | SQLAlchemy 2.0 + Alembic |
| Base de datos | PostgreSQL 16 |
| Frontend | React + Vite (alternativa si se acaba el tiempo: plantillas Jinja2) |
| Pruebas | pytest (unitarias e integración), Playwright (end-to-end) |
| Entorno | Docker Compose |
| CI | GitHub Actions |
| Especificación | OpenSpec |

**3.3 Persistencia.** PostgreSQL con una restricción de exclusión:

```sql
ALTER TABLE reservations ADD CONSTRAINT no_overlap
EXCLUDE USING gist (space_id WITH =, tstzrange(start_at, end_at) WITH &&)
WHERE (status = 'APPROVED');
```

Esto garantiza que dos reservas aprobadas del mismo espacio no se traslapen, aunque lleguen al mismo milisegundo. Las fechas se guardan en UTC y se muestran en la zona horaria institucional.

**3.4 Componentes.** El cliente React consume la API REST. FastAPI valida el token JWT y el rol. La capa de servicios verifica disponibilidad y transiciones de estado. SQLAlchemy persiste en PostgreSQL, que aplica la restricción como garantía final.

**3.5 Decisiones comparadas.**

| Decisión | Elegida | Descartada | Motivo |
|---|---|---|---|
| Base de datos | PostgreSQL | Google Sheets, SQLite | Sheets no tiene concurrencia ni restricciones; SQLite no soporta `EXCLUDE USING gist`. |
| Framework | FastAPI | Django, Flask | FastAPI da validación y documentación automática con poco código; Django es más pesado para una API; Flask exige más código manual. |
| Validación de traslapes | Servicio + restricción en BD | Solo servicio | El servicio da mensajes claros; solo la BD protege contra condiciones de carrera. |

---

## 4. Estrategia de desarrollo

**4.1 Metodología.** Iterativa e incremental con SDD: cada funcionalidad se escribe primero en OpenSpec, luego se implementa y se verifica con pruebas.

**4.2 Etapas.**

| Etapa | Entregable | Duración estimada |
|---|---|---|
| 0 | Repo, Docker, CI y specs base en OpenSpec | 1 semana |
| 1 | Espacios, reservas y validación de traslapes | 3 semanas |
| 2 | Flujo de estados: pendiente → aprobada / rechazada / cancelada | 2 semanas |
| 3 | Login, registro y permisos por rol | 2 semanas |
| 4 | Interfaz web (disponibilidad, solicitud, gestión) | 3 semanas |
| 5 | Opcionales y documentación final | 2 semanas (reserva) |

**4.3 Orden.** Lo central primero (traslapes y disponibilidad), luego acceso (roles), luego conveniencia (correos, reportes). Si el tiempo se agota, el MVP ya resuelve el problema.

**4.4 Dependencias.**

- Aprobación depende de traslapes y de roles.
- La interfaz depende de la API estable de las etapas 1 a 3.
- Los correos dependen de la máquina de estados de la etapa 2.

**4.5 Criterios de terminado por etapa.**

- Specs de la etapa marcadas como cumplidas en OpenSpec.
- Pruebas en verde en GitHub Actions.
- Cobertura ≥ 80 % en la lógica de `bookings` y `availability`.
- Cero errores críticos abiertos.
- Código revisado por mí antes de hacer merge a `main`.

---

## 5. Calidad

**5.1 Pruebas.**

| Tipo | Qué prueba | Ejemplo concreto |
|---|---|---|
| Unitarias | Lógica de traslape y transiciones | Reserva 10:00–12:00 y otra 12:00–14:00 **no** se traslapan. |
| Integración | API + PostgreSQL real | Insertar dos reservas traslapadas directamente en BD y verificar que la restricción falle. |
| Concurrencia | Dos solicitudes simultáneas | Dos hilos reservan la misma sala a las 10:00; solo uno obtiene `201`. |
| End-to-end | Flujo completo en el navegador | Docente solicita → admin aprueba → aparece en la disponibilidad. |
| Autorización | Permisos | Un solicitante que hace `PATCH /bookings/{id}/approve` recibe `403`. |

**5.2 Riesgos.**

| # | Riesgo | Prob. | Impacto | Mitigación concreta |
|---|---|---|---|---|
| R1 | Error en bordes de horario o zonas horarias | Media | Alto | Casos límite en pruebas unitarias; todo en UTC. |
| R2 | Reservas duplicadas por concurrencia | Media | Alto | Restricción `EXCLUDE` en PostgreSQL + prueba de concurrencia. |
| R3 | Alcance excesivo, MVP sin terminar | Alta | Alto | MVP congelado en la etapa 0; opcionales solo tras cerrar la etapa 3. |
| R4 | Código de IA incorrecto o que no cumple la spec | Media | Medio | Revisión manual, CI obligatorio, checklist contra la spec. |
| R5 | Pérdida de datos en despliegue | Baja | Alto | `pg_dump` diario, migraciones con Alembic, BD de pruebas separada. |
| R6 | Fallas de seguridad en login | Media | Alto | bcrypt para contraseñas, JWT con expiración de 60 min, pruebas de autorización. |
| R7 | Cambios de requisitos de la institución | Media | Medio | Cambios solo mediante nueva versión de spec en OpenSpec. |

**5.3 Verificación.** Una matriz de trazabilidad (hoja de cálculo o tabla en el README) con columnas: *requisito de OpenSpec → decisión que lo sustenta → archivo de código → prueba que lo valida → estado*. Un requisito se marca "verificado" solo cuando su prueba pasa en CI y lo he revisado.

---

## 6. SDD e IA

**6.1 OpenSpec.** Una carpeta `openspec/` en el repo con una spec por módulo (`bookings.md`, `spaces.md`, etc.). Cada spec contiene propósito, requisitos numerados (RF-01, RF-02…) y escenarios en formato Dado/Cuando/Entonces. Cambiar comportamiento exige cambiar la spec primero.

**6.2 De plan a spec.** Ejemplo de conversión:

> **Necesidad:** "evitar conflictos de horario".
> **RF-03:** El sistema rechaza una solicitud si se traslapa con una reserva aprobada del mismo espacio.
> - Escenario 1: 10:00–12:00 existente, nueva 11:00–13:00 → rechazada.
> - Escenario 2: existente 10:00–12:00, nueva 12:00–14:00 → aceptada.
> - Escenario 3: existente cancelada, nueva 10:00–12:00 → aceptada.

Cada escenario se convierte en una prueba.

**6.3 Lo que delego a la IA.** Modelos y esquemas Pydantic, endpoints CRUD, pruebas unitarias a partir de escenarios ya escritos, documentación preliminar y revisión de estilo.

**6.4 Cómo reviso el código generado.**

1. ¿Cumple el escenario de la spec? Sí/no, con referencia al ID.
2. Línea por línea en: validación de traslapes, permisos, hash de contraseñas.
3. CI en verde, y prueba manual de los flujos principales.
4. Sin dependencias sobrantes, código muerto ni secretos en el repo.

Si no cumple la spec, lo reescribo; no lo acepto solo porque pasa las pruebas.

**6.5 Decisiones mías.**

- Stack y arquitectura, con su justificación.
- Reglas de negocio, por ejemplo: si se cancela una reserva aprobada, ¿se libera el espacio de inmediato? (Decisión: sí, y queda en el historial.)
- Modelo de datos y restricciones.
- Qué entra y qué sale del MVP.
- Aprobación final de cada etapa y de cada cambio a las specs.
