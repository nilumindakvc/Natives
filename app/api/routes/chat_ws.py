"""The single per-user chat WebSocket.

One socket per signed-in user carries traffic for all of their conversations.
The receive loop handles two client message types: `send_message` and `read`.
Outgoing event types pushed to clients: `ack`, `new_message`, `message_read`,
`error`.

Auth is via a `token` query param (the Supabase access token), since browsers
can't set Authorization headers on a WebSocket handshake. All blocking DB work
goes through run_in_threadpool so the event loop is never blocked by psycopg2.
"""
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.core import chat_ops
from app.core.database import SessionLocal
from app.core.security import TokenError, decode_access_token
from app.core.ws_manager import manager
from app.schemas.conversation import MessageOut, WSReadReceipt, WSSendMessage

router = APIRouter(tags=["chat"])


def _message_payload(event_type: str, msg_out: MessageOut, client_msg_id: str | None = None) -> dict:
    payload = {"type": event_type, "message": msg_out.model_dump(mode="json")}
    if client_msg_id is not None:
        payload["client_msg_id"] = client_msg_id
    return payload


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        claims = decode_access_token(token)
        user_id = uuid.UUID(str(claims.get("sub")))
    except (TokenError, ValueError, TypeError):
        await websocket.close(code=4401)
        return

    def _check_user() -> bool:
        db = SessionLocal()
        try:
            return chat_ops.user_exists_and_active(db, user_id)
        finally:
            db.close()

    if not await run_in_threadpool(_check_user):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "send_message":
                await _handle_send(websocket, user_id, data)
            elif msg_type == "read":
                await _handle_read(websocket, user_id, data)
            else:
                await websocket.send_json({"type": "error", "detail": "Unknown message type."})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)


async def _handle_send(websocket: WebSocket, user_id: uuid.UUID, data: dict) -> None:
    try:
        payload = WSSendMessage.model_validate(data)
    except ValidationError:
        await websocket.send_json({"type": "error", "detail": "Invalid message payload."})
        return

    def _persist():
        db = SessionLocal()
        try:
            conv = chat_ops.get_conversation_for_user(db, payload.conversation_id, user_id)
            if conv is None:
                return None
            msg = chat_ops.persist_message(db, conv, user_id, payload.body)
            recipient_id = chat_ops.other_party_user_id(db, conv, user_id)
            return MessageOut.model_validate(msg), recipient_id
        finally:
            db.close()

    result = await run_in_threadpool(_persist)
    if result is None:
        await websocket.send_json({"type": "error", "detail": "Conversation not found."})
        return

    msg_out, recipient_id = result
    await websocket.send_json(_message_payload("ack", msg_out, payload.client_msg_id))
    if recipient_id is not None and manager.is_online(recipient_id):
        await manager.send_to_user(recipient_id, _message_payload("new_message", msg_out))


async def _handle_read(websocket: WebSocket, user_id: uuid.UUID, data: dict) -> None:
    try:
        payload = WSReadReceipt.model_validate(data)
    except ValidationError:
        await websocket.send_json({"type": "error", "detail": "Invalid read payload."})
        return

    def _mark():
        db = SessionLocal()
        try:
            conv = chat_ops.get_conversation_for_user(db, payload.conversation_id, user_id)
            if conv is None:
                return None
            return chat_ops.mark_conversation_read(db, payload.conversation_id, user_id)
        finally:
            db.close()

    result = await run_in_threadpool(_mark)
    if result is None:
        await websocket.send_json({"type": "error", "detail": "Conversation not found."})
        return

    marked_ids, sender_id, read_at = result
    if marked_ids and sender_id is not None and manager.is_online(sender_id):
        await manager.send_to_user(
            sender_id,
            {
                "type": "message_read",
                "conversation_id": str(payload.conversation_id),
                "message_ids": [str(i) for i in marked_ids],
                "read_at": read_at.isoformat() if read_at else None,
            },
        )
