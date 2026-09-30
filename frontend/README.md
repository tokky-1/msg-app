# MSG — frontend

The web client for MSG, a 1:1 messenger. Wired to the FastAPI backend in
`../backend`: real auth, real message history, and live delivery over the
WebSocket.

```bash
npm install
npm run dev
```

It talks to `VITE_API_URL`, which falls back to `http://localhost:8000` when
unset (see `.env.example`). The backend must be running, and its `CORS_ORIGINS`
must include the dev server's origin.

## The flow

| Route             | Screen                                                        |
| ----------------- | ------------------------------------------------------------- |
| `/`               | Splash — the opening animation, then it hands over            |
| `/welcome`        | Signed-out landing                                            |
| `/signup`         | Create an account                                             |
| `/login`          | Log in                                                        |
| `/chats`          | Inbox: every conversation, newest first                       |
| `/chats/:username`| One conversation: send, edit, delete                          |
| `/new`            | Open a conversation by username                               |
| `/me`             | Account                                                       |

There are no tabs. The header carries the navigation: the profile icon opens
the account, the red plus starts a chat, and a back arrow returns from either.
Log out lives at the end of the account page. Login and sign up are a single
centred form with no surrounding chrome; they reach each other through the link
under the submit button.

Routing is a hash router in `src/lib/routing.js` and `src/lib/router.jsx` — no
routing dependency. Signing in accepts anything non-empty and stores the
account in `localStorage`. Search on the inbox filters locally over usernames
and the latest message; the backend has no search route.

## Design rules

- **Two voices.** Sky `#7EB2DD` is you, blush `#FCB0B3` is them — the same split
  the API stores as `sender_id` / `receiver_id`. Each bubble also has one corner
  cut toward whoever spoke, so the shape says it too. Nothing else uses these
  two colours.
- **Red is rare, and at most one per screen.** `#F93943` marks connection state (the
  socket dot, an unread count), the single action that starts or ends something
  (the new-chat plus, log out), and what cannot be undone (an error rule, the
  confirm-delete fill). It is never the only thing carrying a meaning — the dot
  always sits beside the word "Online". It is only ever set as text at 19.2px/700 or
  larger, which is where `#F93943` on cream clears the 3:1 contrast floor.
- **Navy is chrome, cream is paper.** `#445E93` for the rail and the signed-out
  screens, `#FCECC9` for anything you read on.
- **Radius encodes kind.** Panels are flat, controls are 10px, bubbles are 18px
  with one corner at 4px.
- **Radius encodes kind** (see below), and the app sits in one 46rem column on
  a deeper cream backdrop, so a wide window frames it rather than stretching it.
- Type is Bricolage Grotesque for display and Schibsted Grotesk for text.

## Motion

Three curves, defined in `src/styles/tokens.css`. The built-in CSS easings are
too weak to read as intentional, and `ease-in` is never used — it delays the
first frame, the one the user watches hardest.

| Token            | Curve                              | Used for                          |
| ---------------- | ---------------------------------- | --------------------------------- |
| `--ease-out`     | `cubic-bezier(0.23, 1, 0.32, 1)`   | Entrances, exits, press feedback  |
| `--ease-in-out`  | `cubic-bezier(0.77, 0, 0.175, 1)`  | Looping motion already on screen  |
| `--ease-soft`    | `cubic-bezier(0.4, 0, 0.2, 1)`     | Hover and colour changes          |

Everything interactive is under 300ms. Pressable surfaces scale down on
`:active` rather than shifting position. Hover states are gated behind
`@media (hover: hover) and (pointer: fine)`, since a tap on a touch screen
fires `:hover` and leaves it stuck. Reduced motion zeroes durations *and*
delays — a staggered row with a live delay and a dead duration is worse than
the animation it replaced.

The splash is the only thing that moves on its own. Everything else answers a
click.

## How it talks to the backend

`src/api.js` wraps every route; `src/lib/session.jsx` is the only thing that
calls it and holds all client state.

- **Auth.** `POST /auth/login` returns a token, kept in `localStorage` and sent
  as a bearer header. On boot the stored token is checked against `/auth/me`; a
  401 anywhere else signs you out, but an unreachable server does not throw a
  good token away.
- **Sending** goes over the WebSocket, not `POST /messages`. The server saves
  the message and echoes it back to the sender as well as the receiver, so a
  bubble only appears once it is actually stored — nothing is optimistic.
- **Receiving** is the same socket. It reconnects with backoff (1s, 2s, 4s… to
  15s), and the "Online" indicator reports its real state.
- **Editing and deleting** use `PATCH` / `DELETE /messages/{id}`.
- **Opening a chat** needs the partner's id, which the inbox implies for
  existing conversations and `GET /auth/users/{username}` supplies for new ones.

### Known gaps

- `POST /messages` persists but does not broadcast — only the WebSocket route
  calls the connection manager. Two clients on sockets get live delivery; a
  message sent over REST reaches the recipient only on their next refresh.
- The API has no read state, so unread counts are a local high-water mark per
  conversation (`msg.seen` in `localStorage`), not a server fact.
- There is no endpoint listing users, so a new chat has to be opened by typing
  an exact username.
