import { createContext, useContext } from 'react'

/* Router internals: the context plus everything that isn't a component.
   The provider and Link live in router.jsx so fast refresh keeps working. */

export const RouteContext = createContext('/')

export function readPath() {
  const raw = window.location.hash.replace(/^#/, '')
  return raw.startsWith('/') ? raw : '/'
}

export function navigate(path, { replace = false } = {}) {
  const next = `#${path}`
  if (window.location.hash === next) return
  if (replace) window.location.replace(next)
  else window.location.hash = next
}

export function useRoute() {
  return useContext(RouteContext)
}

/* Matches "/chats/:username" against the current path: null on a miss, the
   params object on a hit. */
export function useMatch(pattern) {
  const path = useRoute()
  const patternParts = pattern.split('/').filter(Boolean)
  const pathParts = path.split('/').filter(Boolean)
  if (patternParts.length !== pathParts.length) return null

  const params = {}
  for (let i = 0; i < patternParts.length; i += 1) {
    const key = patternParts[i]
    if (key.startsWith(':')) params[key.slice(1)] = decodeURIComponent(pathParts[i])
    else if (key !== pathParts[i]) return null
  }
  return params
}
