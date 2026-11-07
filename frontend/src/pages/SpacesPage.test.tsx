import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import SpacesPage from './SpacesPage'

const spaceId = 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6'
const spaces = [
  {
    id: spaceId,
    name: 'Auditorio Central',
    type: 'AUDITORIO',
    capacity: 120,
    status: 'ACTIVO',
  },
]

describe('SpacesPage', () => {
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

  it('lists API spaces and displays occupied and free intervals', async () => {
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
            space_id: spaceId,
            date: '2026-11-10',
            occupied: [{ start: '09:00:00', end: '10:00:00' }],
            free: [{ start: '07:00:00', end: '09:00:00' }],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route path="/spaces" element={<SpacesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByRole('option', { name: 'Auditorio Central' })
    await user.selectOptions(screen.getByLabelText('Espacio'), spaceId)
    await user.type(screen.getByLabelText('Fecha'), '2026-11-10')
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `/api/spaces/${spaceId}/availability?date=2026-11-10`,
      expect.any(Object),
    )
    expect(await screen.findByText('09:00–10:00')).toBeInTheDocument()
    expect(screen.getByText('07:00–09:00')).toBeInTheDocument()
  })

  it('shows the API 404 response for an unknown space', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(spaces), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Espacio no encontrado.' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route path="/spaces" element={<SpacesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByRole('option', { name: 'Auditorio Central' })
    await user.selectOptions(screen.getByLabelText('Espacio'), spaceId)
    await user.type(screen.getByLabelText('Fecha'), '2026-11-10')
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Espacio no encontrado.',
    )
  })

  it('shows a forbidden API response when spaces cannot be listed', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Usuario no habilitado.' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    render(
      <MemoryRouter initialEntries={['/spaces']}>
        <Routes>
          <Route path="/spaces" element={<SpacesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Usuario no habilitado.',
    )
  })
})
