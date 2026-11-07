import { Link, useLocation } from 'react-router-dom'

const screens: Record<string, { title: string; description: string }> = {
  '/register': {
    title: 'Registro',
    description: 'Crea una cuenta para solicitar acceso al sistema.',
  },
  '/login': {
    title: 'Iniciar sesión',
    description: 'Accede a las funciones disponibles para tu cuenta.',
  },
  '/auth/verify': {
    title: 'Verificación del correo',
    description: 'Completa la verificación desde el enlace recibido por correo.',
  },
  '/auth/activate-admin': {
    title: 'Activación del administrador inicial',
    description: 'Define la contraseña del administrador inicial.',
  },
  '/spaces': {
    title: 'Espacios y disponibilidad',
    description: 'Consulta espacios y sus franjas disponibles.',
  },
  '/reservations/new': {
    title: 'Nueva solicitud',
    description: 'Envía una solicitud de reserva.',
  },
  '/reservations/mine': {
    title: 'Mis reservas',
    description: 'Consulta tus reservas, cancelaciones e historial.',
  },
  '/admin/users': {
    title: 'Administración de usuarios',
    description: 'Gestiona habilitación y roles de usuario.',
  },
  '/admin/reservations': {
    title: 'Administración de solicitudes',
    description: 'Gestiona solicitudes e historial de reservas.',
  },
  '/admin/spaces': {
    title: 'Administración de espacios',
    description: 'Registra y consulta espacios académicos.',
  },
}

export default function ScreenPreview() {
  const { pathname } = useLocation()
  const screen = screens[pathname]

  if (!screen) {
    return (
      <section className="welcome-card" aria-labelledby="welcome-title">
        <p className="eyebrow">Sistema de reservas académicas</p>
        <h1 id="welcome-title">Espacios para aprender y compartir</h1>
        <p>
          Consulta espacios, disponibilidad y solicitudes desde un solo lugar.
          Las reglas de acceso y reservas se aplican en el servicio.
        </p>
        <div className="welcome-actions">
          <Link className="button button-primary" to="/login">
            Iniciar sesión
          </Link>
          <Link className="button button-secondary" to="/register">
            Crear cuenta
          </Link>
        </div>
      </section>
    )
  }

  return (
    <section className="welcome-card" aria-labelledby="screen-title">
      <p className="eyebrow">Sistema de reservas académicas</p>
      <h1 id="screen-title">{screen.title}</h1>
      <p>{screen.description}</p>
      <p className="setup-note">
        Esta pantalla se habilitará durante la implementación del flujo
        correspondiente.
      </p>
    </section>
  )
}
