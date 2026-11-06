# Plan de ingeniería de software: Sistema de gestión de reservas de espacios académicos

---

## 1. Análisis del problema

### 1.1 Problemática

Las reservas de laboratorios, auditorios y salas de cómputo se gestionan hoy por correo electrónico y hojas de cálculo compartidas. Esto genera:

- **Duplicidad de solicitudes:** la misma sala se pide por varios canales y no queda claro cuál solicitud es válida.
- **Conflictos de horario:** dos docentes pueden quedar asignados a la Sala de Cómputo 2 el martes de 10:00 a 12:00 sin que nadie lo note hasta el día de la clase.
- **Disponibilidad difícil de consultar:** saber si un auditorio está libre exige revisar varios correos y hojas.
- **Falta de trazabilidad:** no hay un registro confiable de quién reservó, cuándo ni de las cancelaciones.

### 1.2 Necesidades de la institución

- Una única fuente de verdad para las reservas.
- Impedir, por construcción, que dos reservas aprobadas del mismo espacio se traslapen.
- Consultar la disponibilidad por espacio, fecha y franja horaria.
- Saber qué persona verificada hizo cada solicitud, y cuándo.
- Restringir la aprobación de reservas al personal autorizado.
- Limitar la duración de cada reserva a cuatro horas consecutivas, por una regla de negocio que la institución solicitó en una fase posterior.

### 1.3 Actores

| Actor | Responsabilidades en el sistema |
|---|---|
| Visitante | Se registra con nombre, correo y contraseña. |
| Usuario verificado | Confirma su correo. Puede iniciar y cerrar sesión, pero no reservar. |
| Usuario habilitado (docente o estudiante) | Consulta disponibilidad, crea solicitudes y cancela sus propias reservas. |
| Administrador | Habilita o deshabilita usuarios, aprueba o rechaza solicitudes, registra espacios y promueve o revoca administradores. |
| Sistema | Envía los correos de verificación y aplica las validaciones y cambios de estado automáticos. |

El primer administrador lo crea la semilla de datos a partir de la variable `ADMIN_EMAIL`. Solo un administrador puede promover a otros.

### 1.4 Alcance y limitaciones

**Incluye:**

- Registro, verificación de correo, inicio y cierre de sesión.
- Habilitación de usuarios y gestión de roles (usuario y administrador).
- Gestión de espacios: alta y consulta.
- Consulta de disponibilidad, creación de solicitudes, aprobación, rechazo, cancelación e historial.
- Prevención de reservas simultáneas y límite de cuatro horas por reserva.

**No incluye:**

- Integración con el sistema de matrícula o con horarios académicos.
- Pagos o cobros por uso de espacios.
- Reservas recurrentes.
- Control físico de acceso.
- Aplicación móvil nativa.
- Inicio de sesión con proveedores externos.
- Recuperación de contraseña por correo.
- Rol de coordinador académico o reportes para perfiles distintos del administrador.

**Limitaciones:**

- El proyecto lo desarrolla una sola persona en un semestre.
- Los correos de verificación se envían desde una cuenta de Gmail personal con contraseña de aplicación. Esa cuenta tiene límites de envío diarios.
- El despliegue se hace en un servidor o en un hosting básico.
- El desarrollo se realiza en Windows. Los requisitos se formulan de forma que se puedan verificar en ese sistema operativo.
- La interfaz debe funcionar en navegadores modernos de escritorio y móvil.

---

## 2. Propuesta de solución

### 2.1 Descripción

Aplicación web en la que los usuarios se registran con su correo y lo verifican. Un administrador los habilita. Los usuarios habilitados consultan la disponibilidad de los espacios y solicitan reservas, que un administrador aprueba. El sistema impide que dos reservas aprobadas se traslapen, aunque las solicitudes lleguen al mismo tiempo.

### 2.2 Funcionalidades prioritarias

| Prioridad | Funcionalidades |
|---|---|
| Indispensables (MVP) | Registro, verificación, login y logout · Habilitación de usuarios · Roles y permisos · Alta y consulta de espacios · Consulta de disponibilidad · Creación de solicitudes con validación de conflictos · Aprobación y rechazo · Cancelación · Historial de reservas · Límite de cuatro horas (cambio solicitado en la Fase 4) |
| Opcionales | Notificación por correo al cambiar el estado de una reserva · Bloqueo de espacios por mantenimiento · Reportes de ocupación · Vista de calendario |

### 2.3 Módulos

1. **`auth`:** registro, verificación de correo, inicio y cierre de sesión, tokens y administrador inicial.
2. **`users`:** estados de habilitación, roles, promoción y revocación.
3. **`spaces`:** espacios con nombre, tipo, capacidad y estado.
4. **`bookings`:** solicitudes, aprobación, rechazo, cancelación y validación de traslapes.
5. **`availability`:** cálculo de franjas libres por espacio y fecha.
6. **`history`:** registro de cambios de cuentas y de reservas.

### 2.4 Desarrollo progresivo

Se construye primero la identidad (`auth` y `users`), porque las reservas dependen de saber quién solicita y quién aprueba. Después se construyen los espacios y las reservas con su validación de traslapes, que es el núcleo del problema. La interfaz web va después, cuando la API está estable. El límite de cuatro horas se incorpora al final, como un cambio gestionado con OpenSpec.

Este orden evita escribir un mecanismo de identidad temporal que luego habría que reemplazar, y deja las reglas de permisos probadas contra la autenticación real.

### 2.5 Requisitos

Cada requisito tiene un identificador que se usa en las especificaciones de OpenSpec, en las pruebas y en la matriz de verificación (sección 5.3).

#### 2.5.1 Requisitos funcionales

**Etapa 1: identidad**

| ID | Requisito |
|---|---|
| RF-01 | Un visitante se registra con nombre, correo y contraseña de al menos 12 caracteres. El correo es único sin distinguir mayúsculas. El usuario queda en estado `PENDIENTE_VERIFICACION` y recibe un enlace de verificación de un solo uso, con un token de al menos 256 bits que caduca en 24 horas. Un reenvío invalida el enlace anterior y solo puede pedirse cada 2 minutos. Al verificarlo, el estado pasa a `VERIFICADO`. |
| RF-02 | Un usuario verificado inicia sesión y recibe un token JWT de 60 minutos. Un usuario sin verificar recibe `403` con el mensaje "cuenta no verificada". Las credenciales incorrectas responden con un mensaje genérico que no revela si el correo existe. |
| RF-03 | El usuario cierra sesión y el servidor revoca el token hasta su vencimiento. Cualquier petición posterior con ese token responde `401`. |
| RF-04 | El administrador habilita o deshabilita usuarios. Las transiciones válidas son `VERIFICADO → HABILITADO` y `HABILITADO ⇄ DESHABILITADO`. Cualquier otra transición responde `409`. |
| RF-05 | Solo un administrador promueve a otro usuario verificado a administrador o le revoca el rol. Nadie se promueve a sí mismo. No se puede revocar el rol al último administrador activo. |
| RF-06 | La semilla crea el primer administrador con el correo de `ADMIN_EMAIL`, en estado `VERIFICADO` y sin contraseña. Genera un enlace de activación de un solo uso, válido 24 horas, y lo escribe en un archivo de texto en la ruta indicada por la variable `SECRETS_DIR`, que debe apuntar fuera del repositorio. La carpeta `secrets/` está además incluida en `.gitignore` como medida adicional. El enlace nunca se imprime en consola ni se registra en logs. El archivo se elimina al usarse. |
| RF-07 | Cada cambio de estado de un usuario (creación, verificación, habilitación, deshabilitación) y cada cambio de rol queda registrado con: usuario afectado, responsable del cambio, fecha y hora en UTC, valor anterior y valor nuevo. Los registros no se editan ni se borran. |

**Etapa 2: espacios y reservas**

| ID | Requisito |
|---|---|
| RF-08 | El administrador registra espacios con nombre, tipo (`LABORATORIO`, `AUDITORIO` o `SALA_COMPUTO`), capacidad y estado (`ACTIVO` o `INACTIVO`). Los usuarios habilitados consultan la lista de espacios. |
| RF-09 | Un usuario habilitado consulta las franjas ocupadas y libres de un espacio para una fecha. Un usuario no habilitado recibe `403`. |
| RF-10 | Un usuario habilitado crea una solicitud con espacio, fecha, hora de inicio y hora de fin. La hora de fin debe ser posterior a la de inicio. La solicitud nace en estado `PENDIENTE`. |
| RF-11 | Una solicitud que se traslape con una reserva `APROBADA` del mismo espacio responde `409` e indica con cuál reserva hay conflicto. Dos reservas se traslapan solo si comparten tiempo real: 10:00–12:00 y 12:00–14:00 no se traslapan. |
| RF-12 | El sistema acepta solicitudes `PENDIENTE` que se traslapen entre sí. Al aprobar una, las `PENDIENTE` del mismo espacio que se traslapen con ella pasan a `RECHAZADA` con el motivo "conflicto con reserva aprobada". |
| RF-13 | Solo el administrador aprueba o rechaza solicitudes. Cualquier otra acción de ese tipo responde `403`. |
| RF-14 | El solicitante cancela sus propias reservas. Al cancelar una reserva `APROBADA`, el espacio queda libre de inmediato. Los estados `RECHAZADA` y `CANCELADA` son finales. |
| RF-15 | Al deshabilitar a un usuario, sus solicitudes `PENDIENTE` y sus reservas `APROBADA` futuras pasan a `CANCELADA` con el motivo "usuario deshabilitado". |
| RF-16 | Cada cambio de estado de una reserva queda registrado con: identificador de la reserva, responsable, fecha y hora en UTC, estado anterior, estado nuevo y motivo (obligatorio en rechazos, cancelaciones y deshabilitaciones). Los registros no se editan ni se borran. |
| RF-18 | El solicitante consulta el listado de sus propias reservas, y el administrador consulta el de todas, con estado, espacio, fecha y horario. Un usuario sin permiso recibe `403`. |

**Fase 4: cambio solicitado por la institución**

| ID | Requisito |
|---|---|
| RF-17 | Ningún usuario puede reservar un espacio por más de cuatro horas consecutivas. Una solicitud que lo exceda responde `422`. |

#### 2.5.2 Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF-01 | La consulta de disponibilidad responde en menos de 2 segundos con 500 reservas cargadas. |
| RNF-02 | Las contraseñas se guardan con bcrypt. Ni las contraseñas ni los tokens aparecen en logs, en respuestas de error ni en la salida de consola. |
| RNF-03 | Las fechas se guardan en UTC y se muestran en la zona horaria institucional. |
| RNF-04 | La clave JWT, la contraseña SMTP, `ADMIN_EMAIL` y `SECRETS_DIR` se leen de variables de entorno, nunca del código. |
| RNF-05 | La cobertura de pruebas es de al menos 80 % en los módulos `auth`, `users`, `bookings` y `availability`. |
| RNF-06 | La aplicación completa (API, base de datos y migraciones) se levanta con un solo comando de Docker Compose. |
| RNF-07 | La interfaz funciona en navegadores modernos de escritorio y móvil. |

---

## 3. Arquitectura y tecnología

### 3.1 Arquitectura seleccionada

Monolito modular por capas: API, servicios de negocio y repositorios de datos, en un solo despliegue.

**Justificación:** el sistema tiene un alcance acotado y un solo desarrollador. Los microservicios añadirían comunicación entre servicios, despliegues separados y trazas distribuidas, sin un beneficio proporcional a este tamaño. La separación en módulos y capas mantiene el código ordenado y permite migrar a otra arquitectura si fuera necesario.

### 3.2 Stack tecnológico

| Área | Tecnología | Uso |
|---|---|---|
| Lenguaje | Python 3.12 | Backend. |
| Framework | FastAPI con Pydantic | API REST y validación de entradas. |
| ORM y migraciones | SQLAlchemy 2.0 y Alembic | Acceso a datos y versionado del esquema. |
| Base de datos | PostgreSQL 16 | Persistencia y restricciones de integridad. |
| Seguridad | bcrypt para contraseñas; JWT (PyJWT) con vigencia de 60 minutos | Autenticación. |
| Frontend | React con Vite | Interfaz web (alternativa: plantillas Jinja2 si el tiempo no alcanza). |
| Pruebas | pytest (unitarias e integración); Playwright (end-to-end) | Verificación automatizada. |
| Entorno | Docker Compose | Ejecución local y en CI con la misma base de datos. |
| Integración continua | GitHub Actions | Ejecución de pruebas en cada cambio. |
| Especificación | OpenSpec | Especificaciones y registro de cambios. |
| Correo | Mailpit en desarrollo; SMTP de Gmail en demostración | Envío de enlaces de verificación. |

### 3.3 Estrategia de persistencia

Se usa PostgreSQL. La integridad de las reservas se garantiza en la propia base de datos con una restricción de exclusión sobre rangos de tiempo, que impide que dos reservas aprobadas del mismo espacio se traslapen aunque lleguen al mismo tiempo:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE reservations ADD CONSTRAINT no_overlap
EXCLUDE USING gist (space_id WITH =, tstzrange(start_at, end_at) WITH &&)
WHERE (status = 'APPROVED');
```

Un índice único sobre el correo en minúsculas impide cuentas duplicadas. Las fechas se guardan en UTC.

### 3.4 Organización de componentes

- **Cliente web (React):** interfaz para visitantes, usuarios y administradores. Consume la API.
- **API (FastAPI):** endpoints, validación de entradas y verificación del token y del rol.
- **Capa de servicios:** reglas de negocio: traslapes, transiciones de estado, habilitación y promoción.
- **Capa de persistencia (SQLAlchemy):** repositorios sobre PostgreSQL.
- **Servicio de correo:** envía los enlaces de verificación por SMTP.

Para crear una reserva, el cliente envía su token. La API verifica que el token no esté revocado, que el rol sea correcto y que el usuario esté habilitado. El servicio comprueba los traslapes y el repositorio guarda la reserva. PostgreSQL aplica la restricción como garantía final.

### 3.5 Decisiones técnicas comparadas

| Decisión | Elegida | Alternativas descartadas | Justificación |
|---|---|---|---|
| Base de datos | PostgreSQL | Hojas de cálculo (Google Sheets, Excel); SQLite | Las hojas no tienen control de concurrencia ni restricciones. SQLite no soporta la restricción `EXCLUDE USING gist` que necesita el sistema. |
| Framework backend | FastAPI | Django; Flask | FastAPI ofrece validación tipada y documentación automática con poco código. Django es más pesado de lo necesario para una API. Flask exige más código manual. |
| Prevención de traslapes | Validación en el servicio y restricción en la base de datos | Solo validación en la aplicación | El servicio da mensajes claros al usuario. Solo la restricción de la base de datos protege contra condiciones de carrera. |
| Orden de construcción | Autenticación antes que reservas | Reservas con una identidad temporal | Evita escribir y probar un mecanismo temporal que luego habría que reemplazar. |

---

## 4. Estrategia de desarrollo

### 4.1 Metodología

Desarrollo iterativo e incremental guiado por SDD con OpenSpec. Cada requisito de la sección 2.5 se escribe primero como especificación con escenarios verificables, después se implementa y finalmente se verifica con pruebas automatizadas.

Este plan se entrega en un commit independiente y anterior a cualquier especificación o código, para que el historial de Git demuestre la secuencia.

### 4.2 Etapas de implementación

| Etapa | Contenido | Requisitos | Duración |
|---|---|---|---|
| 0 | Repositorio, Docker Compose, CI, OpenSpec inicializado, `.gitignore` con `secrets/` | RNF-06 | 1 semana |
| 1 | Registro, verificación, login, logout, habilitación, roles, administrador inicial e historial de cuentas | RF-01 a RF-07 | 4 semanas |
| 2 | Espacios, disponibilidad, solicitudes, traslapes, aprobación, cancelación e historial de reservas | RF-08 a RF-16 | 4 semanas |
| 3 | Interfaz web | RNF-07 | 3 semanas |
| 4 | Cambio de límite de cuatro horas (RF-17) y cierre | RF-17 | 1 semana |

**Total: 13 semanas.** Si el semestre es más corto, se recorta primero la etapa 4 y después la interfaz se simplifica con plantillas.

### 4.3 Orden de funcionalidades

Primero la identidad, porque todas las reglas de reserva dependen de saber quién actúa. Después el núcleo del problema, que son los espacios y las reservas con validación de traslapes. La interfaz va cuando la API está estable. El cambio de cuatro horas se incorpora al final, siguiendo el proceso de la sección 6.6.

### 4.4 Dependencias

- Las reservas dependen del inicio de sesión (RF-02) y de la habilitación (RF-04).
- La habilitación depende de la verificación del correo (RF-01).
- La promoción de administradores depende del administrador inicial (RF-06).
- La cancelación en cascada (RF-15) depende de que existan reservas.
- La interfaz depende de la API estable de las etapas 1 y 2.

### 4.5 Criterios de terminado por etapa

Una etapa se considera terminada cuando:

- Todos sus requisitos tienen especificación en OpenSpec, con sus escenarios.
- Sus pruebas pasan en GitHub Actions.
- Cumple la cobertura de RNF-05 en los módulos de la etapa.
- No quedan errores críticos abiertos.
- El código fue revisado por el estudiante antes de integrarse a `main`.
- La matriz de verificación (5.3) está actualizada para sus requisitos.

---

## 5. Estrategia de calidad

### 5.1 Tipos de pruebas

| Tipo | Qué verifica | Ejemplo |
|---|---|---|
| Unitarias | Lógica de traslapes, transiciones de estado y formatos | Las reservas 10:00–12:00 y 12:00–14:00 no se traslapan (RF-11). |
| Integración | API y PostgreSQL reales | Insertar dos reservas aprobadas traslapadas debe fallar en la base de datos (RF-11). |
| Concurrencia | Aprobaciones simultáneas | Dos solicitudes pendientes que se traslapan se aprueban a la vez: solo una queda `APROBADA` (RF-11, RF-12). |
| Flujo de cuentas | Registro, verificación, login y logout | Un enlace de verificación usado dos veces responde error la segunda vez (RF-01). Un token usado tras logout responde `401` (RF-03). |
| Seguridad de secretos | Salida de consola, logs y control de versiones | Ejecutar la semilla no imprime el enlace; el archivo está fuera del repositorio y Git no lo rastrea (RF-06, RNF-02). |
| Autorización | Permisos por rol y estado | Un usuario que intenta aprobar una solicitud recibe `403` (RF-13). Un usuario no habilitado que reserva recibe `403` (RF-09, RF-10). |
| Historial | Registro de cambios | Aprobar una reserva genera un registro con estado anterior y nuevo (RF-16). |
| End-to-end | Flujo completo en el navegador | Registro, verificación, habilitación, solicitud y aprobación (RF-01 a RF-13). |

### 5.2 Riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Errores en los bordes de horario o en las zonas horarias | Media | Alto | Pruebas con casos límite y almacenamiento en UTC (RNF-03). |
| R2 | Reservas duplicadas por condiciones de carrera | Media | Alto | Restricción `EXCLUDE` en PostgreSQL y prueba de concurrencia (RF-11). |
| R3 | Alcance excesivo que impide terminar el MVP | Alta | Alto | MVP definido en la etapa 0. Los opcionales solo se empiezan después de la etapa 3. |
| R4 | Código generado por IA que no cumple la especificación | Media | Medio | Revisión manual de cada cambio, CI obligatorio y revisión contra la especificación. |
| R5 | Pérdida de datos o fallas en el despliegue | Baja | Alto | Respaldo diario con `pg_dump`, migraciones versionadas con Alembic y base de datos de pruebas separada. |
| R6 | Fallas de seguridad en la autenticación | Media | Alto | bcrypt (RNF-02), tokens con vigencia y revocación (RF-02, RF-03), enlaces de un solo uso (RF-01). |
| R7 | Bloqueo o límite de envío de la cuenta de Gmail | Media | Medio | Mailpit en desarrollo. El proveedor SMTP se configura por variables de entorno (RNF-04). |
| R8 | Pérdida de acceso del único administrador | Baja | Alto | Regla de último administrador (RF-05) y semilla para recrear el acceso (RF-06). |

### 5.3 Verificación del cumplimiento de requisitos

Cada requisito se rastrea en una matriz que relaciona su identificador con el módulo que lo implementa, la prueba que lo valida y el estado. Un requisito se marca como verificado solo cuando su prueba pasa en CI y el estudiante ha revisado la implementación contra la especificación.

| ID | Módulo | Prueba que lo valida | Etapa | Estado |
|---|---|---|---|---|
| RF-01 | `auth` | Correo duplicado en mayúsculas se rechaza; enlace usado dos veces falla; reenvío dentro de 2 minutos se rechaza | 1 | Pendiente |
| RF-02 | `auth` | Login sin verificar → `403`; credenciales erróneas dan el mismo mensaje | 1 | Pendiente |
| RF-03 | `auth` | Token usado después de logout → `401` | 1 | Pendiente |
| RF-04 | `users` | Transiciones inválidas responden `409` | 1 | Pendiente |
| RF-05 | `users` | Autopromoción y revocación del último administrador se rechazan | 1 | Pendiente |
| RF-06 | `auth` | La semilla crea el administrador sin contraseña; `git check-ignore` confirma que `secrets/` está ignorado; `git status` no lista el archivo del enlace; la ruta resuelta de `SECRETS_DIR` no está dentro del repositorio; el enlace no aparece en consola ni en logs | 1 | Pendiente |
| RF-07 | `history` | Cada cambio de estado de usuario genera un registro, incluida la verificación | 1 | Pendiente |
| RF-08 | `spaces` | Alta con tipo inválido se rechaza | 2 | Pendiente |
| RF-09 | `availability` | Usuario no habilitado recibe `403` | 2 | Pendiente |
| RF-10 | `bookings` | Fin anterior o igual al inicio se rechaza | 2 | Pendiente |
| RF-11 | `bookings`, BD | Traslape con aprobada responde `409`; borde 12:00 aceptado; dos aprobaciones simultáneas no pasan | 2 | Pendiente |
| RF-12 | `bookings` | Dos pendientes traslapadas se crean; al aprobar una, la otra queda `RECHAZADA` con motivo | 2 | Pendiente |
| RF-13 | `bookings` | Solicitante que aprueba recibe `403` | 2 | Pendiente |
| RF-14 | `bookings` | Cancelar una reserva rechazada responde error; cancelar una aprobada libera el espacio | 2 | Pendiente |
| RF-15 | `users`, `bookings` | Deshabilitar cancela pendientes y aprobadas futuras | 2 | Pendiente |
| RF-16 | `history` | Cambio de estado de reserva genera registro; `UPDATE` sobre el historial falla | 2 | Pendiente |
| RF-17 | `bookings` | Reserva de 4 horas y 1 minuto responde `422` | 4 | Pendiente |
| RNF-01 | `availability` | Consulta con 500 reservas responde en menos de 2 segundos | 2 | Pendiente |
| RNF-02 | `auth` | Hash bcrypt verificado; ausencia de tokens y contraseñas en logs | 1 | Pendiente |
| RNF-03 | Todos | Fechas guardadas en UTC | 2 | Pendiente |
| RNF-04 | Configuración | Arranque sin variables obligatorias falla con mensaje claro | 1 | Pendiente |
| RNF-05 | CI | Reporte de cobertura ≥ 80 % | 1 y 2 | Pendiente |
| RNF-06 | Raíz del repositorio | `docker compose up` levanta todos los servicios | 0 | Pendiente |
| RNF-07 | Frontend | Prueba end-to-end en escritorio y en vista móvil | 3 | Pendiente |

---

## 6. Uso de SDD e inteligencia artificial

### 6.1 Uso de OpenSpec

OpenSpec es la fuente de verdad del sistema. El repositorio contiene una carpeta `openspec/` con una especificación por módulo (`auth.md`, `users.md`, `spaces.md`, `bookings.md`, `availability.md`, `history.md`). Cada especificación incluye su propósito, sus requisitos con los identificadores de la sección 2.5 y sus escenarios de aceptación. Los cambios se proponen en OpenSpec antes de programarse, se dividen en tareas y quedan registrados en el historial de cambios.

Regla de trabajo: cualquier cambio de comportamiento empieza actualizando la especificación. No se modifica código sin antes actualizar su especificación.

### 6.2 Transformación del plan en especificaciones

Cada necesidad de la sección 1.2 se convierte en uno o más requisitos, y cada requisito en escenarios concretos. Por ejemplo, la necesidad de impedir reservas traslapadas se convierte en RF-11:

> **RF-11:** Una solicitud que se traslape con una reserva aprobada del mismo espacio responde `409`.
> - Escenario 1: existe una reserva aprobada de 10:00 a 12:00; una solicitud de 11:00 a 13:00 → `409`, indica la reserva en conflicto.
> - Escenario 2: existe una reserva aprobada de 10:00 a 12:00; una solicitud de 12:00 a 14:00 → aceptada.
> - Escenario 3: existe una reserva cancelada de 10:00 a 12:00; una solicitud de 10:00 a 12:00 → aceptada.

Cada escenario se convierte en una prueba automatizada cuyo nombre incluye el identificador del requisito, por ejemplo `test_rf11_traslape_con_aprobada_responde_409`.

### 6.3 Actividades delegadas a la IA

- Generar modelos, esquemas Pydantic y endpoints CRUD a partir de la especificación.
- Escribir pruebas unitarias a partir de escenarios ya definidos.
- Proponer refactorizaciones y revisar el estilo del código.
- Redactar documentación técnica preliminar.
- Revisar consultas SQL y configuraciones en busca de errores comunes.

### 6.4 Verificación del código generado

Ningún código generado por IA entra al repositorio sin revisión. El proceso es:

1. Comprobar que el código cumple el escenario correspondiente de la especificación, indicando su identificador.
2. Revisar línea por línea la lógica crítica: traslapes, permisos, habilitación, manejo de tokens y del enlace de activación, y hash de contraseñas.
3. Ejecutar las pruebas localmente y en CI.
4. Verificar que no haya dependencias innecesarias, código muerto ni secretos en el repositorio.
5. Probar manualmente los flujos principales desde la interfaz.

Si el código no cumple la especificación, se corrige o se reescribe, aunque pase las pruebas.

### 6.5 Decisiones que son responsabilidad del estudiante

- La elección del stack y de la arquitectura, con su justificación.
- Las reglas de negocio: que las solicitudes pendientes traslapadas se permitan y que, al aprobar una, las demás se rechacen (RF-12); que al cancelar una reserva aprobada el espacio se libere de inmediato (RF-14).
- El modelo de datos y sus restricciones de integridad.
- Qué entra en el MVP y qué queda fuera.
- La estrategia de seguridad y de manejo de errores.
- La aprobación final de cada etapa y de cada cambio a las especificaciones.

La IA puede proponer alternativas, pero la decisión y su justificación deben ser del estudiante, porque debe poder defenderlas en la sustentación.

### 6.6 Gestión del cambio de cuatro horas

Cuando la institución solicita la regla de cuatro horas (Fase 4), el cambio se gestiona así:

1. **Análisis de impacto:** la regla afecta la validación de solicitudes (RF-10), la matriz de verificación (sección 5.3) y las pruebas de concurrencia, porque una reserva más larga puede traslapar más solicitudes. No cambia las decisiones de arquitectura ni el stack.
2. **Actualización de la especificación:** se crea un cambio en OpenSpec que añade RF-17 a la especificación de `bookings`, con sus escenarios.
3. **Escenarios de aceptación:** duración de exactamente cuatro horas, aceptada; cuatro horas y un minuto, rechazada con `422`; duración de cero o negativa, rechazada como antes.
4. **Implementación y pruebas:** se implementa la regla y se agregan las pruebas de RF-17.
5. **Regresión:** se ejecutan todas las pruebas de los requisitos RF-01 a RF-16 para confirmar que nada existente se rompió.
6. **Registro:** el cambio queda en el historial de OpenSpec y en la matriz de verificación.
