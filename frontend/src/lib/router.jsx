import { useCallback, useEffect, useState } from 'react'
import { RouteContext, navigate, readPath } from './routing'

/* A hash router in a few lines, so the flow has real URLs without pulling in a
   routing dependency. Swap for react-router when the screens get wired up. */

export function RouterProvider({ children }) {
  const [path, setPath] = useState(readPath)

  useEffect(() => {
    const onChange = () => setPath(readPath())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return <RouteContext value={path}>{children}</RouteContext>
}

export function Link({ to, children, ...rest }) {
  const onClick = useCallback(
    (event) => {
      // Let the browser handle modified clicks — the href is a real URL.
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
      event.preventDefault()
      navigate(to)
    },
    [to],
  )

  return (
    <a href={`#${to}`} onClick={onClick} {...rest}>
      {children}
    </a>
  )
}
