"""In-memory registry of live WebSocket connections, keyed by user id.

Single-process only: correct while the backend runs one worker. See the
scaling note in the phase-2 plan for the Redis pub/sub path to take if this
ever needs to fan out across multiple workers/instances.
"""
import uuid
from collections import defaultdict

from anyio.from_thread import run as run_from_thread
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    def is_online(self, user_id: uuid.UUID) -> bool:
        return bool(self._connections.get(user_id))

    async def send_to_user(self, user_id: uuid.UUID, payload: dict) -> None:
        """Best-effort push to every live socket a user has open. A dead
        socket is skipped; its own receive loop handles cleanup on disconnect."""
        for websocket in list(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:
                pass


manager = ConnectionManager()


def push_sync(user_id: uuid.UUID, payload: dict) -> None:
    """Push a payload to a user's live socket(s) from a *synchronous* context,
    such as a regular (non-websocket) REST route handler — these run in
    FastAPI's threadpool, not on the event loop that owns the sockets.
    `anyio.from_thread.run` bridges back onto that loop; if there isn't one
    to bridge to (e.g. a standalone script), this is a silent no-op rather
    than failing the caller's request.
    """
    try:
        run_from_thread(manager.send_to_user, user_id, payload)
    except RuntimeError:
        pass
