const DAY = 86_400_000

const time = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })
const weekday = new Intl.DateTimeFormat(undefined, { weekday: 'long' })
const dayMonth = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' })
const fullDay = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

function midnight(date) {
  const copy = new Date(date)
  copy.setHours(0, 0, 0, 0)
  return copy.getTime()
}

export function clockTime(iso) {
  return time.format(new Date(iso))
}

/* Inbox stamps: today shows a clock, this week a weekday, older a date. */
export function stamp(iso) {
  const then = new Date(iso)
  const days = Math.round((midnight(new Date()) - midnight(then)) / DAY)
  if (days <= 0) return time.format(then)
  if (days === 1) return 'Yesterday'
  if (days < 7) return weekday.format(then)
  return dayMonth.format(then)
}

/* Separators inside a thread. */
export function dayLabel(iso) {
  const then = new Date(iso)
  const days = Math.round((midnight(new Date()) - midnight(then)) / DAY)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  return fullDay.format(then)
}

export function sameDay(a, b) {
  return midnight(new Date(a)) === midnight(new Date(b))
}
