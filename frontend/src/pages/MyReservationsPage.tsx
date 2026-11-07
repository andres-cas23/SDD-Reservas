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

function formatTime(value: string): string {
  return value.slice(0, 5)
}

export default function MyReservationsPage() {
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void apiRequest<Reservation[]>('/reservations')
      .then(setReservations)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : 'No se pudieron cargar tus reservas.',
        )
      })
      .finally(() => setIsLoading(false))
  }, [])

  function updateReservationStatus(id: string, status: string) {
    setReservations((current) =>
      current.map((reservation) =>
        reservation.id === id ? { ...reservation, status } : reservation,
      ),
    )
  }

  return (
    <section className="feature-page" aria-labelledby="my-reservations-title">
      <p className="eyebrow">Tu actividad</p>
      <h1 id="my-reservations-title">Mis reservas</h1>
      <p className="form-intro">
        Consulta tus solicitudes y reservas. Puedes cancelar las que estén
        pendientes o aprobadas y consultar el historial de cada una.
      </p>
      {isLoading && <p role="status">Cargando tus reservas…</p>}
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      {!isLoading && !error && reservations.length === 0 && (
        <section className="data-card">
          <p>No tienes reservas todavía.</p>
        </section>
      )}
      {reservations.map((reservation) => (
        <ReservationCard
          key={reservation.id}
          onStatusChange={updateReservationStatus}
          reservation={reservation}
        />
      ))}
    </section>
  )
}

function ReservationCard({
  reservation,
  onStatusChange,
}: {
  reservation: Reservation
  onStatusChange: (id: string, status: string) => void
}) {
  const [isCancelFormOpen, setIsCancelFormOpen] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [cancelError, setCancelError] = useState('')
  const [cancelMessage, setCancelMessage] = useState('')
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [history, setHistory] = useState<ReservationHistory[] | null>(null)
  const [historyError, setHistoryError] = useState('')
  const canCancel = ['PENDIENTE', 'APROBADA'].includes(reservation.status)

  async function handleCancel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const reason = String(new FormData(form).get('reason') ?? '')
    setIsCancelling(true)
    setCancelError('')
    setCancelMessage('')

    try {
      const response = await apiRequest<{ status: string }>(
        `/reservations/${encodeURIComponent(reservation.id)}/cancel`,
        {
          method: 'POST',
          body: JSON.stringify({ reason }),
        },
      )
      onStatusChange(reservation.id, response.status)
      setCancelMessage('La reserva se canceló.')
      setIsCancelFormOpen(false)
      form.reset()
    } catch (requestError) {
      setCancelError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo cancelar la reserva.',
      )
    } finally {
      setIsCancelling(false)
    }
  }

  async function toggleHistory() {
    const opening = !isHistoryOpen
    setIsHistoryOpen(opening)
    if (!opening || history !== null || isHistoryLoading) {
      return
    }

    setIsHistoryLoading(true)
    setHistoryError('')
    try {
      const response = await apiRequest<ReservationHistory[]>(
        `/reservations/${encodeURIComponent(reservation.id)}/history`,
      )
      setHistory(response)
    } catch (requestError) {
      setHistoryError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo consultar el historial.',
      )
    } finally {
      setIsHistoryLoading(false)
    }
  }

  return (
    <article
      className="data-card reservation-card"
      aria-labelledby={`reservation-${reservation.id}`}
    >
      <div className="reservation-heading">
        <h2 id={`reservation-${reservation.id}`}>{reservation.space}</h2>
        <span className="reservation-status">{reservation.status}</span>
      </div>
      <p className="reservation-schedule">
        {reservation.date} · {formatTime(reservation.start_time)}–
        {formatTime(reservation.end_time)}
      </p>
      <div className="reservation-actions">
        {canCancel && (
          <button
            aria-expanded={isCancelFormOpen}
            className="button button-secondary"
            onClick={() => {
              setIsCancelFormOpen((open) => !open)
              setCancelError('')
              setCancelMessage('')
            }}
            type="button"
          >
            Cancelar reserva
          </button>
        )}
        <button
          aria-expanded={isHistoryOpen}
          className="button button-secondary"
          onClick={() => void toggleHistory()}
          type="button"
        >
          Ver historial
        </button>
      </div>

      {isCancelFormOpen && canCancel && (
        <form className="form-stack cancel-form" onSubmit={handleCancel}>
          <label htmlFor={`cancel-reason-${reservation.id}`}>
            Motivo de cancelación
          </label>
          <textarea
            id={`cancel-reason-${reservation.id}`}
            maxLength={500}
            minLength={1}
            name="reason"
            required
            rows={3}
          />
          <button className="button button-primary" disabled={isCancelling}>
            {isCancelling ? 'Cancelando…' : 'Confirmar cancelación'}
          </button>
        </form>
      )}
      {cancelMessage && (
        <p className="notice notice-success" role="status">
          {cancelMessage}
        </p>
      )}
      {cancelError && (
        <p className="notice notice-error" role="alert">
          {cancelError}
        </p>
      )}

      {isHistoryOpen && (
        <section className="reservation-history" aria-label="Historial de reserva">
          <h3>Historial</h3>
          {isHistoryLoading && <p role="status">Cargando historial…</p>}
          {historyError && (
            <p className="notice notice-error" role="alert">
              {historyError}
            </p>
          )}
          {history && history.length === 0 && <p>Sin cambios registrados.</p>}
          {history && history.length > 0 && (
            <ol className="history-list">
              {history.map((entry) => (
                <li key={entry.id}>
                  <strong>
                    {entry.old_status ?? 'Creada'} → {entry.new_status}
                  </strong>
                  <span>
                    {new Date(entry.created_at).toISOString()} UTC · Usuario{' '}
                    {entry.actor_user_id}
                  </span>
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
