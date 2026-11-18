"""Synchronous DB operations for chat, shared by the REST route and the
WebSocket handler (the latter calls these via ``run_in_threadpool``). Kept
separate so both entry points use exactly one implementation.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.seller import SellerDetail
from app.models.user import User


def resolve_seller_id_for_user(db: Session, user_id: uuid.UUID) -> Optional[uuid.UUID]:
    """The caller's own seller_details.id, if they are a seller; else None."""
    return db.scalar(select(SellerDetail.id).where(SellerDetail.user_id == user_id))


def get_conversation_for_user(
    db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Conversation]:
    """Return the conversation only if this user is a participant (its
    customer, or the user behind its seller_details row)."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return None
    if conv.customer_id == user_id:
        return conv
    own_seller_id = resolve_seller_id_for_user(db, user_id)
    if own_seller_id is not None and conv.seller_id == own_seller_id:
        return conv
    return None


def other_party_user_id(db: Session, conv: Conversation, sender_user_id: uuid.UUID) -> uuid.UUID:
    """The user id of whichever participant is NOT the sender."""
    if conv.customer_id == sender_user_id:
        seller_user_id = db.scalar(
            select(SellerDetail.user_id).where(SellerDetail.id == conv.seller_id)
        )
        return seller_user_id
    return conv.customer_id


def persist_message(
    db: Session, conv: Conversation, sender_id: uuid.UUID, body: str
) -> Message:
    msg = Message(conversation_id=conv.id, sender_id=sender_id, body=body)
    db.add(msg)
    conv.last_message_at = func.now()
    conv.last_message_preview = body[:200]
    db.commit()
    db.refresh(msg)
    return msg


def mark_conversation_read(
    db: Session, conv_id: uuid.UUID, reader_id: uuid.UUID
) -> tuple[list[uuid.UUID], Optional[uuid.UUID], Optional[datetime]]:
    """Mark every unread message NOT sent by the reader as read.

    Returns (ids just marked, the sender those messages belong to, read_at) so
    the caller can push a read-receipt to that sender over the socket.
    """
    unread = db.scalars(
        select(Message).where(
            and_(
                Message.conversation_id == conv_id,
                Message.sender_id != reader_id,
                Message.read_at.is_(None),
            )
        )
    ).all()
    if not unread:
        return [], None, None
    now = datetime.now(timezone.utc)
    ids: list[uuid.UUID] = []
    sender_id: Optional[uuid.UUID] = None
    for m in unread:
        m.read_at = now
        ids.append(m.id)
        sender_id = m.sender_id
    db.commit()
    return ids, sender_id, now


def unread_count(db: Session, conv_id: uuid.UUID, reader_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id == conv_id,
            Message.sender_id != reader_id,
            Message.read_at.is_(None),
        )
    ) or 0


def user_exists_and_active(db: Session, user_id: uuid.UUID) -> bool:
    user = db.get(User, user_id)
    return user is not None and user.is_active
