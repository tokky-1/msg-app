import { useState } from 'react'
import { Field } from '../components/Field'
import { useSession } from '../lib/sessionContext'
import { Link } from '../lib/router'
import { navigate } from '../lib/routing'

export function Login() {
  const { logIn } = useSession()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }))

  async function onSubmit(event) {
    event.preventDefault()
    if (!form.username.trim() || !form.password) {
      setError('Fill in both fields to log in.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await logIn({ username: form.username.trim(), password: form.password })
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
        <h1 className="auth-title">Log in</h1>
        <p className="auth-sub">Pick up wherever you left the conversation.</p>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        <Field
          label="Username"
          name="username"
          autoComplete="username"
          placeholder="e.g. adaeze"
          value={form.username}
          onChange={set('username')}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="Your password"
          value={form.password}
          onChange={set('password')}
        />

        <button type="submit" className="btn btn-solid btn-full auth-submit" disabled={busy}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>

        <p className="auth-swap">
          No account yet?{' '}
          <Link to="/signup" className="btn-text">
            Create one
          </Link>
        </p>
      </form>
    </main>
  )
}
