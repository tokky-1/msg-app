import { Avatar } from '../components/Avatar'
import { Live } from '../components/Live'
import { BackLink, ScreenHeader } from '../components/ScreenHeader'
import { navigate } from '../lib/routing'
import { useSession } from '../lib/sessionContext'

export function Account() {
  const { account, inbox, online, signOut } = useSession()

  return (
    <div className="screen">
      <ScreenHeader
        lead={<BackLink />}
        title="Account"
        small
        sub="Who you are on this server"
        action={<Live on={online} label={online ? 'Socket connected' : 'Socket closed'} />}
      />

      <div className="screen-scroll">
        <div className="page-body">
          <div className="profile-id">
            <Avatar username={account.username} you large />
            <div>
              <h2 className="profile-name">{account.username}</h2>
              <p className="profile-mail">{account.email}</p>
            </div>
          </div>

          <dl className="facts">
            <div className="fact">
              <dt className="fact-key">Conversations</dt>
              <dd className="fact-val">{inbox.length}</dd>
            </div>
            <div className="fact">
              <dt className="fact-key">Messages you can edit or delete</dt>
              <dd className="fact-val">Only your own</dd>
            </div>
            <div className="fact">
              <dt className="fact-key">Delivery</dt>
              <dd className="fact-val">Over WebSocket</dd>
            </div>
            <div className="fact">
              <dt className="fact-key">Server</dt>
              <dd className="fact-val">{import.meta.env.VITE_API_URL ?? 'Not configured'}</dd>
            </div>
          </dl>

          <p className="prose account-note">
            Logging out clears the token from this browser. Your messages stay on the server.
          </p>

          <button
            type="button"
            className="btn btn-signout account-out"
            onClick={() => {
              signOut()
              navigate('/welcome')
            }}
          >
            Log out
          </button>
        </div>
      </div>
    </div>
  )
}
