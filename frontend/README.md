# Interfaz web

Aplicación React con Vite y TypeScript. Las pantallas se conectan con la API FastAPI mediante el prefijo `/api`.

## Desarrollo local

Desde esta carpeta instala dependencias y ejecuta Vite:

```powershell
npm install
npm run dev
```

Por defecto, Vite reenvía `/api/*` a `http://127.0.0.1:8000` y elimina el prefijo `/api` antes de enviar la solicitud. Para apuntar a otro servidor FastAPI, define `VITE_API_PROXY_TARGET` en `.env.local`:

```text
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

El cliente usa `/api` como base predeterminada. Se puede cambiar con `VITE_API_BASE_URL` si el despliegue publica la API en otra ruta u origen.

## Enlaces de correo

Configura `APP_BASE_URL` del backend con el origen de la interfaz para que los enlaces de verificación y activación inicial abran las rutas de la SPA (`/auth/verify#token=...` y `/auth/activate-admin#token=...`). El fragmento mantiene el token en el navegador; la interfaz lo envía en el cuerpo de `POST /api/auth/verify` o `POST /api/auth/activate-admin`. En producción, el servidor debe enrutar `/api/*` al backend y entregar la SPA para sus rutas de cliente.

## Espacios y solicitudes

Un usuario habilitado puede consultar el catálogo en `/spaces`, elegir un espacio y una fecha para ver las franjas ocupadas y libres, y enviar una solicitud desde `/reservations/new`. La interfaz muestra las respuestas y errores del API; la disponibilidad y las reglas de reserva se validan en el servidor.

En `/reservations/mine`, el usuario consulta las reservas que devuelve la API. Puede cancelar las que estén PENDIENTE o APROBADA enviando un motivo, y abrir siempre el historial de cualquiera de sus reservas. Los IDs devueltos por `GET /reservations` identifican la reserva para esas operaciones.

## Administración

Cuando hay una sesión, la interfaz consulta `GET /api/auth/me` y muestra los enlaces de administración únicamente si la API devuelve el rol `ADMIN`. La API sigue autorizando cada operación: las pantallas permiten listar usuarios, cambiar estado o rol y consultar su historial; aprobar o rechazar reservas pendientes y revisar historiales; y registrar/listar espacios.

## Comprobaciones

```powershell
npm run lint
npm run build
npm run test:e2e
```

Las pruebas de navegador cubren los flujos principales con respuestas de API
simuladas. En la primera ejecución local, instala Chromium con
`npx playwright install chromium`.
