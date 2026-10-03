/* Every endpoint the backend exposes, in one place.
   Backend: backend/routes/{auth,message,ws,health}.py */

const configured = import.meta.env.VITE_API_URL
if (!configured) {
  // No silent fallback to localhost: a build pointed at nothing should say so
  // here rather than fail later as "undefined is not a function".
  throw new Error(
    'VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env, or set it in the build environment.',
  )
}
const BASE = configured.replace(/\/$/, '')

const REQUEST_TIMEOUT_MS = 15000

let token = null

export function setToken(next) {
  token = next
}

/* Carries the status so callers can tell "wrong password" (401 on login) from
   "your session expired" (401 on anything else). */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/* main.py answers its own errors with a string `detail`, but FastAPI's own
   422 answers with a list of {loc, msg, type}. Handing that list to Error()
   renders it "[object Object]", so pull the field names and messages out. */
function describeProblem(detail, status) {
  if (typeof detail === 'string' && detail) return detail

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        const field = Array.isArray(item?.loc)
          ? item.loc.filter((part) => part !== 'body' && part !== 'query').join('.')
          : ''
        const message = item?.msg ?? 'is not valid'
        return field ? `${field}: ${message}` : message
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }

  return `Request failed with ${status}`
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  let response
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : null),
        ...(auth && token ? { Authorization: `Bearer ${token}` } : null),
      },
      body: body ? JSON.stringify(body) : undefined,
      // fetch waits forever by default. A port that accepts the connection and
      // then never answers - a container mid-restart is the usual one - would
      // otherwise leave the screen on "Loading…" with nothing to report.
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    })
  } catch (problem) {
    if (problem?.name === 'TimeoutError') {
      throw new ApiError('The server did not answer in time.', 0)
    }
    // fetch only rejects otherwise when the request never got a reply at all.
    throw new ApiError('Cannot reach the server. Check that it is running.', 0)
  }

  if (!response.ok) {
    const problem = await response.json().catch(() => null)
    throw new ApiError(describeProblem(problem?.detail, response.status), response.status)
  }

  if (response.status === 204) return null
  return response.json().catch(() => null)
}

/* POST /auth/register -> { id, username, email } */
export const register = (data) =>
  request('/auth/register', { method: 'POST', body: data, auth: false })

/* POST /auth/login -> { access_token, token_type } */
export const login = (data) => request('/auth/login', { method: 'POST', body: data, auth: false })

/* GET /auth/me -> { id, username, email } */
export const me = () => request('/auth/me')

/* GET /auth/users/{username} -> { id, username, email } */
export const getUser = (username) => request(`/auth/users/${encodeURIComponent(username)}`)

/* GET /messages/inbox -> [{ message, partner_username }] */
export const inbox = () => request('/messages/inbox')

/* GET /messages/conversation/{username} -> [message] */
export const conversation = (username, { limit = 50, offset = 0 } = {}) =>
  request(`/messages/conversation/${encodeURIComponent(username)}?limit=${limit}&offset=${offset}`)

/* POST /messages -> message */
export const sendMessage = (receiverId, content) =>
  request('/messages', { method: 'POST', body: { receiver_id: receiverId, content } })

/* GET /messages/{id} -> message */
export const getMessage = (id) => request(`/messages/${id}`)

/* PATCH /messages/{id} -> message */
export const editMessage = (id, content) =>
  request(`/messages/${id}`, { method: 'PATCH', body: { content } })

/* DELETE /messages/{id} */
export const deleteMessage = (id) => request(`/messages/${id}`, { method: 'DELETE' })

/* GET /health and GET /ready */
export const health = () => request('/health', { auth: false })
export const ready = () => request('/ready', { auth: false })

/* GET /ws?token=... — the socket takes the token as a query param because a
   browser cannot set an Authorization header on a WebSocket. Frames arrive as
   { type: "message", message } or { type: "error", error }. */
export function openSocket(accessToken) {
  const url = new URL('/ws', BASE)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', accessToken)
  return new WebSocket(url)
}
