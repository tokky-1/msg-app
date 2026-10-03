# MSG

A messenger for two people at a time. No groups, no feed — you need one
username to start, and messages land the moment they are sent.

FastAPI + Postgres on the back, React + Vite on the front, talking over REST
for history and a WebSocket for live delivery.

| Chats | Rate limit refusing the 11th message |
| --- | --- |
| ![The chat list](docs/screenshots/chats.jpg) | ![Rate limit exceeded](docs/screenshots/rate-limit.jpg) |

## Run it

```bash
cp backend/.env.example backend/.env   # then edit SECRET_KEY, DB_USER, DB_PASSWORD
docker compose --env-file ./backend/.env up --build
```

The `--env-file` is not optional. Compose interpolates `${DB_USER}` and friends
from its own environment, which `env_file:` inside a service does not feed, so
without it the `db` service refuses to start and says which variable is missing.

That brings up three services in order: `db` becomes healthy, `migrate` runs
`alembic upgrade head` and exits 0, then `app` starts. The API is on
`http://localhost:8000`, docs at `/docs`.

The frontend is not containerised — run it alongside:

```bash
cd frontend && npm install && npm run dev
```

### Development without Docker

```bash
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn main:app --reload
uv run pytest        # 23 tests
```

## Architecture

```
  browser
     |  REST: auth, history, edit, delete        WebSocket: send + live delivery
     v
  +--------------------------------------------------------------+
  |  FastAPI (app)                                                |
  |                                                               |
  |  routes/      auth, message, ws, health                       |
  |     |         thin: dependencies, status codes, serialisation |
  |     v                                                         |
  |  services/    the business rules live here                    |
  |     |         rate limit, edit window, who may touch what     |
  |     v                                                         |
  |  repository/  every query, and nothing else                   |
  |     |                                                         |
  |     v                                                         |
  |  models/      SQLAlchemy tables                               |
  +--------------------------------------------------------------+
     |
     v
  Postgres  (migrations applied by the one-shot `migrate` service)
```

Domain errors are raised by the service layer as subclasses of `DomainError`
and mapped to status codes once, in `main.py` — so a rule like "only the sender
may delete" is written in one place and answers correctly whether it was
reached over REST or over the socket.

**Sending goes over the WebSocket, not `POST /messages`.** The server stores the
message and echoes it to the receiver *and* back to the sender, so the client
only renders a bubble once it is really saved. The REST route still exists and
is what the tests and scripts use.

**The rate limit** is 10 messages per minute per sender, counted against an
append-only `message_send_events` log rather than the `messages` table — the
messages themselves can be deleted, and counting those let anyone delete their
way to a fresh allowance. The window is computed by the database so the app
container's clock cannot skew it, and the sender's row is locked for the length
of the check so two simultaneous sends cannot both pass.

## Known limitations

- **The WebSocket manager is in-memory and single-instance.** `core/ws_manager.py`
  keeps a dict of live sockets in the process, so a second replica would only
  reach the clients attached to itself. Scaling out needs Redis pub/sub (or
  similar) between instances.
- **`POST /messages` does not broadcast.** Only the WebSocket route tells the
  connection manager about a new message, so a message sent over REST reaches
  the recipient on their next load rather than immediately.
- **`UserService.register` is coupled to psycopg2 constraint names.** It reads
  `e.orig.diag.constraint_name` and compares against `users_username_key` /
  `users_email_key`, which are Postgres' default names for those unique
  constraints. Renaming a constraint, or moving to another driver or database,
  turns a clean 409 into a generic one.
- **The token travels in the WebSocket query string.** A browser cannot set an
  `Authorization` header on a WebSocket, so `/ws?token=…` is the usual
  workaround — but query strings are the part of a URL most likely to end up in
  access logs and proxy logs. Behind TLS it is not on the wire in clear, but it
  is still written down somewhere.
- **There is no blanket `except` in the WebSocket loop, deliberately.** It
  catches `WebSocketDisconnect`, bad JSON and `DomainError`, and lets anything
  else propagate so a real bug is loud instead of being swallowed into a socket
  that silently stops working. The `finally` still deregisters the connection.
- **The published database port is for development only.** `docker-compose.yaml`
  maps `5432:5432` so you can attach a client from the host. Do not publish it
  anywhere real — and note that if you already run Postgres on the host, both
  bind 5432 and which one a host client reaches is not defined.
- **Authentication is not rate limited.** Login and registration accept
  unlimited attempts; only message sending is capped.

## Layout

```
.
├── Dockerfile              one image, used by both `migrate` and `app`
├── docker-compose.yaml     db → migrate → app
├── backend/                FastAPI service (see backend/README.md)
└── frontend/               React client (see frontend/README.md)
```
