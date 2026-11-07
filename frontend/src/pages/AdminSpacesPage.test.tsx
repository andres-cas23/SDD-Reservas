import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AdminSpacesPage from './AdminSpacesPage'

const newSpace = {
  id: 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6',
  name: 'Laboratorio Norte',
  type: 'LABORATORIO',
  capacity: 24,
  status: 'ACTIVO',
}

describe('AdminSpacesPage', () => {
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

  it('creates a space through the API and adds the response to the catalog', async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(newSpace), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/spaces']}>
        <Routes>
          <Route path="/admin/spaces" element={<AdminSpacesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Nombre'), 'Laboratorio Norte')
    await user.selectOptions(screen.getByLabelText('Tipo'), 'LABORATORIO')
    await user.type(screen.getByLabelText('Capacidad'), '24')
    await user.selectOptions(screen.getByLabelText('Estado'), 'ACTIVO')
    await user.click(screen.getByRole('button', { name: 'Registrar espacio' }))

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/spaces',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'Laboratorio Norte',
          type: 'LABORATORIO',
          capacity: 24,
          status: 'ACTIVO',
        }),
      }),
    )
    expect(await screen.findByText('Se registró el espacio Laboratorio Norte.')).toBeInTheDocument()
    expect(screen.getByText('LABORATORIO · Capacidad 24 · ACTIVO')).toBeInTheDocument()
  })
})
