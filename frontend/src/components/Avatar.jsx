export function Avatar({ username, you = false, large = false }) {
  const classes = ['avatar', you && 'avatar-you', large && 'avatar-lg']
    .filter(Boolean)
    .join(' ')
  return (
    <span className={classes} aria-hidden="true">
      {username.slice(0, 1)}
    </span>
  )
}
