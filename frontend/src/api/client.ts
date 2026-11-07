import { apiBaseUrl } from '../config'
import {
  AUTH_UNAUTHORIZED_EVENT,
  clearAccessToken,
  getAccessToken,
} from './session'

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(
    status: number,
    detail: unknown,
  ) {
    super(getApiErrorMessage(status, detail))
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function getApiErrorMessage(status: number, detail: unknown): string {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (
        typeof item === 'object' &&
        item !== null &&
        'msg' in item &&
        typeof item.msg === 'string'
      ) {
        return [item.msg]
      }

      return []
    })
    if (messages.length > 0) {
      return messages.join(' ')
    }
  }

  if (
    typeof detail === 'object' &&
    detail !== null &&
    'message' in detail &&
    typeof detail.message === 'string'
  ) {
    return detail.message
  }

  return `La solicitud no pudo completarse (HTTP ${status}).`
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  const accessToken = path === '/auth/login' ? null : getAccessToken()
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers,
  })
  const responseText = await response.text()
  let payload: unknown

  if (responseText) {
    try {
      payload = JSON.parse(responseText)
    } catch {
      payload = responseText
    }
  }

  if (!response.ok) {
    if (response.status === 401 && headers.has('Authorization')) {
      clearAccessToken()
      window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT))
    }
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? payload.detail
        : payload
    throw new ApiError(response.status, detail)
  }

  return payload as T
}
