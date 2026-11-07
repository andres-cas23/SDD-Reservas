import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, apiRequest } from '../api/client'

interface Space {
  id: string
  name: string
  type: string
  capacity: number
  status: string
}

export default function AdminSpacesPage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [loading, setLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    void apiRequest<Space[]>('/spaces')
      .then(setSpaces)
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : 'No se pudieron cargar los espacios.',
        )
      })
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const formData = new FormData(form)
    setError('')
    setMessage('')
    setIsSubmitting(true)
    try {
      const space = await apiRequest<Space>('/spaces', {
        method: 'POST',
        body: JSON.stringify({
          name: String(formData.get('name') ?? ''),
          type: String(formData.get('type') ?? ''),
          capacity: Number(formData.get('capacity')),
          status: String(formData.get('status') ?? ''),
        }),
      })
      setSpaces((current) =>
        [...current, space].sort((a, b) => a.name.localeCompare(b.name)),
      )
      setMessage(`Se registró el espacio ${space.name}.`)
      form.reset()
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo registrar el espacio.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="feature-page" aria-labelledby="admin-spaces-title">
      <p className="eyebrow">Administración</p>
      <h1 id="admin-spaces-title">Espacios</h1>
      <p className="form-intro">Registra espacios académicos y consulta el catálogo.</p>
      <section className="data-card" aria-labelledby="create-space-title">
        <h2 id="create-space-title">Registrar espacio</h2>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label htmlFor="space-name">Nombre</label>
          <input id="space-name" maxLength={200} name="name" required />
          <label htmlFor="space-type">Tipo</label>
          <select id="space-type" name="type" required defaultValue="LABORATORIO">
            <option value="LABORATORIO">Laboratorio</option>
            <option value="AUDITORIO">Auditorio</option>
            <option value="SALA_COMPUTO">Sala de cómputo</option>
          </select>
          <label htmlFor="space-capacity">Capacidad</label>
          <input id="space-capacity" min={1} name="capacity" required type="number" />
          <label htmlFor="space-status">Estado</label>
          <select id="space-status" name="status" required defaultValue="ACTIVO">
            <option value="ACTIVO">Activo</option>
            <option value="INACTIVO">Inactivo</option>
          </select>
          <button className="button button-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Registrando…' : 'Registrar espacio'}
          </button>
        </form>
        {message && <p className="notice notice-success" role="status">{message}</p>}
        {error && <p className="notice notice-error" role="alert">{error}</p>}
      </section>
      <section className="data-card" aria-labelledby="space-catalog-title">
        <h2 id="space-catalog-title">Catálogo</h2>
        {loading && <p role="status">Cargando espacios…</p>}
        {!loading && spaces.length === 0 && <p>No hay espacios registrados.</p>}
        {spaces.length > 0 && (
          <ul className="space-list">
            {spaces.map((space) => (
              <li key={space.id}>
                <strong>{space.name}</strong>
                <span>{space.type} · Capacidad {space.capacity} · {space.status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  )
}
