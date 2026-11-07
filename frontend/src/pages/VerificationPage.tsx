import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { ApiError, apiRequest } from '../api/client'

export default function VerificationPage() {
  const { hash } = useLocation()
  const verificationStarted = useRef(false)
  const token = new URLSearchParams(hash.slice(1)).get('token')?.trim() ?? ''
  const [verificationMessage, setVerificationMessage] = useState('')
  const [verificationError, setVerificationError] = useState('')
  const [resendMessage, setResendMessage] = useState('')
  const [resendError, setResendError] = useState('')
  const [isResending, setIsResending] = useState(false)

  useEffect(() => {
    if (!token || verificationStarted.current) {
      return
    }

    verificationStarted.current = true
    void apiRequest<{ message: string }>('/auth/verify', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
      .then((response) => setVerificationMessage(response.message))
      .catch((requestError: unknown) => {
        setVerificationError(
          requestError instanceof ApiError
            ? requestError.message
            : 'No se pudo verificar el correo. Inténtalo de nuevo.',
        )
      })
  }, [token])

  async function handleResend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsResending(true)
    setResendMessage('')
    setResendError('')

    const form = event.currentTarget
    const email = String(new FormData(form).get('email') ?? '')

    try {
      await apiRequest('/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setResendMessage('Si la cuenta puede verificarse, se envió un nuevo enlace.')
      form.reset()
    } catch (requestError) {
      setResendError(
        requestError instanceof ApiError
          ? requestError.message
          : 'No se pudo reenviar el enlace. Inténtalo de nuevo.',
      )
    } finally {
      setIsResending(false)
    }
  }

  return (
    <section className="form-card" aria-labelledby="verification-title">
      <p className="eyebrow">Verificación de cuenta</p>
      <h1 id="verification-title">Verifica tu correo</h1>
      {token ? (
        <p className="form-intro" role="status">
          {verificationMessage || 'Verificando el enlace…'}
        </p>
      ) : (
        <p className="form-intro">
          Abre el enlace de verificación del correo o solicita que se reenvíe.
        </p>
      )}
      {verificationError && (
        <p className="notice notice-error" role="alert">
          {verificationError}
        </p>
      )}
      <form className="form-stack resend-form" onSubmit={handleResend}>
        <label htmlFor="resend-email">Correo para reenviar verificación</label>
        <input
          autoComplete="email"
          id="resend-email"
          name="email"
          placeholder="nombre@institucion.edu"
          required
          type="email"
        />
        <button className="button button-secondary" disabled={isResending}>
          {isResending ? 'Enviando…' : 'Reenviar enlace'}
        </button>
      </form>
      {resendMessage && (
        <p className="notice notice-success" role="status">
          {resendMessage}
        </p>
      )}
      {resendError && (
        <p className="notice notice-error" role="alert">
          {resendError}
        </p>
      )}
    </section>
  )
}
