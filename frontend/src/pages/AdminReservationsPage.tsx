import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, apiRequest } from '../api/client'

interface Reservation {
  id: string
  status: string
  space: string
  date: string
  start_time: string
  end_time: string
}

interface ReservationHistory {
  id: string
  actor_user_id: string
  old_status: string | null
  new_status: string
  reason: string | null
  created_at: string
}

export default function AdminReservationsPage() {
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void apiRequest<Reservation[]>('/reservations')
      .then(setReservations)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : 'No se pudieron cargar las reservas.',
        )
      })
      .finally(() => setLoading(false))
  }, [])

  function updateStatus(id: string, status: string) {
    setReservations((current) =>
      current.map((reservation) =>
        reservation.id === id ? { ...reservation, status } : reservation,
      ),
    )
  }

  return (
    <section className="feature-page" aria-labelledby="admin-reservations-title">
      <p className="eyebrow">Administración</p>
      <h1 id="admin-reservations-title">Reservas</h1>
      <p className="form-intro">
        Revisa solicitudes, decide las pendientes y consulta cualquier historial.
      </p>
      {loading && <p role="status">Cargando reservas…</p>}
      {error && <p className="notice notice-error" role="alert">{error}</p>}
      {!loading && !error && reservations.length === 0 && (
        <section className="data-card"><p>No hay reservas registradas.</p></section>
      )}
      {reservations.map((reservation) => (
        <AdminReservationCard
          key={reservation.id}
          onStatusChange={updateStatus}
          reservation={reservation}
        />
      ))}
    </section>
  )
}

function AdminReservationCard({
  reservation,
  onStatusChange,
}: {
  reservation: Reservation
  onStatusChange: (id: string, status: string) => void
}) {
  const [rejectOpen, setRejectOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [message, setMessage] = useState('')
  const [historyOpen, setHistoryOpen] = useState(false)
  const [history, setHistory] = useState<ReservationHistory[] | null>(null)
  const [historyError, setHistoryError] = useState('')
  const [historyLoading, setHistoryLoading] = useState(false)

  async function decide(action: 'approve' | 'reject', reason?: string) {
    setBusy(true)
    setActionError('')
    setMessage('')
    try {
      const response = await apiRequest<{ status: string }>(
        `/reservations/${reservation.id}/${action}`,
        {
          method: 'POST',
          ...(reason === undefined
            ? {}
            : { body: JSON.stringify({ reason }) }),
        },
      )
      onStatusChange(reservation.id, response.status)
      setMessage(
        action === 'approve' ? 'Reserva aprobada.' : 'Reserva rechazada.',
      )
      setRejectOpen(false)
    } catch (requestError) {
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo actualizar la reserva.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function handleReject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const reason = String(new FormData(event.currentTarget).get('reason') ?? '')
    await decide('reject', reason)
  }

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
        await apiRequest<ReservationHistory[]>(
          `/reservations/${reservation.id}/history`,
        ),
      )
    } catch (requestError) {
      setHistoryError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo consultar el historial de la reserva.',
      )
    } finally {
      setHistoryLoading(false)
    }
  }

  return (
    <article
      className="data-card reservation-card"
      aria-labelledby={`admin-reservation-${reservation.id}`}
    >
      <div className="reservation-heading">
        <h2 id={`admin-reservation-${reservation.id}`}>{reservation.space}</h2>
        <span className="reservation-status">{reservation.status}</span>
      </div>
      <p className="reservation-schedule">
        {reservation.date} · {reservation.start_time.slice(0, 5)}–
        {reservation.end_time.slice(0, 5)}
      </p>
      <div className="reservation-actions">
        {reservation.status === 'PENDIENTE' && (
          <>
            <button
              className="button button-primary"
              disabled={busy}
              onClick={() => void decide('approve')}
              type="button"
            >
              Aprobar
            </button>
            <button
              aria-expanded={rejectOpen}
              className="button button-secondary"
              onClick={() => setRejectOpen((open) => !open)}
              type="button"
            >
              Rechazar
            </button>
          </>
        )}
        <button
          aria-expanded={historyOpen}
          className="button button-secondary"
          onClick={() => void toggleHistory()}
          type="button"
        >
          Ver historial
        </button>
      </div>
      {rejectOpen && reservation.status === 'PENDIENTE' && (
        <form className="form-stack cancel-form" onSubmit={handleReject}>
          <label htmlFor={`reject-reason-${reservation.id}`}>Motivo de rechazo</label>
          <textarea
            id={`reject-reason-${reservation.id}`}
            maxLength={500}
            minLength={1}
            name="reason"
            required
            rows={3}
          />
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Guardando…' : 'Confirmar rechazo'}
          </button>
        </form>
      )}
      {message && <p className="notice notice-success" role="status">{message}</p>}
      {actionError && <p className="notice notice-error" role="alert">{actionError}</p>}
      {historyOpen && (
        <section className="reservation-history" aria-label="Historial de reserva">
          <h3>Historial</h3>
          {historyLoading && <p role="status">Cargando historial…</p>}
          {historyError && <p className="notice notice-error" role="alert">{historyError}</p>}
          {history && history.length === 0 && <p>Sin cambios registrados.</p>}
          {history && history.length > 0 && (
            <ol className="history-list">
              {history.map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.old_status ?? 'Creada'} → {entry.new_status}</strong>
                  <span>{new Date(entry.created_at).toISOString()} UTC · Usuario {entry.actor_user_id}</span>
                  {entry.reason && <span>Motivo: {entry.reason}</span>}
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </article>
  )
}
