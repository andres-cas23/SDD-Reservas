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
