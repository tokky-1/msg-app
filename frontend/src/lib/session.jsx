import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../api'
import { SessionContext } from './sessionContext'

/* The whole client-side data layer: the signed-in account, every message we
   have loaded, and the live socket. Talks to src/api.js and nothing else. */

const TOKEN_KEY = 'msg.token'
const SEEN_KEY = 'msg.seen'

function readStored(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key)
    return raw === null ? fallback : JSON.parse(raw)
  } catch {
    // Private mode, blocked storage — the app still works, you just sign in again.
    return fallback
  }
}

function writeStored(key, value) {
  try {
    if (value === null) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* no-op */
  }
}

const byTime = (a, b) => new Date(a.timestamp) - new Date(b.timestamp)

export function SessionProvider({ children }) {
  const [token, setTokenState] = useState(() => readStored(TOKEN_KEY, null))
  const [account, setAccount] = useState(null)
  // 'loading' only while a stored token is being checked against /auth/me.
  const [status, setStatus] = useState(() => (readStored(TOKEN_KEY, null) ? 'loading' : 'out'))

  const [messages, setMessages] = useState([])
  const [inbox, setInbox] = useState([])
  const [inboxState, setInboxState] = useState({ status: 'idle', error: '' })
  // username -> { id, username, email }. Sending needs the id, and the inbox
  // only gives usernames, so every partner we learn about lands here.
  const [partners, setPartners] = useState({})
  const [threads, setThreads] = useState({})
  const [seen, setSeen] = useState(() => readStored(SEEN_KEY, {}))
  const [online, setOnline] = useState(false)

  const socketRef = useRef(null)
  const retryRef = useRef(0)
  const [retryTick, setRetryTick] = useState(0)

  api.setToken(token)

  const setToken = useCallback((next) => {
    api.setToken(next)
    writeStored(TOKEN_KEY, next)
    setTokenState(next)
  }, [])

  const signOut = useCallback(() => {
    setToken(null)
    setAccount(null)
    setStatus('out')
    setMessages([])
    setInbox([])
    setPartners({})
    setThreads({})
    setInboxState({ status: 'idle', error: '' })
  }, [setToken])

  /* A 401 on anything other than the login call means the token died under us. */
  const handle = useCallback(
    (error) => {
      if (error instanceof api.ApiError && error.status === 401) signOut()
      return error
    },
    [signOut],
  )

  // Resume a stored session, or discard the token if the server rejects it.
  useEffect(() => {
    if (!token) return undefined
    let cancelled = false
    api
      .me()
      .then((user) => {
        if (cancelled) return
        setAccount(user)
        setStatus('in')
      })
      .catch((error) => {
        if (cancelled) return
        // A server that is merely unreachable should not throw away a good
        // token, so hold the session and let the screens report the outage.
        if (error instanceof api.ApiError && error.status === 401) signOut()
        else setStatus('in')
      })
    return () => {
      cancelled = true
    }
  }, [token, signOut])

  const remember = useCallback((people) => {
    setPartners((current) => {
      const next = { ...current }
      for (const person of people) next[person.username] = person
      return next
    })
  }, [])

  const mergeMessages = useCallback((incoming) => {
    setMessages((current) => {
      const byId = new Map(current.map((message) => [message.id, message]))
      for (const message of incoming) byId.set(message.id, message)
      return [...byId.values()].sort(byTime)
    })
  }, [])

  const refreshInbox = useCallback(async () => {
    setInboxState((s) => ({ status: s.status === 'ready' ? 'ready' : 'loading', error: '' }))
    try {
      const items = await api.inbox()
      setInbox(items)
      mergeMessages(items.map((item) => item.message))
      setInboxState({ status: 'ready', error: '' })
    } catch (error) {
      handle(error)
      setInboxState({ status: 'error', error: error.message })
    }
  }, [handle, mergeMessages])

  useEffect(() => {
    if (status === 'in') refreshInbox()
  }, [status, refreshInbox])

  /* The inbox pairs a username with a message, and that message carries both
     ids — so every conversation we already have teaches us its partner's id
     without another request. */
  useEffect(() => {
    if (!account || inbox.length === 0) return
    remember(
      inbox.map((item) => {
        const { sender_id: from, receiver_id: to } = item.message
        return { id: from === account.id ? to : from, username: item.partner_username }
      }),
    )
  }, [inbox, account, remember])

  // ---- live socket -------------------------------------------------------

  useEffect(() => {
    if (!token || status !== 'in') return undefined

    let closedByUs = false
    const socket = api.openSocket(token)
    socketRef.current = socket

    socket.onopen = () => {
      retryRef.current = 0
      setOnline(true)
    }

    socket.onmessage = (event) => {
      let frame
      try {
        frame = JSON.parse(event.data)
      } catch {
        return
      }
      if (frame.type === 'message') mergeMessages([frame.message])
    }

    socket.onclose = () => {
      setOnline(false)
      if (closedByUs) return
      // Back off so a server that is down is not hammered: 1s, 2s, 4s… to 15s.
      const wait = Math.min(1000 * 2 ** retryRef.current, 15000)
      retryRef.current += 1
      window.setTimeout(() => setRetryTick((n) => n + 1), wait)
    }

    socket.onerror = () => socket.close()

    return () => {
      closedByUs = true
      socketRef.current = null
      setOnline(false)
      socket.close()
    }
  }, [token, status, retryTick, mergeMessages])

  /* A frame only carries the message, so the inbox previews and ordering have
     to be re-read. Only when a new id appears — an edit changes no ordering. */
  const messageCount = messages.length
  useEffect(() => {
    if (status !== 'in' || messageCount === 0) return
    refreshInbox()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messageCount])

  // ---- actions -----------------------------------------------------------

  const logIn = useCallback(
    async ({ username, password }) => {
      const { access_token: accessToken } = await api.login({ username, password })
      api.setToken(accessToken)
      const user = await api.me()
      setToken(accessToken)
      setAccount(user)
      setStatus('in')
    },
    [setToken],
  )

  const registerAccount = useCallback(
    async ({ username, email, password }) => {
      await api.register({ username, email, password })
      await logIn({ username, password })
    },
    [logIn],
  )

  const resolvePartner = useCallback(
    async (username) => {
      const known = partners[username]
      if (known) return known
      const person = await api.getUser(username)
      remember([person])
      return person
    },
    [partners, remember],
  )

  const loadConversation = useCallback(
    async (username) => {
      setThreads((current) => ({ ...current, [username]: { status: 'loading', error: '' } }))
      try {
        const person = await resolvePartner(username)
        const history = await api.conversation(username)
        mergeMessages(history)
        setThreads((current) => ({ ...current, [username]: { status: 'ready', error: '' } }))
        return person
      } catch (error) {
        handle(error)
        setThreads((current) => ({
          ...current,
          [username]: { status: 'error', error: error.message },
        }))
        return null
      }
    },
    [resolvePartner, mergeMessages, handle],
  )

  const sendMessage = useCallback(
    async (receiverId, content) => {
      const socket = socketRef.current
      if (socket && socket.readyState === WebSocket.OPEN) {
        // The server echoes the saved message back to the sender too, so the
        // bubble appears once it is actually stored — never optimistically.
        socket.send(JSON.stringify({ receiver_id: receiverId, content }))
        return
      }
      const message = await api.sendMessage(receiverId, content).catch((error) => {
        throw handle(error)
      })
      mergeMessages([message])
    },
    [handle, mergeMessages],
  )

  const editMessage = useCallback(
    async (id, content) => {
      const updated = await api.editMessage(id, content).catch((error) => {
        throw handle(error)
      })
      mergeMessages([updated])
    },
    [handle, mergeMessages],
  )

  const deleteMessage = useCallback(
    async (id) => {
      await api.deleteMessage(id).catch((error) => {
        throw handle(error)
      })
      setMessages((current) => current.filter((message) => message.id !== id))
      refreshInbox()
    },
    [handle, refreshInbox],
  )

  /* The API has no read receipts, so "unread" is a local high-water mark:
     anything they sent after you last opened the thread. */
  const markRead = useCallback((username) => {
    setSeen((current) => {
      const next = { ...current, [username]: new Date().toISOString() }
      writeStored(SEEN_KEY, next)
      return next
    })
  }, [])

  const messagesWith = useCallback(
    (username) => {
      const person = partners[username]
      if (!person) return []
      return messages.filter(
        (message) => message.sender_id === person.id || message.receiver_id === person.id,
      )
    },
    [messages, partners],
  )

  const inboxItems = useMemo(() => {
    if (!account) return []
    return inbox.map((item) => {
      const mark = seen[item.partner_username]
      const theirs = item.message.sender_id !== account.id
      const unread = theirs && (!mark || new Date(item.message.timestamp) > new Date(mark)) ? 1 : 0
      return { ...item, unread }
    })
  }, [inbox, seen, account])

  const value = useMemo(
    () => ({
      status,
      account,
      online,
      inbox: inboxItems,
      inboxState,
      unreadTotal: inboxItems.reduce((sum, item) => sum + item.unread, 0),
      partners,
      threads,
      logIn,
      register: registerAccount,
      signOut,
      refreshInbox,
      loadConversation,
      resolvePartner,
      messagesWith,
      sendMessage,
      editMessage,
      deleteMessage,
      markRead,
    }),
    [
      status,
      account,
      online,
      inboxItems,
      inboxState,
      partners,
      threads,
      logIn,
      registerAccount,
      signOut,
      refreshInbox,
      loadConversation,
      resolvePartner,
      messagesWith,
      sendMessage,
      editMessage,
      deleteMessage,
      markRead,
    ],
  )

  return <SessionContext value={value}>{children}</SessionContext>
}
