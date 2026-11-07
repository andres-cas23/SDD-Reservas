import { useEffect, useState } from 'react'
import { ApiError, apiRequest } from '../api/client'

interface User {
  id: string
  name: string
  email: string
  status: string
  role: string
}

interface AccountHistory {
  id: string
  change_type: string
  old_value: string | null
  new_value: string
  created_at: string
}

const nextStatus: Record<string, string> = {
  VERIFICADO: 'HABILITADO',
  HABILITADO: 'DESHABILITADO',
  DESHABILITADO: 'HABILITADO',
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    void apiRequest<User[]>('/users')
      .then(setUsers)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : 'No se pudieron cargar los usuarios.',
        )
      })
      .finally(() => setLoading(false))
  }, [])

  async function changeUser(
    userId: string,
    action: 'status' | 'role',
    value: string,
  ) {
    setActionError('')
    setMessage('')
    try {
      const user = await apiRequest<User>(`/users/${userId}/${action}`, {
        method: 'PATCH',
        body: JSON.stringify({ [action]: value }),
      })
      setUsers((current) =>
        current.map((item) => (item.id === userId ? user : item)),
      )
      setMessage(`Se actualizó el usuario ${user.email}.`)
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo actualizar el usuario.',
      )
    }
  }

  return (
    <section className="feature-page" aria-labelledby="admin-users-title">
      <p className="eyebrow">Administración</p>
      <h1 id="admin-users-title">Usuarios</h1>
      <p className="form-intro">
        Administra la habilitación y el rol. La API valida cada transición.
      </p>
      {loading && <p role="status">Cargando usuarios…</p>}
      {error && <p className="notice notice-error" role="alert">{error}</p>}
      {actionError && (
        <p className="notice notice-error" role="alert">{actionError}</p>
      )}
      {message && <p className="notice notice-success" role="status">{message}</p>}
      {!loading && !error && users.length === 0 && (
        <section className="data-card"><p>No hay usuarios registrados.</p></section>
      )}
      {users.map((user) => (
        <UserCard
          key={user.id}
          onChange={changeUser}
          user={user}
        />
      ))}
    </section>
  )
}

function UserCard({
  user,
  onChange,
}: {
  user: User
  onChange: (userId: string, action: 'status' | 'role', value: string) => void
}) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState<AccountHistory[] | null>(null)
  const [historyError, setHistoryError] = useState('')
  const [historyLoading, setHistoryLoading] = useState(false)

  async function toggleHistory() {
    const opening = !historyOpen
    setHistoryOpen(opening)
    if (!opening || history !== null || historyLoading) {
      return
    }
    setHistoryLoading(true)
    setHistoryError('')
    try {
      setHistory(
        await apiRequest<AccountHistory[]>(`/users/${user.id}/history`),
      )
    } catch (requestError) {
      setHistoryError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo consultar el historial del usuario.',
      )
    } finally {
      setHistoryLoading(false)
    }
  }

  return (
    <article className="data-card admin-record" aria-labelledby={`user-${user.id}`}>
      <div className="record-heading">
        <h2 id={`user-${user.id}`}>{user.name}</h2>
        <span className="reservation-status">{user.status} · {user.role}</span>
      </div>
      <p>{user.email}</p>
      <div className="reservation-actions">
        {nextStatus[user.status] && (
          <button
            className="button button-secondary"
            onClick={() => onChange(user.id, 'status', nextStatus[user.status])}
            type="button"
          >
            {nextStatus[user.status] === 'DESHABILITADO'
              ? 'Deshabilitar'
              : 'Habilitar'}
          </button>
        )}
        {user.role === 'USER' ? (
          <button
            className="button button-secondary"
            onClick={() => onChange(user.id, 'role', 'ADMIN')}
            type="button"
          >
            Asignar ADMIN
          </button>
        ) : (
          <button
            className="button button-secondary"
            onClick={() => onChange(user.id, 'role', 'USER')}
            type="button"
          >
            Cambiar a USER
          </button>
        )}
        <button
          aria-expanded={historyOpen}
          className="button button-secondary"
          onClick={() => void toggleHistory()}
          type="button"
        >
          Historial de usuario
        </button>
      </div>
      {historyOpen && (
        <section className="reservation-history" aria-label="Historial de usuario">
          <h3>Historial de cuenta</h3>
          {historyLoading && <p role="status">Cargando historial…</p>}
          {historyError && <p className="notice notice-error" role="alert">{historyError}</p>}
          {history && history.length === 0 && <p>Sin cambios registrados.</p>}
          {history && history.length > 0 && (
            <ol className="history-list">
              {history.map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.change_type}: {entry.old_value ?? '—'} → {entry.new_value}</strong>
                  <span>{new Date(entry.created_at).toISOString()} UTC</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </article>
  )
}
