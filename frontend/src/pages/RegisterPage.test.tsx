import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import RegisterPage from './RegisterPage'

describe('RegisterPage', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('submits visitor registration to the API and displays its success response', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: 'PENDIENTE_VERIFICACION' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const user = userEvent.setup()
    render(<RegisterPage />)

    await user.type(screen.getByLabelText('Nombre'), 'Ana Docente')
    await user.type(
      screen.getByLabelText('Correo electrónico'),
      'ana@example.com',
    )
    await user.type(
      screen.getByLabelText('Contraseña'),
      'password-largo-123',
    )
    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/register',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'Ana Docente',
          email: 'ana@example.com',
          password: 'password-largo-123',
        }),
      }),
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Revisa tu correo para verificar la cuenta.',
    )
  })

  it('displays the API error response without reporting success', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Ya existe una cuenta con ese correo.' }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const user = userEvent.setup()
    render(<RegisterPage />)

    await user.type(screen.getByLabelText('Nombre'), 'Ana Docente')
    await user.type(
      screen.getByLabelText('Correo electrónico'),
      'ana@example.com',
    )
    await user.type(
      screen.getByLabelText('Contraseña'),
      'password-largo-123',
    )
    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya existe una cuenta con ese correo.',
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
