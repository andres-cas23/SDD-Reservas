import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AdminReservationsPage from './AdminReservationsPage'

const reservationId = 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6'
const reservation = {
  id: reservationId,
  status: 'PENDIENTE',
  space: 'Auditorio Central',
  date: '2026-11-10',
  start_time: '10:00:00',
  end_time: '12:00:00',
}

describe('AdminReservationsPage', () => {
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

  it('approves a pending reservation through the API', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([reservation]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'APROBADA' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/reservations']}>
        <Routes>
          <Route
            path="/admin/reservations"
            element={<AdminReservationsPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    const card = await screen.findByRole('article', {
      name: 'Auditorio Central',
    })
    await user.click(within(card).getByRole('button', { name: 'Aprobar' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/reservations/${reservationId}/approve`,
      expect.objectContaining({ method: 'POST' }),
    )
    expect(await screen.findByText('APROBADA')).toBeInTheDocument()
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Reserva aprobada.',
    )
  })

  it('rejects a pending reservation with a reason', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([reservation]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'RECHAZADA' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/reservations']}>
        <Routes>
          <Route
            path="/admin/reservations"
            element={<AdminReservationsPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    const card = await screen.findByRole('article', {
      name: 'Auditorio Central',
    })
    await user.click(within(card).getByRole('button', { name: 'Rechazar' }))
    await user.type(
      within(card).getByLabelText('Motivo de rechazo'),
      'Espacio no disponible',
    )
    await user.click(
      within(card).getByRole('button', { name: 'Confirmar rechazo' }),
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/reservations/${reservationId}/reject`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ reason: 'Espacio no disponible' }),
      }),
    )
    expect(await screen.findByText('RECHAZADA')).toBeInTheDocument()
  })

  it('loads and displays reservation history', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([reservation]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: 'a89c4c78-32a0-4b2b-8c12-48e42a4c82b6',
              reservation_id: reservationId,
              actor_user_id: 'b98c4c78-32a0-4b2b-8c12-48e42a4c82b6',
              old_status: null,
              new_status: 'PENDIENTE',
              reason: null,
              created_at: '2026-02-01T10:00:00Z',
            },
          ]),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/reservations']}>
        <Routes>
          <Route
            path="/admin/reservations"
            element={<AdminReservationsPage />}
          />
        </Routes>
      </MemoryRouter>,
    )

    const card = await screen.findByRole('article', {
      name: 'Auditorio Central',
    })
    await user.click(within(card).getByRole('button', { name: 'Ver historial' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/reservations/${reservationId}/history`,
      expect.any(Object),
    )
    expect(await screen.findByText('Creada → PENDIENTE')).toBeInTheDocument()
    expect(screen.getByText(/Usuario b98c4c78/)).toBeInTheDocument()
  })
})
