import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import MyReservationsPage from './MyReservationsPage'

const pendingId = 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6'
const approvedId = '8d65d2be-cfcc-4851-b15c-54a04a5ecf1f'
const rejectedId = 'f865bb9a-3ca4-46e7-9c2c-2a7fb5af2cc2'
const cancelledId = 'c20dd77f-4441-4f58-bf69-0e07697f15f7'

const reservations = [
  {
    id: pendingId,
    status: 'PENDIENTE',
    space: 'Auditorio Central',
    date: '2026-11-10',
    start_time: '10:00:00',
    end_time: '12:00:00',
  },
  {
    id: approvedId,
    status: 'APROBADA',
    space: 'Laboratorio A',
    date: '2026-11-11',
    start_time: '13:00:00',
    end_time: '14:00:00',
  },
  {
    id: rejectedId,
    status: 'RECHAZADA',
    space: 'Sala de cómputo',
    date: '2026-11-12',
    start_time: '15:00:00',
    end_time: '16:00:00',
  },
  {
    id: cancelledId,
    status: 'CANCELADA',
    space: 'Aula magna',
    date: '2026-11-13',
    start_time: '09:00:00',
    end_time: '10:00:00',
  },
]

function renderMyReservationsPage() {
  return render(
    <MemoryRouter initialEntries={['/reservations/mine']}>
      <Routes>
        <Route path="/reservations/mine" element={<MyReservationsPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('MyReservationsPage', () => {
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

  it('displays reservations from the API and only offers cancellation for active states', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(reservations), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    renderMyReservationsPage()

    expect(await screen.findByText('Auditorio Central')).toBeInTheDocument()
    expect(screen.getByText('Laboratorio A')).toBeInTheDocument()
    expect(screen.getByText('Sala de cómputo')).toBeInTheDocument()
    expect(screen.getByText('Aula magna')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Ver historial' })).toHaveLength(4)
    expect(screen.getAllByRole('button', { name: 'Cancelar reserva' })).toHaveLength(2)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/reservations',
      expect.objectContaining({ headers: expect.any(Headers) }),
    )
  })

  it('requests and displays the selected reservation history', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([reservations[0]]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: 'history-id',
              reservation_id: pendingId,
              actor_user_id: 'user-id',
              old_status: null,
              new_status: 'PENDIENTE',
              reason: null,
              created_at: '2026-11-06T19:00:00Z',
            },
          ]),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    const user = userEvent.setup()
    renderMyReservationsPage()

    const card = await screen.findByRole('article', {
      name: 'Auditorio Central',
    })
    await user.click(within(card).getByRole('button', { name: 'Ver historial' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/reservations/${pendingId}/history`,
      expect.any(Object),
    )
    expect(await screen.findByText('Creada → PENDIENTE')).toBeInTheDocument()
    expect(
      screen.getByText('2026-11-06T19:00:00.000Z UTC · Usuario user-id'),
    ).toBeInTheDocument()
  })

  it('cancels a pending reservation with its reason and updates its state', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([reservations[0]]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'CANCELADA' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    renderMyReservationsPage()

    const card = await screen.findByRole('article', {
      name: 'Auditorio Central',
    })
    await user.click(
      within(card).getByRole('button', { name: 'Cancelar reserva' }),
    )
    await user.type(
      within(card).getByLabelText('Motivo de cancelación'),
      'Cambio de horario',
    )
    await user.click(
      within(card).getByRole('button', { name: 'Confirmar cancelación' }),
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/reservations/${pendingId}/cancel`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ reason: 'Cambio de horario' }),
      }),
    )
    expect(await screen.findByText('La reserva se canceló.')).toBeInTheDocument()
    expect(within(card).getByText('CANCELADA')).toBeInTheDocument()
    expect(
      within(card).queryByRole('button', { name: 'Cancelar reserva' }),
    ).not.toBeInTheDocument()
  })

  it('displays API errors when loading reservations fails', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Acceso denegado.' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    renderMyReservationsPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Acceso denegado.',
    )
  })
})
