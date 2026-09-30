import { Avatar } from './Avatar'
import { Link } from '../lib/router'

/* The header is the navigation. There are no tabs: the profile icon opens the
   account, the plus starts a chat, and a back arrow returns from either. */

export function ScreenHeader({ lead, title, small = false, sub, action, children }) {
  return (
    <header className="head">
      <div className="head-row">
        {lead}
        <div className="head-title-wrap">
          <h1 className={`head-title ${small ? 'head-title-sm' : ''}`.trim()}>{title}</h1>
          {sub ? <p className="head-sub">{sub}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </header>
  )
}

export function ProfileLink({ username }) {
  return (
    <Link to="/me" className="head-avatar" aria-label="Your account">
      <Avatar username={username} you />
    </Link>
  )
}

export function BackLink({ to = '/chats', label = 'Back to chats' }) {
  return (
    <Link to={to} className="head-round head-back" aria-label={label}>
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path
          d="M11 3.5 5.5 9l5.5 5.5"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </Link>
  )
}

export function NewChatLink() {
  return (
    <Link to="/new" className="head-round head-add" aria-label="New chat">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path d="M9 3.5v11M3.5 9h11" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      </svg>
    </Link>
  )
}
