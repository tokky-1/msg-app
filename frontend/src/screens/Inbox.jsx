import { useMemo, useState } from 'react'
import { Avatar } from '../components/Avatar'
import { NewChatLink, ProfileLink, ScreenHeader } from '../components/ScreenHeader'
import { stamp } from '../lib/format'
import { Link } from '../lib/router'
import { useSession } from '../lib/sessionContext'

export function Inbox() {
  const { account, inbox, inboxState, refreshInbox } = useSession()
  const [query, setQuery] = useState('')

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return inbox
    return inbox.filter(
      (item) =>
        item.partner_username.includes(needle) ||
        item.message.content.toLowerCase().includes(needle),
    )
  }, [inbox, query])

  return (
    <div className="screen">
      <ScreenHeader
        lead={<ProfileLink username={account.username} />}
        title="Chats"
        action={<NewChatLink />}
      >
        <div className="head-search-wrap">
          <svg
            className="head-search-icon"
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="7" cy="7" r="4.75" stroke="currentColor" strokeWidth="1.75" />
            <path
              d="m10.75 10.75 3 3"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
            />
          </svg>
          <label className="sr-only" htmlFor="chat-search">
            Search chats
          </label>
          <input
            id="chat-search"
            className="head-search"
            type="search"
            placeholder="Search chats"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      </ScreenHeader>

      <div className="screen-scroll">
        {inboxState.status === 'error' ? (
          <div className="page-body">
            <div className="empty">
              <h2 className="empty-title">Cannot load your chats</h2>
              <p className="empty-text">{inboxState.error}</p>
              <button type="button" className="btn btn-solid" onClick={refreshInbox}>
                Try again
              </button>
            </div>
          </div>
        ) : inboxState.status === 'loading' && inbox.length === 0 ? (
          <p className="page-body prose">Loading your chats…</p>
        ) : inbox.length === 0 ? (
          <div className="page-body">
            <div className="empty">
              <h2 className="empty-title">No chats yet</h2>
              <p className="empty-text">
                You only need someone&rsquo;s username to start. Once you send the first
                message, the conversation shows up here.
              </p>
              <Link to="/new" className="btn btn-solid">
                Start a chat
              </Link>
            </div>
          </div>
        ) : shown.length === 0 ? (
          <div className="page-body">
            <div className="empty">
              <h2 className="empty-title">Nothing matches &ldquo;{query.trim()}&rdquo;</h2>
              <p className="empty-text">
                Search looks at usernames and the latest message in each chat.
              </p>
            </div>
          </div>
        ) : (
          <ul className="chat-list">
            {shown.map(({ message, partner_username: partner, unread }) => {
              const mine = message.sender_id === account.id
              return (
                <li className="chat-row" key={partner}>
                  <Link to={`/chats/${partner}`} className="chat-link">
                    <Avatar username={partner} />
                    <span>
                      <span className="chat-name">{partner}</span>
                      <span className={`chat-preview ${mine ? 'chat-preview-you' : ''}`.trim()}>
                        <span className="sr-only">
                          {mine ? 'You said: ' : `${partner} said: `}
                        </span>
                        {message.content}
                      </span>
                    </span>
                    <span className="chat-side">
                      <span className="chat-time">{stamp(message.timestamp)}</span>
                      {unread ? (
                        <span className="chat-unread">
                          {unread}
                          <span className="sr-only"> unread</span>
                        </span>
                      ) : null}
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
