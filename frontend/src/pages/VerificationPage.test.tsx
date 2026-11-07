import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import VerificationPage from './VerificationPage'

describe('VerificationPage', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('sends the token from the email-link fragment and displays the API result', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ message: 'Cuenta verificada.' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    render(
      <MemoryRouter initialEntries={['/auth/verify#token=verify-secret']}>
        <Routes>
          <Route path="/auth/verify" element={<VerificationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Cuenta verificada.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/verify',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ token: 'verify-secret' }),
      }),
    )
  })

  it('submits the resend email and displays an API error response', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'No se puede reenviar en este momento.' }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/auth/verify']}>
        <Routes>
          <Route path="/auth/verify" element={<VerificationPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(
      screen.getByLabelText('Correo para reenviar verificación'),
      'ana@example.com',
    )
    await user.click(screen.getByRole('button', { name: 'Reenviar enlace' }))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/resend-verification',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'ana@example.com' }),
      }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se puede reenviar en este momento.',
    )
  })
})
