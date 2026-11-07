import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AppShell from './App'
import { apiRequest } from './api/client'

describe('AppShell authentication', () => {
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

  it('sends the bearer token on logout and clears the local session', async () => {
    sessionStorage.setItem('reservas.accessToken', 'session-token')
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ role: 'ADMIN' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/spaces" element={<p>Espacios</p>} />
            <Route path="/login" element={<p>Formulario de acceso</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('link', { name: 'Usuarios' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/logout',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/auth/me',
      expect.any(Object),
    )
    const requestHeaders = new Headers(fetchMock.mock.calls[0][1].headers)
    expect(requestHeaders.get('Authorization')).toBe('Bearer session-token')
    expect(sessionStorage.getItem('reservas.accessToken')).toBeNull()
    expect(await screen.findByText('Formulario de acceso')).toBeInTheDocument()
  })

  it('clears the session and navigates to login after an authenticated 401', async () => {
    sessionStorage.setItem('reservas.accessToken', 'expired-token')
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ role: 'USER' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Token inválido.' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route
              path="/spaces"
              element={
                <button
                  onClick={() => {
                    void apiRequest('/spaces').catch(() => undefined)
                  }}
                >
                  Consultar espacios
                </button>
              }
            />
            <Route path="/login" element={<p>Formulario de acceso</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Consultar espacios' }))

    expect(await screen.findByText('Formulario de acceso')).toBeInTheDocument()
    expect(sessionStorage.getItem('reservas.accessToken')).toBeNull()
  })

  it('hides administrator navigation when the authenticated role is USER', async () => {
    sessionStorage.setItem('reservas.accessToken', 'user-token')
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ role: 'USER' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/spaces" element={<p>Espacios</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Espacios')

    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me', expect.any(Object))
    expect(screen.queryByRole('link', { name: 'Usuarios' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Reservas' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Espacios' })).not.toBeInTheDocument()
  })

  it('shows administrator navigation only after GET /auth/me returns ADMIN', async () => {
    sessionStorage.setItem('reservas.accessToken', 'admin-token')
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ role: 'ADMIN' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/spaces" element={<p>Espacios</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('link', { name: 'Usuarios' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reservas' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Espacios' })).toBeInTheDocument()
  })
})
