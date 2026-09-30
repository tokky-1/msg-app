import { useState } from 'react'
import { Field } from '../components/Field'
import { useSession } from '../lib/sessionContext'
import { Link } from '../lib/router'
import { navigate } from '../lib/routing'

export function SignUp() {
  const { register } = useSession()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [touched, setTouched] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }))

  const shortPassword = form.password.length > 0 && form.password.length < 8
  const missing = !form.username.trim() || !form.email.trim() || !form.password

  async function onSubmit(event) {
    event.preventDefault()
    setTouched(true)
    if (missing || shortPassword) return
    setBusy(true)
    setError('')
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
      })
      navigate('/chats')
    } catch (problem) {
      setError(problem.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth">
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <h1 className="auth-title">Create an account</h1>
        <p className="auth-sub">
          Three fields, then you can message anyone whose username you know.
        </p>

        {error || (touched && missing) ? (
          <p className="form-error" role="alert">
            {error || 'Every field is needed before the account can be created.'}
          </p>
        ) : null}

        <Field
          label="Username"
          name="username"
          autoComplete="username"
          placeholder="e.g. adaeze"
          note="Lowercase, no spaces. People use this to reach you."
          value={form.username}
          onChange={set('username')}
        />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={form.email}
          onChange={set('email')}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          placeholder="Choose a password"
          invalid={shortPassword}
          note={shortPassword ? 'Use at least 8 characters.' : 'At least 8 characters.'}
          value={form.password}
          onChange={set('password')}
        />

        <button type="submit" className="btn btn-solid btn-full auth-submit" disabled={busy}>
          {busy ? 'Creating…' : 'Create account'}
        </button>

        <p className="auth-swap">
          Already registered?{' '}
          <Link to="/login" className="btn-text">
            Log in
          </Link>
        </p>
      </form>
    </main>
  )
}
