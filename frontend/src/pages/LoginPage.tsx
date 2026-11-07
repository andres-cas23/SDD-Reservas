import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, apiRequest } from '../api/client'
import { setAccessToken } from '../api/session'

interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    setIsSubmitting(true)
    setError('')
    const formData = new FormData(form)

    try {
      const response = await apiRequest<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: String(formData.get('email') ?? ''),
          password: String(formData.get('password') ?? ''),
        }),
      })
      setAccessToken(response.access_token)
      navigate('/spaces')
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo iniciar sesión. Inténtalo de nuevo.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="form-card" aria-labelledby="login-title">
      <p className="eyebrow">Acceso al sistema</p>
      <h1 id="login-title">Iniciar sesión</h1>
      <p className="form-intro">Ingresa con tu correo y contraseña.</p>
      <form className="form-stack" onSubmit={handleSubmit}>
        <label htmlFor="login-email">Correo electrónico</label>
        <input
          autoComplete="email"
          id="login-email"
          name="email"
          required
          type="email"
        />
        <label htmlFor="login-password">Contraseña</label>
        <input
          autoComplete="current-password"
          id="login-password"
          name="password"
          required
          type="password"
        />
        <button className="button button-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Ingresando…' : 'Iniciar sesión'}
        </button>
      </form>
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
