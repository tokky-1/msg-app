import { useEffect } from 'react'
import { Bubble } from '../components/Bubble'
import { Logo } from '../components/Logo'

/* The one place in the app that moves on its own: a conversation writes
   itself, the wordmark lands, and the screen hands over. Skippable by click or
   key, and reduced motion drops straight through it. */

const REDUCED = '(prefers-reduced-motion: reduce)'

export function Splash({ onDone }) {
  useEffect(() => {
    const quick = window.matchMedia?.(REDUCED).matches
    const timer = window.setTimeout(onDone, quick ? 250 : 3000)

    const skip = () => {
      window.clearTimeout(timer)
      onDone()
    }
    window.addEventListener('pointerdown', skip)
    window.addEventListener('keydown', skip)

    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('pointerdown', skip)
      window.removeEventListener('keydown', skip)
    }
  }, [onDone])

  return (
    <div className="splash on-ink" role="status" aria-label="Opening MSG">
      <div className="splash-inner">
        <Bubble>you up?</Bubble>
        <Bubble mine>always</Bubble>
        <Bubble>good. talk to me</Bubble>
        <Logo size="lg" className="splash-mark" />
      </div>
      <button type="button" className="btn-text splash-skip" onClick={onDone}>
        Skip
      </button>
    </div>
  )
}
