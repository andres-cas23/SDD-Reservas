import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LoginPage from './LoginPage'

describe('LoginPage', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    sessionStorage.clear()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('stores the returned access token for the browser session', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'session-token',
          token_type: 'bearer',
          expires_in: 3600,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/spaces" element={<p>Espacios disponibles</p>} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(
      screen.getByLabelText('Correo electrónico'),
      'ana@example.com',
    )
    await user.type(screen.getByLabelText('Contraseña'), 'password-largo-123')
    await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          email: 'ana@example.com',
          password: 'password-largo-123',
        }),
      }),
    )
    expect(sessionStorage.getItem('reservas.accessToken')).toBe('session-token')
    expect(await screen.findByText('Espacios disponibles')).toBeInTheDocument()
  })

  it('shows the API response for an unverified account', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'cuenta no verificada' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(
      screen.getByLabelText('Correo electrónico'),
      'ana@example.com',
    )
    await user.type(screen.getByLabelText('Contraseña'), 'password-largo-123')
    await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'cuenta no verificada',
    )
    expect(sessionStorage.getItem('reservas.accessToken')).toBeNull()
  })
})
