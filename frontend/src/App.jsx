import { useCallback, useEffect, useState } from 'react'
import { navigate, useMatch, useRoute } from './lib/routing'
import { useSession } from './lib/sessionContext'
import { Account } from './screens/Account'
import { Conversation } from './screens/Conversation'
import { Inbox } from './screens/Inbox'
import { Login } from './screens/Login'
import { NewChat } from './screens/NewChat'
import { Shell } from './screens/Shell'
import { SignUp } from './screens/SignUp'
import { Splash } from './screens/Splash'
import { Welcome } from './screens/Welcome'

const PUBLIC = ['/welcome', '/login', '/signup']

export default function App() {
  const path = useRoute()
  const conversation = useMatch('/chats/:username')
  const { account, status } = useSession()
  const [splashDone, setSplashDone] = useState(false)

  const onSplashDone = useCallback(() => setSplashDone(true), [])

  // The landing screen only ever hands over to one of two places.
  useEffect(() => {
    if (path !== '/' || !splashDone || status === 'loading') return
    navigate(account ? '/chats' : '/welcome', { replace: true })
  }, [path, splashDone, account, status])

  // Keep the URL honest in both directions: signed out on a private screen
  // goes back to the welcome, signed in on an auth screen goes to the chats.
  useEffect(() => {
    if (path === '/' || status === 'loading') return
    if (!account && !PUBLIC.includes(path)) navigate('/welcome', { replace: true })
    else if (account && PUBLIC.includes(path)) navigate('/chats', { replace: true })
  }, [path, account, status])

  if (path === '/' || !splashDone) return <Splash onDone={onSplashDone} />

  // A stored token is being checked against /auth/me. Showing the welcome here
  // would flash a signed-out screen at someone who is already signed in.
  if (status === 'loading') return <div className="frame" />

  if (!account) {
    if (path === '/login') return <Login />
    if (path === '/signup') return <SignUp />
    return <Welcome />
  }

  if (conversation) {
    return (
      <Shell>
        <Conversation username={conversation.username} />
      </Shell>
    )
  }

  return (
    <Shell>
      {path === '/new' ? <NewChat /> : path === '/me' ? <Account /> : <Inbox />}
    </Shell>
  )
}
