import { useState, type FormEvent } from 'react'
import { ApiError, apiRequest } from '../api/client'

interface Registration {
  name: string
  email: string
  password: string
}

export default function RegisterPage() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    setIsSubmitting(true)
    setMessage('')
    setError('')

    const formData = new FormData(form)
    const registration: Registration = {
      name: String(formData.get('name') ?? ''),
      email: String(formData.get('email') ?? ''),
      password: String(formData.get('password') ?? ''),
    }

    try {
      await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify(registration),
      })
      setMessage('Registro recibido. Revisa tu correo para verificar la cuenta.')
      form.reset()
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo completar el registro. Inténtalo de nuevo.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="form-card" aria-labelledby="register-title">
      <p className="eyebrow">Nueva cuenta</p>
      <h1 id="register-title">Registro</h1>
      <p className="form-intro">
        Completa tus datos. La API enviará el enlace de verificación.
      </p>
      <form className="form-stack" onSubmit={handleSubmit}>
        <label htmlFor="registration-name">
          Nombre
          <input
            autoComplete="name"
            id="registration-name"
            maxLength={200}
            name="name"
            required
          />
        </label>
        <label htmlFor="registration-email">
          Correo electrónico
          <input
            autoComplete="email"
            id="registration-email"
            name="email"
            required
            type="email"
          />
        </label>
        <label htmlFor="registration-password">Contraseña</label>
        <div>
          <input
            autoComplete="new-password"
            id="registration-password"
            minLength={12}
            name="password"
            required
            type="password"
          />
          <span className="field-hint">
            Debe tener al menos 12 caracteres.
          </span>
        </div>
        <button className="button button-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Enviando…' : 'Crear cuenta'}
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
