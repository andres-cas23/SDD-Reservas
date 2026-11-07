import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ReservationRequestPage from './ReservationRequestPage'

const spaceId = 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6'
const spaces = [
  {
    id: spaceId,
    name: 'Auditorio Central',
    type: 'AUDITORIO',
    status: 'ACTIVO',
  },
]

function renderReservationPage() {
  return render(
    <MemoryRouter initialEntries={['/reservations/new']}>
      <Routes>
        <Route
          path="/reservations/new"
          element={<ReservationRequestPage />}
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ReservationRequestPage', () => {
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

  it('sends the selected space, date, and times to the API', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(spaces), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'PENDIENTE' }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    renderReservationPage()

    await screen.findByRole('option', {
      name: 'Auditorio Central · AUDITORIO · ACTIVO',
    })
    await user.selectOptions(screen.getByLabelText('Espacio'), spaceId)
    await user.type(screen.getByLabelText('Fecha'), '2026-11-10')
    await user.type(screen.getByLabelText('Hora de inicio'), '09:00')
    await user.type(screen.getByLabelText('Hora de fin'), '10:00')
    await user.click(screen.getByRole('button', { name: 'Enviar solicitud' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/reservations',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          space_id: spaceId,
          date: '2026-11-10',
          start_time: '09:00',
          end_time: '10:00',
        }),
      }),
    )
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Solicitud creada. Estado: PENDIENTE.',
    )
  })

  it('displays the API conflict response', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(spaces), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: {
              message: 'El horario se cruza con una reserva aprobada.',
              reservation_id: 'reservation-conflict',
            },
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    const user = userEvent.setup()
    renderReservationPage()

    await screen.findByRole('option', {
      name: 'Auditorio Central · AUDITORIO · ACTIVO',
    })
    await user.selectOptions(screen.getByLabelText('Espacio'), spaceId)
    await user.type(screen.getByLabelText('Fecha'), '2026-11-10')
    await user.type(screen.getByLabelText('Hora de inicio'), '09:00')
    await user.type(screen.getByLabelText('Hora de fin'), '10:00')
    await user.click(screen.getByRole('button', { name: 'Enviar solicitud' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El horario se cruza con una reserva aprobada.',
    )
  })

  it('associates API 422 validation details with the corresponding field', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(spaces), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: [
              {
                loc: ['body', 'end_time'],
                msg: 'Formato de hora inválido.',
                type: 'time_parsing',
              },
            ],
          }),
          { status: 422, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    const user = userEvent.setup()
    renderReservationPage()

    await screen.findByRole('option', {
      name: 'Auditorio Central · AUDITORIO · ACTIVO',
    })
    await user.selectOptions(screen.getByLabelText('Espacio'), spaceId)
    await user.type(screen.getByLabelText('Fecha'), '2026-11-10')
    await user.type(screen.getByLabelText('Hora de inicio'), '09:00')
    await user.type(screen.getByLabelText('Hora de fin'), '10:00')
    await user.click(screen.getByRole('button', { name: 'Enviar solicitud' }))

    const endTimeInput = screen.getByLabelText('Hora de fin')
    expect(endTimeInput).toHaveAttribute('aria-invalid', 'true')
    expect(await screen.findByText('Formato de hora inválido.')).toBeInTheDocument()
  })
})
