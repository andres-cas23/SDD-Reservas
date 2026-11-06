# SDD Reservas: identidad API

Etapa 1 implementa el registro, la verificación de correo, la autenticación y la administración de usuarios por API. No incluye interfaz gráfica ni endpoints de reservas.

## Requisitos

- Python 3.12 o posterior
- Docker Compose

## Inicio local

1. Crea la configuración local y edita los valores:

   ```powershell
   Copy-Item .env.example .env
   ```

   Usa un `JWT_SECRET` aleatorio de al menos 32 caracteres y una `SECRETS_DIR` absoluta que esté fuera del repositorio. La configuración de ejemplo de SMTP está preparada para Mailpit.

2. Instala la API y las herramientas de pruebas:

   ```powershell
   python -m pip install -e ".[dev]"
   ```

3. Inicia PostgreSQL y Mailpit:

   ```powershell
   docker compose up -d db mailpit
   ```

4. Aplica la migración inicial y ejecuta la API:

   ```powershell
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

   Mailpit queda disponible en `http://localhost:8025`; la API en `http://localhost:8000`. La documentación interactiva está en `/docs`.

5. Crea el administrador inicial:

   ```powershell
   python -m app.seed_admin
   ```

   La semilla usa `ADMIN_EMAIL` y escribe el enlace de activación en `admin-activation.txt` dentro de `SECRETS_DIR`. No muestra el enlace en consola. Al activar la cuenta, el administrador define una contraseña de al menos 12 caracteres y el archivo se elimina.

## API de identidad

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/auth/register` | Registro; envía el enlace de verificación |
| `POST` | `/auth/verify` | Verificación con `{"token":"..."}` |
| `POST` | `/auth/resend-verification` | Reenvío con `{"email":"..."}` |
| `POST` | `/auth/login` | Login; devuelve un JWT de 60 minutos |
| `POST` | `/auth/logout` | Revoca el JWT bearer actual |
| `POST` | `/auth/activate-admin` | Activación con `{"token":"...","password":"..."}` |
| `GET` | `/users` | Lista usuarios; requiere administrador |
| `PATCH` | `/users/{id}/status` | Cambia el estado permitido; requiere administrador |
| `PATCH` | `/users/{id}/role` | Cambia el rol; requiere administrador |
| `GET` | `/users/{id}/history` | Consulta auditoría; requiere administrador |

Los tokens de verificación y activación se ubican en el fragmento (`#token=...`) del enlace, que no se envía al servidor ni aparece en los logs de acceso. Para completar los flujos API, se copia el token del fragmento y se envía en el cuerpo JSON del endpoint correspondiente. Los tokens se guardan en la base de datos solo como hashes.

Los secretos se configuran mediante variables de entorno (o `.env` local, ignorado por Git). Las credenciales y los tokens no deben incluirse en logs. En despliegues reales, proporciona credenciales y URLs de PostgreSQL/SMTP específicas del entorno y guarda `SECRETS_DIR` fuera del repositorio.

## Pruebas y cobertura

Las pruebas de `pytest` usan SQLite en memoria mediante `tests/conftest.py`; no se conectan a la base PostgreSQL de desarrollo. Para pruebas de migraciones o integración con PostgreSQL hay un servicio aislado `test-db`, con la base `reservas_test` en el puerto `5433` y un volumen separado:

```powershell
docker compose --profile test up -d test-db
$env:DATABASE_URL = "postgresql+psycopg://reservas:reservas@localhost:5433/reservas_test"
alembic upgrade head
```

Los downgrades de migraciones deben ejecutarse únicamente con esa URL de pruebas configurada, nunca con la URL de desarrollo que apunta a `localhost:5432/reservas`. Por ejemplo:

```powershell
alembic downgrade base
Remove-Item Env:DATABASE_URL
```

Al terminar, se puede detener el servicio de pruebas sin afectar la base de desarrollo:

```powershell
docker compose --profile test stop test-db
```

```powershell
python -m pytest --cov=app --cov-report=term-missing
```

La configuración exige una cobertura mínima del 80 % del paquete `app`.

## API de espacios

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/spaces` | Registra un espacio; requiere administrador |
| `GET` | `/spaces` | Lista espacios; requiere usuario HABILITADO |
| `GET` | `/spaces/{space_id}/availability?date=YYYY-MM-DD` | Consulta franjas ocupadas y libres; requiere usuario HABILITADO |

El registro recibe `{"name":"Auditorio","type":"AUDITORIO","capacity":120,"status":"ACTIVO"}`. Los tipos admitidos son `LABORATORIO`, `AUDITORIO` y `SALA_COMPUTO`; los estados son `ACTIVO` e `INACTIVO`. El nombre no puede estar vacío y la capacidad debe ser positiva. Los datos no válidos responden `422`; un usuario sin rol de administrador recibe `403`.

La lista devuelve los espacios ordenados por nombre e incluye el estado de cada uno. La disponibilidad recibe una fecha académica en `America/Bogota` y devuelve `space_id`, `date`, `occupied` y `free`, como listas de intervalos con `start` y `end`. Solo las reservas `APROBADA` ocupan franjas. La ventana diaria es de 07:00 a 21:00; un día sin reservas devuelve ocupación vacía y una franja libre de 07:00 a 21:00. Un espacio inexistente responde `404` y una cuenta no HABILITADA responde `403`.

## API de reservas

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/reservations` | Crea una solicitud PENDIENTE; requiere usuario HABILITADO |
| `POST` | `/reservations/{reservation_id}/approve` | Aprueba una solicitud pendiente; requiere administrador |
| `POST` | `/reservations/{reservation_id}/reject` | Rechaza una solicitud pendiente con motivo; requiere administrador |

La solicitud recibe `{"space_id":"<uuid>","date":"2026-11-10","start_time":"10:00","end_time":"12:00"}`. El espacio debe estar ACTIVO, y el intervalo debe estar dentro de 07:00–21:00 en `America/Bogota`, con hora de inicio anterior a la hora de fin. Las horas fuera del horario o intervalos no válidos responden `422`; un espacio inactivo responde `409`. Las solicitudes PENDIENTE pueden traslaparse. Un traslape con una reserva APROBADA responde `409` e incluye `reservation_id` del conflicto. Los intervalos contiguos no se consideran traslapados.

Al aprobar, las solicitudes PENDIENTE traslapadas del mismo espacio se marcan RECHAZADA con motivo `conflicto con reserva aprobada`. El rechazo manual requiere `{"reason":"..."}` no vacío. Los intentos de aprobar o rechazar por usuarios no administradores responden `403`; las transiciones desde estados distintos de PENDIENTE responden `409`.

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/reservations/{reservation_id}/cancel` | Cancela una reserva propia PENDIENTE o APROBADA con motivo |
| `GET` | `/reservations/{reservation_id}/history` | Consulta el historial; el administrador puede consultar cualquiera y el solicitante solo el propio |

La cancelación recibe `{"reason":"..."}` no vacío. Una reserva RECHAZADA o CANCELADA responde `409` si se intenta cancelar otra vez; otro usuario recibe `403`. Cancelar una reserva APROBADA libera inmediatamente su horario. El historial incluye actor, instante UTC, estado anterior y nuevo y motivo cuando corresponde; los registros son inmutables. Al deshabilitar a un usuario, la misma transacción cancela sus solicitudes PENDIENTE y sus reservas APROBADA futuras con motivo `usuario deshabilitado`; si el cambio falla, se revierten también las modificaciones de reservas.
