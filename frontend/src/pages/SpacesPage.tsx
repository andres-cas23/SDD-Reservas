import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiRequest } from '../api/client'

interface Space {
  id: string
  name: string
  type: string
  capacity: number
  status: string
}

interface TimeInterval {
  start: string
  end: string
}

interface Availability {
  occupied: TimeInterval[]
  free: TimeInterval[]
}

function formatTime(value: string): string {
  return value.slice(0, 5)
}

export default function SpacesPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [spacesError, setSpacesError] = useState('')
  const [availability, setAvailability] = useState<Availability | null>(null)
  const [availabilityError, setAvailabilityError] = useState('')
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false)

  useEffect(() => {
    void apiRequest<Space[]>('/spaces')
      .then(setSpaces)
      .catch((requestError: unknown) => {
        setSpacesError(
          requestError instanceof ApiError
            ? requestError.message
            : 'No se pudieron cargar los espacios.',
        )
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function handleAvailabilitySubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    setAvailability(null)
    setAvailabilityError('')
    setIsCheckingAvailability(true)
    const formData = new FormData(event.currentTarget)
    const spaceId = String(formData.get('space_id') ?? '')
    const date = String(formData.get('date') ?? '')

    try {
      const response = await apiRequest<Availability>(
        `/spaces/${encodeURIComponent(spaceId)}/availability?date=${encodeURIComponent(date)}`,
      )
      setAvailability(response)
    } catch (requestError) {
      setAvailabilityError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo consultar la disponibilidad.',
      )
    } finally {
      setIsCheckingAvailability(false)
    }
  }

  return (
    <section className="feature-page" aria-labelledby="spaces-title">
      <p className="eyebrow">Espacios académicos</p>
      <h1 id="spaces-title">Espacios y disponibilidad</h1>
      <p className="form-intro">
        Consulta espacios y las franjas ocupadas y libres para una fecha.
      </p>

      <section className="data-card" aria-labelledby="space-list-title">
        <div className="section-heading">
          <h2 id="space-list-title">Espacios disponibles en el sistema</h2>
          <Link className="button button-secondary" to="/reservations/new">
            Nueva solicitud
          </Link>
        </div>
        {isLoading && <p role="status">Cargando espacios…</p>}
        {spacesError && (
          <p className="notice notice-error" role="alert">
            {spacesError}
          </p>
        )}
        {!isLoading && !spacesError && spaces.length === 0 && (
          <p>No hay espacios registrados.</p>
        )}
        {spaces.length > 0 && (
          <ul className="space-list">
            {spaces.map((space) => (
              <li key={space.id}>
                <strong>{space.name}</strong>
                <span>
                  {space.type} · Capacidad {space.capacity} · {space.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="data-card" aria-labelledby="availability-title">
        <h2 id="availability-title">Consultar disponibilidad</h2>
        <form className="form-stack availability-form" onSubmit={handleAvailabilitySubmit}>
          <label htmlFor="availability-space">Espacio</label>
          <select
            id="availability-space"
            name="space_id"
            required
            disabled={isLoading || spaces.length === 0}
          >
            <option value="">Selecciona un espacio</option>
            {spaces.map((space) => (
              <option key={space.id} value={space.id}>
                {space.name}
              </option>
            ))}
          </select>
          <label htmlFor="availability-date">Fecha</label>
          <input id="availability-date" name="date" required type="date" />
          <button
            className="button button-primary"
            disabled={isCheckingAvailability || spaces.length === 0}
          >
            {isCheckingAvailability ? 'Consultando…' : 'Consultar'}
          </button>
        </form>
        {availabilityError && (
          <p className="notice notice-error" role="alert">
            {availabilityError}
          </p>
        )}
        {availability && (
          <div className="interval-columns" aria-live="polite">
            <IntervalList title="Franjas ocupadas" intervals={availability.occupied} />
            <IntervalList title="Franjas libres" intervals={availability.free} />
          </div>
        )}
      </section>
    </section>
  )
}

function IntervalList({
  title,
  intervals,
}: {
  title: string
  intervals: TimeInterval[]
}) {
  return (
    <div>
      <h3>{title}</h3>
      {intervals.length === 0 ? (
        <p>No hay franjas.</p>
      ) : (
        <ul className="interval-list">
          {intervals.map((interval) => (
            <li key={`${interval.start}-${interval.end}`}>
              {formatTime(interval.start)}–{formatTime(interval.end)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
