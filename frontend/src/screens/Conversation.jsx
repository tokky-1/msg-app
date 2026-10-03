import { Fragment, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Avatar } from '../components/Avatar'
import { Live } from '../components/Live'
import { BackLink } from '../components/ScreenHeader'
import { clockTime, dayLabel, sameDay } from '../lib/format'
import { Link } from '../lib/router'
import { useSession } from '../lib/sessionContext'
import { DeleteDialog } from './DeleteDialog'

export function Conversation({ username }) {
  const {
    account,
    online,
    partners,
    threads,
    loadConversation,
    messagesWith,
    sendMessage,
    editMessage,
    deleteMessage,
    markRead,
  } = useSession()

  const person = partners[username]
  const thread = threads[username] ?? { status: 'loading', error: '' }
  const messages = messagesWith(username)

  const [draft, setDraft] = useState('')
  const [editing, setEditing] = useState(null)
  const [editDraft, setEditDraft] = useState('')
  const [pendingDelete, setPendingDelete] = useState(null)
  const [actionError, setActionError] = useState('')
  const [sending, setSending] = useState(false)

  const scroller = useRef(null)
  const composer = useRef(null)

  useEffect(() => {
    loadConversation(username)
  }, [loadConversation, username])

  useEffect(() => {
    markRead(username)
  }, [markRead, username, messages.length])

  // Pin to the newest message whenever the thread grows.
  useLayoutEffect(() => {
    const node = scroller.current
    if (node) node.scrollTop = node.scrollHeight
  }, [messages.length, username])

  if (thread.status === 'error') {
    return (
      <div className="screen">
        <header className="convo-head">
          <BackLink />
          <div className="convo-head-grow">
            <span className="convo-head-name">{username}</span>
          </div>
        </header>
        <div className="screen-scroll">
          <div className="page-body">
            <div className="empty">
              <h2 className="empty-title">Cannot open this chat</h2>
              <p className="empty-text">{thread.error}</p>
              <Link to="/chats" className="btn btn-solid">
                Back to chats
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  async function onSend(event) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || !person || sending) return
    setSending(true)
    setActionError('')
    try {
      // Resolves only once the server has stored the message, so a rejection
      // leaves the draft where it is instead of swallowing what was typed.
      await sendMessage(person.id, content)
      setDraft('')
      composer.current?.focus()
    } catch (error) {
      setActionError(error.message)
    } finally {
      setSending(false)
    }
  }

  function onComposerKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSend(event)
    }
  }

  function startEdit(message) {
    setEditing(message.id)
    setEditDraft(message.content)
  }

  async function saveEdit(event) {
    event.preventDefault()
    const content = editDraft.trim()
    const id = editing
    setEditing(null)
    if (!content) return
    try {
      await editMessage(id, content)
    } catch (error) {
      setActionError(error.message)
    }
  }

  async function confirmDelete() {
    const message = pendingDelete
    setPendingDelete(null)
    try {
      await deleteMessage(message.id)
    } catch (error) {
      setActionError(error.message)
    }
  }

  return (
    <div className="convo">
      <header className="convo-head">
        <BackLink />
        <Avatar username={username} />
        <div className="convo-head-grow">
          <span className="convo-head-name">{username}</span>
        </div>
        <Live on={online} />
      </header>

      <div className="convo-scroll" ref={scroller}>
        <div className="convo-thread">
          {thread.status === 'loading' && messages.length === 0 ? (
            <p className="convo-empty convo-empty-text">Loading this conversation…</p>
          ) : null}

          {thread.status === 'ready' && messages.length === 0 ? (
            <div className="convo-empty">
              <h2 className="convo-empty-title">Nothing here yet</h2>
              <p className="convo-empty-text">
                Say something to {username}. It lands the moment you send it.
              </p>
            </div>
          ) : null}

          {messages.map((message, index) => {
            const mine = message.sender_id === account.id
            const previous = messages[index - 1]
            const newDay = !previous || !sameDay(previous.timestamp, message.timestamp)

            if (editing === message.id) {
              return (
                <form className="msg msg-you msg-edit" key={message.id} onSubmit={saveEdit}>
                  <label className="sr-only" htmlFor="edit-field">
                    Edit your message
                  </label>
                  <textarea
                    id="edit-field"
                    className="composer-input"
                    rows={2}
                    autoFocus
                    placeholder="Edit your message"
                    value={editDraft}
                    onChange={(event) => setEditDraft(event.target.value)}
                  />
                  <div className="msg-edit-row">
                    <button
                      type="button"
                      className="btn btn-quiet btn-sm"
                      onClick={() => setEditing(null)}
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-solid btn-sm">
                      Save
                    </button>
                  </div>
                </form>
              )
            }

            return (
              <Fragment key={message.id}>
                {newDay ? <span className="convo-day">{dayLabel(message.timestamp)}</span> : null}
                <div className={`msg ${mine ? 'msg-you' : 'msg-them'}`}>
                  <div className={`bubble ${mine ? 'bubble-you' : 'bubble-them'}`}>
                    {message.content}
                    <span className="bubble-meta">{clockTime(message.timestamp)}</span>
                  </div>
                  {mine ? (
                    <div className="msg-tools">
                      <button type="button" className="msg-tool" onClick={() => startEdit(message)}>
                        Edit
                      </button>
                      <button
                        type="button"
                        className="msg-tool"
                        onClick={() => setPendingDelete(message)}
                      >
                        Delete
                      </button>
                    </div>
                  ) : null}
                </div>
              </Fragment>
            )
          })}
        </div>
      </div>

      <form className="composer" onSubmit={onSend}>
        {actionError ? (
          <p className="form-error" role="alert">
            {actionError}
          </p>
        ) : null}
        <div className="composer-inner">
          <label className="sr-only" htmlFor="composer">
            Message {username}
          </label>
          <textarea
            id="composer"
            ref={composer}
            className="composer-input"
            rows={1}
            placeholder={`Message ${username}`}
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value)
              if (actionError) setActionError('')
            }}
            onKeyDown={onComposerKeyDown}
          />
          <button
            type="submit"
            className="btn btn-solid composer-send"
            disabled={!draft.trim() || !person || sending}
          >
            Send
          </button>
        </div>
        <span className="composer-hint">Enter sends. Shift and Enter starts a new line.</span>
      </form>

      {pendingDelete ? (
        <DeleteDialog
          message={pendingDelete}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      ) : null}
    </div>
  )
}
