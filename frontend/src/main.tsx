import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import AppShell from './App'
import './index.css'
import RegisterPage from './pages/RegisterPage'
import LoginPage from './pages/LoginPage'
import VerificationPage from './pages/VerificationPage'
import AdminActivationPage from './pages/AdminActivationPage'
import SpacesPage from './pages/SpacesPage'
import ReservationRequestPage from './pages/ReservationRequestPage'
import MyReservationsPage from './pages/MyReservationsPage'
import AdminUsersPage from './pages/AdminUsersPage'
import AdminReservationsPage from './pages/AdminReservationsPage'
import AdminSpacesPage from './pages/AdminSpacesPage'
import ScreenPreview from './ScreenPreview'

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <ScreenPreview /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'auth/verify', element: <VerificationPage /> },
      { path: 'auth/activate-admin', element: <AdminActivationPage /> },
      { path: 'spaces', element: <SpacesPage /> },
      { path: 'reservations/new', element: <ReservationRequestPage /> },
      { path: 'reservations/mine', element: <MyReservationsPage /> },
      { path: 'admin/users', element: <AdminUsersPage /> },
      { path: 'admin/reservations', element: <AdminReservationsPage /> },
      { path: 'admin/spaces', element: <AdminSpacesPage /> },
      { path: '*', element: <ScreenPreview /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
