from fastapi import WebSocket


class ConnectionManager:
    """Registry of the sockets currently open, keyed by user id."""

    def __init__(self):
        # one user can have multiple tabs/devices open — a list, not a single socket
        self.active: dict[int, list[WebSocket]] = {}

    def connect(self, user_id: int, websocket: WebSocket) -> None:
        self.active.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        sockets = self.active.get(user_id)
        if sockets is None:
            return

        if websocket in sockets:
            sockets.remove(websocket)

        # Drop the key with the last socket, so `user_id in self.active` stays a
        # truthful "is this user online?" rather than slowly filling with [].
        if not sockets:
            del self.active[user_id]

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        # Iterate a copy: a failed send prunes the real list underneath us.
        for websocket in list(self.active.get(user_id, [])):
            try:
                await websocket.send_json(payload)
            except Exception:
                # A socket can die without a clean disconnect — laptop lid closed,
                # tab killed. One dead socket must not cost this user the delivery
                # to their other tabs, and it will never recover, so forget it.
                self.disconnect(user_id, websocket)


# One instance for the life of the process, shared by every connection: a socket
# outlives the request that opened it, so this can't be a per-request dependency.
manager = ConnectionManager()
