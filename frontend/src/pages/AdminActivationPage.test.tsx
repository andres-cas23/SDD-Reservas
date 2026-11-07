import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AdminActivationPage from './AdminActivationPage'

describe('AdminActivationPage', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('submits the seed-link token and password and displays the API response', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ message: 'Administrador activado.' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const user = userEvent.setup()
    render(
      <MemoryRouter
        initialEntries={['/auth/activate-admin#token=seed-secret']}
      >
        <Routes>
          <Route
            path="/auth/activate-admin"
            element={<AdminActivationPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(
      screen.getByLabelText('Nueva contraseña'),
      'password-largo-123',
    )
    await user.click(
      screen.getByRole('button', { name: 'Activar administrador' }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/activate-admin',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          token: 'seed-secret',
          password: 'password-largo-123',
        }),
      }),
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Administrador activado.',
    )
  })

  it('does not submit when the activation link has no token', async () => {
    render(
      <MemoryRouter initialEntries={['/auth/activate-admin']}>
        <Routes>
          <Route
            path="/auth/activate-admin"
            element={<AdminActivationPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'El enlace de activación no contiene un token válido.',
    )
    expect(
      screen.getByRole('button', { name: 'Activar administrador' }),
    ).toBeDisabled()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
