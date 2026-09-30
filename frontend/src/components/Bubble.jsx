/* Sky is you, blush is them — the same split the API stores as
   sender_id / receiver_id. The cut corner repeats it in shape.
   `ghost` is an outline in place of a fill: a bubble waiting to be filled in. */
export function Bubble({ mine = false, ghost = false, children, className = '' }) {
  const tone = mine ? 'bubble-you' : 'bubble-them'
  const classes = ['bubble', tone, ghost && 'bubble-ghost', className].filter(Boolean)
  return <div className={classes.join(' ')}>{children}</div>
}

export function Dots() {
  return (
    <span className="dots" aria-label="Typing">
      <span />
      <span />
      <span />
    </span>
  )
}
