import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AdminUsersPage from './AdminUsersPage'

const userId = 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6'
const userRecord = {
  id: userId,
  name: 'Ana Docente',
  email: 'ana@example.com',
  status: 'HABILITADO',
  role: 'USER',
}

describe('AdminUsersPage', () => {
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

  it('updates user status through the API and displays the returned state', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([userRecord]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...userRecord, status: 'DESHABILITADO' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route path="/admin/users" element={<AdminUsersPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const card = await screen.findByRole('article', { name: 'Ana Docente' })
    await user.click(within(card).getByRole('button', { name: 'Deshabilitar' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/users/${userId}/status`,
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'DESHABILITADO' }),
      }),
    )
    expect(await screen.findByText('DESHABILITADO · USER')).toBeInTheDocument()
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Se actualizó el usuario ana@example.com.',
    )
  })

  it('updates a user role and displays the account history', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([userRecord]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...userRecord, role: 'ADMIN' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: 'a89c4c78-32a0-4b2b-8c12-48e42a4c82b6',
              target_user_id: userId,
              actor_user_id: userId,
              change_type: 'ROLE',
              old_value: 'USER',
              new_value: 'ADMIN',
              created_at: '2026-02-01T10:00:00Z',
            },
          ]),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route path="/admin/users" element={<AdminUsersPage />} />
        </Routes>
      </MemoryRouter>,
    )

    const card = await screen.findByRole('article', { name: 'Ana Docente' })
    await user.click(within(card).getByRole('button', { name: 'Asignar ADMIN' }))
    expect(await screen.findByText('HABILITADO · ADMIN')).toBeInTheDocument()
    await user.click(
      within(card).getByRole('button', { name: 'Historial de usuario' }),
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/users/${userId}/role`,
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ role: 'ADMIN' }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `/api/users/${userId}/history`,
      expect.any(Object),
    )
    expect(await screen.findByText('ROLE: USER → ADMIN')).toBeInTheDocument()
  })
})
