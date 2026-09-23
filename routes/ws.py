import json

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from core.errors import DomainError
from core.security import decode_access_token
from core.ws_manager import manager
from db.connect import SessionLocal
from repository.user_repo import UserRepository
from schema.messages import MessageCreate, MessageResponse
from services.mes_service import MessageService

router = APIRouter(tags=["ws"])

# RFC 6455 close code: the handshake was well-formed, the credentials weren't.
WS_POLICY_VIOLATION = 1008


def _authenticate(token: str) -> int | None:
    """Resolve a token to a user id, or None if it doesn't name a live user.

    Same checks as get_current_user, minus the Depends: a browser can't set an
    Authorization header on a WebSocket, so the token arrives as a query param.
    """
    try:
        user_id = int(decode_access_token(token)["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        # Bad signature, expired, malformed, missing or non-numeric sub.
        return None

    # Opened and closed here: nothing holds a session for the life of a socket.
    with SessionLocal() as db:
        user = UserRepository(db).get_by_id(user_id)
        # Valid token for a user that has since been deleted.
        return user.id if user else None


def _send_message(sender_id: int, data: MessageCreate) -> dict:
    """Persist one message through the service layer and serialize the result."""
    with SessionLocal() as db:
        message = MessageService(db).send_message(sender_id, data)
        # Serialize before the session closes: after that the instance is
        # detached and reading .content would raise. mode="json" because
        # send_json() runs json.dumps(), which has no idea what a datetime is.
        return MessageResponse.model_validate(message).model_dump(mode="json")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Authenticate before accept(): a rejected client sees a refused handshake,
    # not an open socket that closes a moment later. _authenticate and
    # _send_message both block on the DB driver, so they run in a worker thread —
    # the same thing FastAPI does for the sync HTTP routes in routes/message.py.
    # Awaiting them on the event loop would stall every other live socket.
    user_id = await run_in_threadpool(_authenticate, token)
    if user_id is None:
        await websocket.close(code=WS_POLICY_VIOLATION)
        return

    await websocket.accept()
    manager.connect(user_id, websocket)

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except (json.JSONDecodeError, KeyError):
                # KeyError: a binary frame has no "text" to decode. Neither is
                # worth dropping the connection over — tell them and read on.
                await websocket.send_json({"type": "error", "error": "Expected a JSON text frame."})
                continue

            try:
                payload = MessageCreate.model_validate(data)
            except ValidationError:
                # Raw frames skip FastAPI's request validation, so this line is
                # the only thing between the client and the service layer.
                await websocket.send_json(
                    {"type": "error", "error": 'Expected {"receiver_id": <int>, "content": <str>}.'}
                )
                continue

            try:
                message = await run_in_threadpool(_send_message, user_id, payload)
            except DomainError as exc:
                # main.py maps these to status codes; there is no HTTP response to
                # hang one on here, so the rejection rides back down the socket
                # and the connection stays open.
                await websocket.send_json({"type": "error", "error": exc.message})
                continue

            envelope = {"type": "message", "message": message}
            # The receiver, if they're online at all, and every socket the sender
            # has open — including this one, which is how the client learns the
            # send landed and how their other tabs find out about it.
            await manager.send_to_user(message["receiver_id"], envelope)
            await manager.send_to_user(user_id, envelope)
    except WebSocketDisconnect:
        pass
    finally:
        # finally, not just the disconnect branch: an unexpected error must not
        # leave a dead socket in the registry for every later send to trip on.
        manager.disconnect(user_id, websocket)
