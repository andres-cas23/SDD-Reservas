import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { ApiError, apiRequest } from './api/client'
import {
  AUTHENTICATED_EVENT,
  AUTH_UNAUTHORIZED_EVENT,
  clearAccessToken,
  getAccessToken,
} from './api/session'
import './App.css'

function AppShell() {
  const navigate = useNavigate()
  const [accessToken, setAccessTokenState] = useState(getAccessToken)
  const [profile, setProfile] = useState<{ token: string; role: string } | null>(
    null,
  )
  const [profileError, setProfileError] = useState<{
    token: string
    message: string
  } | null>(null)
  const [logoutError, setLogoutError] = useState('')

  useEffect(() => {
    function handleAuthenticated() {
      setAccessTokenState(getAccessToken())
    }

    function handleUnauthorized() {
      setAccessTokenState(null)
      navigate('/login')
    }

    window.addEventListener(AUTHENTICATED_EVENT, handleAuthenticated)
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => {
      window.removeEventListener(AUTHENTICATED_EVENT, handleAuthenticated)
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized)
    }
  }, [navigate])

  useEffect(() => {
    let active = true
    if (!accessToken) {
      return () => {
        active = false
      }
    }

    void apiRequest<{ role: string }>('/auth/me')
      .then((profile) => {
        if (active) {
          setProfile({ token: accessToken, role: profile.role })
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setProfileError(
            {
              token: accessToken,
              message:
                requestError instanceof ApiError
                  ? requestError.message
                  : 'No se pudo cargar el perfil de la sesión.',
            },
          )
        }
      })

    return () => {
      active = false
    }
  }, [accessToken])

  async function handleLogout() {
    setLogoutError('')
    try {
      await apiRequest<void>('/auth/logout', { method: 'POST' })
    } catch (requestError) {
      setLogoutError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo cerrar la sesión en el servidor.',
      )
    } finally {
      clearAccessToken()
      setAccessTokenState(null)
      navigate('/login')
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="Reservas académicas, inicio">
          <span className="brand-mark" aria-hidden="true">
            R
          </span>
          <span>Reservas académicas</span>
        </Link>
        <nav className="primary-nav" aria-label="Navegación principal">
          <NavLink to="/spaces">Disponibilidad</NavLink>
          <NavLink to="/reservations/mine">Mis reservas</NavLink>
          {accessToken ? (
            <>
              {profile?.token === accessToken && profile.role === 'ADMIN' && (
                <>
                  <NavLink to="/admin/users">Usuarios</NavLink>
                  <NavLink to="/admin/reservations">Reservas</NavLink>
                  <NavLink to="/admin/spaces">Espacios</NavLink>
                </>
              )}
              <button className="nav-button" onClick={handleLogout} type="button">
                Cerrar sesión
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Iniciar sesión</NavLink>
              <NavLink to="/register">Registro</NavLink>
            </>
          )}
        </nav>
      </header>
      {logoutError && (
        <p className="notice notice-error session-notice" role="alert">
          {logoutError}
        </p>
      )}
      {accessToken && profileError?.token === accessToken && (
        <p className="notice notice-error session-notice" role="alert">
          {profileError.message}
        </p>
      )}
      <main className="main-content">
        <Outlet />
      </main>
      <footer className="site-footer">
        API de reservas académicas · La disponibilidad y las solicitudes se
        validan en el servidor.
      </footer>
    </div>
  )
}

export default AppShell
