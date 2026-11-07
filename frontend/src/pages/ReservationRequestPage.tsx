import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, apiRequest } from '../api/client'

interface Space {
  id: string
  name: string
  type: string
  status: string
}

interface Reservation {
  status: string
}

type ReservationField = 'space_id' | 'date' | 'start_time' | 'end_time'

const reservationFields: ReservationField[] = [
  'space_id',
  'date',
  'start_time',
  'end_time',
]

function getFieldErrors(detail: unknown): Partial<Record<ReservationField, string>> {
  if (!Array.isArray(detail)) {
    return {}
  }

  const errors: Partial<Record<ReservationField, string>> = {}
  for (const item of detail) {
    if (
      typeof item !== 'object' ||
      item === null ||
      !('loc' in item) ||
      !Array.isArray(item.loc) ||
      !('msg' in item) ||
      typeof item.msg !== 'string'
    ) {
      continue
    }
    const field = item.loc.at(-1)
    if (
      typeof field === 'string' &&
      reservationFields.includes(field as ReservationField)
    ) {
      errors[field as ReservationField] = item.msg
    }
  }
  return errors
}

export default function ReservationRequestPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [spacesError, setSpacesError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<ReservationField, string>>
  >({})

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const formData = new FormData(form)
    setIsSubmitting(true)
    setMessage('')
    setError('')
    setFieldErrors({})

    try {
      const reservation = await apiRequest<Reservation>('/reservations', {
        method: 'POST',
        body: JSON.stringify({
          space_id: String(formData.get('space_id') ?? ''),
          date: String(formData.get('date') ?? ''),
          start_time: String(formData.get('start_time') ?? ''),
          end_time: String(formData.get('end_time') ?? ''),
        }),
      })
      setMessage(`Solicitud creada. Estado: ${reservation.status}.`)
      form.reset()
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        if (requestError.status === 422) {
          const validationErrors = getFieldErrors(requestError.detail)
          setFieldErrors(validationErrors)
          setError(
            Object.keys(validationErrors).length > 0
              ? ''
              : requestError.message,
          )
        } else {
          setError(requestError.message)
        }
      } else {
        setError('No se pudo crear la solicitud. Inténtalo de nuevo.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="form-card" aria-labelledby="reservation-request-title">
      <p className="eyebrow">Nueva reserva</p>
      <h1 id="reservation-request-title">Solicitar un espacio</h1>
      <p className="form-intro">
        Envía los datos de tu solicitud. El servidor valida el horario y la
        disponibilidad.
      </p>
      {isLoading && <p role="status">Cargando espacios…</p>}
      {spacesError && (
        <p className="notice notice-error" role="alert">
          {spacesError}
        </p>
      )}
      {!isLoading && !spacesError && spaces.length === 0 && (
        <p>No hay espacios para seleccionar.</p>
      )}
      <form className="form-stack" onSubmit={handleSubmit}>
        <label htmlFor="reservation-space">Espacio</label>
        <select
          aria-describedby={fieldErrors.space_id ? 'reservation-space-error' : undefined}
          aria-invalid={Boolean(fieldErrors.space_id)}
          disabled={isLoading || spaces.length === 0}
          id="reservation-space"
          name="space_id"
          required
        >
          <option value="">Selecciona un espacio</option>
          {spaces.map((space) => (
            <option key={space.id} value={space.id}>
              {space.name} · {space.type} · {space.status}
            </option>
          ))}
        </select>
        {fieldErrors.space_id && (
          <span className="field-error" id="reservation-space-error" role="alert">
            {fieldErrors.space_id}
          </span>
        )}
        <label htmlFor="reservation-date">Fecha</label>
        <input
          aria-describedby={fieldErrors.date ? 'reservation-date-error' : undefined}
          aria-invalid={Boolean(fieldErrors.date)}
          id="reservation-date"
          name="date"
          required
          type="date"
        />
        {fieldErrors.date && (
          <span className="field-error" id="reservation-date-error" role="alert">
            {fieldErrors.date}
          </span>
        )}
        <label htmlFor="reservation-start-time">Hora de inicio</label>
        <input
          aria-describedby={
            fieldErrors.start_time ? 'reservation-start-error' : undefined
          }
          aria-invalid={Boolean(fieldErrors.start_time)}
          id="reservation-start-time"
          name="start_time"
          required
          type="time"
        />
        {fieldErrors.start_time && (
          <span className="field-error" id="reservation-start-error" role="alert">
            {fieldErrors.start_time}
          </span>
        )}
        <label htmlFor="reservation-end-time">Hora de fin</label>
        <input
          aria-describedby={
            fieldErrors.end_time ? 'reservation-end-error' : undefined
          }
          aria-invalid={Boolean(fieldErrors.end_time)}
          id="reservation-end-time"
          name="end_time"
          required
          type="time"
        />
        {fieldErrors.end_time && (
          <span className="field-error" id="reservation-end-error" role="alert">
            {fieldErrors.end_time}
          </span>
        )}
        <button
          className="button button-primary"
          disabled={isSubmitting || isLoading || spaces.length === 0}
        >
          {isSubmitting ? 'Enviando…' : 'Enviar solicitud'}
        </button>
      </form>
      {message && (
        <p className="notice notice-success" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
