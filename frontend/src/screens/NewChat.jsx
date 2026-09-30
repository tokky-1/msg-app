import { useState } from 'react'
import { Field } from '../components/Field'
import { BackLink, ScreenHeader } from '../components/ScreenHeader'
import { navigate } from '../lib/routing'
import { useSession } from '../lib/sessionContext'

export function NewChat() {
  const { resolvePartner } = useSession()
  const [username, setUsername] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  async function onSubmit(event) {
    event.preventDefault()
    const name = username.trim().toLowerCase()
    if (!name) {
      setError('Enter a username to start a chat.')
      return
    }
    setChecking(true)
    setError('')
    try {
      // Confirms the account exists and caches its id, which is what sending
      // a message actually needs.
      await resolvePartner(name)
      navigate(`/chats/${name}`)
    } catch (problem) {
      setError(problem.message)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="screen">
      <ScreenHeader
        lead={<BackLink />}
        title="New chat"
        small
        sub="Conversations open by username"
      />

      <div className="screen-scroll">
        <div className="page-body">
          <form className="form-narrow" onSubmit={onSubmit} noValidate>
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            <Field
              label="Who do you want to message?"
              name="username"
              placeholder="e.g. mariam"
              note="Usernames are lowercase and unique."
              invalid={Boolean(error)}
              value={username}
              onChange={(event) => {
                setUsername(event.target.value)
                setError('')
              }}
            />
            <button
              type="submit"
              className="btn btn-solid btn-full auth-submit"
              disabled={checking}
            >
              {checking ? 'Checking…' : 'Open chat'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
