import { expect, test } from '@playwright/test'

const spaceId = 'c94c0c78-32a0-4b2b-8c12-48e42a4c82b6'
const reservationId = 'a89c4c78-32a0-4b2b-8c12-48e42a4c82b6'
const spaces = [
  {
    id: spaceId,
    name: 'Auditorio Central',
    type: 'AUDITORIO',
    capacity: 120,
    status: 'ACTIVO',
  },
]

test('visitor registers, verifies email, and activates the initial administrator', async ({
  page,
}) => {
  await page.route('**/api/auth/register', async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      name: 'Alex Docente',
      email: 'alex@example.com',
      password: 'secure-password-123',
    })
    await route.fulfill({
      json: { message: 'Registro recibido.' },
      status: 201,
    })
  })
  await page.route('**/api/auth/verify', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ token: 'verify-token' })
    await route.fulfill({ json: { message: 'Correo verificado.' } })
  })
  await page.route('**/api/auth/activate-admin', async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      token: 'seed-token',
      password: 'initial-admin-password',
    })
    await route.fulfill({ json: { message: 'Administrador activado.' } })
  })

  await page.goto('/register')
  await page.getByLabel('Nombre', { exact: true }).fill('Alex Docente')
  await page
    .getByLabel('Correo electrónico', { exact: true })
    .fill('alex@example.com')
  await page
    .getByLabel('Contraseña', { exact: true })
    .fill('secure-password-123')
  await page.getByRole('button', { name: 'Crear cuenta' }).click()
  await expect(page.getByRole('status')).toContainText('Revisa tu correo')

  await page.goto('/auth/verify#token=verify-token')
  await expect(page.getByRole('status')).toContainText('Correo verificado.')

  await page.goto('/auth/activate-admin#token=seed-token')
  await page
    .getByLabel('Nueva contraseña', { exact: true })
    .fill('initial-admin-password')
  await page.getByRole('button', { name: 'Activar administrador' }).click()
  await expect(page.getByRole('status')).toContainText('Administrador activado.')
})

test('enabled user checks availability and submits a reservation', async ({
  page,
}) => {
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      json: { access_token: 'user-token', token_type: 'bearer', expires_in: 3600 },
    })
  })
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ json: { role: 'USER' } })
  })
  await page.route('**/api/spaces', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: spaces })
      return
    }
    await route.fulfill({ status: 405 })
  })
  await page.route('**/api/spaces/*/availability?*', async (route) => {
    await route.fulfill({
      json: {
        occupied: [{ start: '10:00:00', end: '12:00:00' }],
        free: [{ start: '12:00:00', end: '21:00:00' }],
      },
    })
  })
  await page.route('**/api/reservations', async (route) => {
    if (route.request().method() === 'POST') {
      expect(route.request().postDataJSON()).toMatchObject({
        space_id: spaceId,
        start_time: '13:00',
        end_time: '14:00',
      })
      await route.fulfill({ status: 201, json: { status: 'PENDIENTE' } })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/login')
  await page
    .getByLabel('Correo electrónico', { exact: true })
    .fill('alex@example.com')
  await page
    .getByLabel('Contraseña', { exact: true })
    .fill('secure-password-123')
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(page).toHaveURL(/\/spaces$/)

  await page.getByLabel('Espacio', { exact: true }).selectOption(spaceId)
  await page.getByLabel('Fecha', { exact: true }).fill('2026-11-10')
  await page.getByRole('button', { name: 'Consultar' }).click()
  await expect(page.getByText('10:00–12:00')).toBeVisible()
  await expect(page.getByText('12:00–21:00')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Usuarios' })).toHaveCount(0)

  await page.getByRole('link', { name: 'Nueva solicitud' }).click()
  await page.getByLabel('Espacio', { exact: true }).selectOption(spaceId)
  await page.getByLabel('Fecha', { exact: true }).fill('2026-11-10')
  await page.getByLabel('Hora de inicio', { exact: true }).fill('13:00')
  await page.getByLabel('Hora de fin', { exact: true }).fill('14:00')
  await page.getByRole('button', { name: 'Enviar solicitud' }).click()
  await expect(page.getByRole('status')).toContainText('PENDIENTE')
})

test('administrator sees admin navigation and approves a reservation', async ({
  page,
}) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('reservas.accessToken', 'admin-token')
  })
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ json: { role: 'ADMIN' } })
  })
  await page.route('**/api/reservations', async (route) => {
    await route.fulfill({
      json: [
        {
          id: reservationId,
          status: 'PENDIENTE',
          space: 'Auditorio Central',
          date: '2026-11-10',
          start_time: '10:00:00',
          end_time: '12:00:00',
        },
      ],
    })
  })
  await page.route(`**/api/reservations/${reservationId}/approve`, async (route) => {
    await route.fulfill({ json: { status: 'APROBADA' } })
  })

  await page.goto('/admin/reservations')
  await expect(page.getByRole('link', { name: 'Usuarios' })).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Reservas', exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Aprobar' }).click()
  await expect(page.getByText('APROBADA', { exact: true })).toBeVisible()
})

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`keeps the spaces screen usable at ${viewport.name} size`, async ({
    page,
  }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    })
    await page.route('**/api/spaces', async (route) => {
      await route.fulfill({ json: spaces })
    })

    await page.goto('/spaces')
    await expect(
      page.getByRole('heading', { name: 'Espacios y disponibilidad' }),
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Consultar disponibilidad' }),
    ).toBeVisible()
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <=
          document.documentElement.clientWidth,
      ),
    ).toBe(true)
  })
}
