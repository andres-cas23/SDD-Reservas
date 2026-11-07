const ACCESS_TOKEN_KEY = 'reservas.accessToken'
export const AUTH_UNAUTHORIZED_EVENT = 'reservas:unauthorized'
export const AUTHENTICATED_EVENT = 'reservas:authenticated'

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  window.dispatchEvent(new Event(AUTHENTICATED_EVENT))
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
}
