# Proposal

## Why

Las etapas 1 y 2 exponen las funciones de identidad, espacios y reservas mediante una API, pero aún no ofrecen la interfaz web necesaria para que visitantes, usuarios habilitados y administradores las utilicen. Esta etapa agrega una aplicación React accesible en escritorio y móvil sin trasladar reglas de negocio fuera del backend.

## What Changes

- Crear una aplicación web React con Vite dentro de `frontend/`, en este mismo repositorio, que consuma las API existentes.
- Incorporar registro, verificación y reenvío de verificación, inicio y cierre de sesión, y activación del administrador inicial mediante enlaces que abren rutas de la interfaz.
- Incorporar consulta de espacios y disponibilidad, creación de solicitudes, “Mis reservas” con cancelación e historial, y pantallas de administración de usuarios, solicitudes y espacios.
- Mostrar las acciones de administración solo al rol ADMIN; el backend continúa siendo la autoridad de autorización y de todas las reglas de reservas.
- Presentar los errores de API acordes con RF-01–RF-18: redirigir a login ante 401, mostrar acceso denegado o el mensaje de cuenta no verificada ante 403, indicar espacio inexistente ante 404, mostrar el motivo de 409 y asociar errores 422 con los campos correspondientes.
- Hacer que la interfaz funcione en navegadores modernos de escritorio y móvil, según RNF-07.
- Excluir recuperación o cambio de contraseña, cancelación de reservas ajenas, límite de cuatro horas (RF-17), notificaciones, calendario semanal, reportes, edición o eliminación de espacios y rol de coordinador.

## Capabilities

### New Capabilities
- `web-frontend`: interfaz web adaptable para los flujos de identidad, espacios, disponibilidad y reservas de usuarios y administradores.

### Modified Capabilities

## Impact

- Nuevo código y dependencias de interfaz bajo `frontend/`.
- Consumo de los endpoints existentes de autenticación, usuarios, espacios y reservas.
- Enlaces de verificación y activación inicial que deben abrir rutas de la interfaz; la API seguirá procesando los tokens y las acciones.
- Pruebas automatizadas de interfaz y flujos que verifican la comunicación con la API, los permisos visuales, errores y adaptación a móvil.
