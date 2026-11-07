import { useState, type FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { ApiError, apiRequest } from '../api/client'

export default function AdminActivationPage() {
  const { hash } = useLocation()
  const token = new URLSearchParams(hash.slice(1)).get('token')?.trim() ?? ''
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token) {
      setError('El enlace de activación no contiene un token válido.')
      return
    }

    const form = event.currentTarget
    setIsSubmitting(true)
    setMessage('')
    setError('')
    const password = String(new FormData(form).get('password') ?? '')

    try {
      const response = await apiRequest<{ message: string }>(
        '/auth/activate-admin',
        {
          method: 'POST',
          body: JSON.stringify({ token, password }),
        },
      )
      setMessage(response.message)
      form.reset()
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo activar el administrador. Inténtalo de nuevo.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="form-card" aria-labelledby="admin-activation-title">
      <p className="eyebrow">Configuración inicial</p>
      <h1 id="admin-activation-title">Activar administrador</h1>
      <p className="form-intro">
        Define una contraseña para completar la activación de la cuenta
        administradora.
      </p>
      {!token && (
        <p className="notice notice-error" role="alert">
          El enlace de activación no contiene un token válido.
        </p>
      )}
      <form className="form-stack" onSubmit={handleSubmit}>
        <label htmlFor="admin-activation-password">Nueva contraseña</label>
        <div>
          <input
            autoComplete="new-password"
            disabled={!token || isSubmitting}
            id="admin-activation-password"
            minLength={12}
            name="password"
            required
            type="password"
          />
          <span className="field-hint">Debe tener al menos 12 caracteres.</span>
        </div>
        <button
          className="button button-primary"
          disabled={!token || isSubmitting}
        >
          {isSubmitting ? 'Activando…' : 'Activar administrador'}
        </button>
      </form>
      {message && (
        <p className="notice notice-success" role="status">
          {message}
        </p>
      )}
      {error && token && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
