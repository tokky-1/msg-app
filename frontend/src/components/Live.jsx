/* Our own socket, nothing more. The backend has no presence broadcast, so
   this says whether *this* client is connected - never whether the other
   person is around, which is what "Online" would promise.
   Red is the dot; the word carries the meaning, so it still reads with
   colour stripped out. */
export function Live({ on = true, label }) {
  return (
    <span className={`live ${on ? 'live-on' : 'live-off'}`}>
      <span className="live-dot" aria-hidden="true" />
      <span className="live-label">{label ?? (on ? 'Connected' : 'Reconnecting…')}</span>
    </span>
  )
}
