"""Customer<->seller chat: conversation listing, creation and history.

Message *sending* is not here — it happens over the WebSocket in chat_ws.py.
These endpoints cover discovering conversations and paging through history.
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbDep, PaginationDep
from app.core import chat_ops
from app.core.ws_manager import manager
from app.models.conversation import Conversation
from app.models.enums import ApprovalStatus
from app.models.message import Message
from app.models.seller import SellerDetail
from app.schemas.common import Page
from app.schemas.conversation import ConversationCreate, ConversationOut, MessageOut

router = APIRouter(prefix="/me/conversations", tags=["conversations"])


def _to_out(db: Session, conv: Conversation, user_id: uuid.UUID) -> ConversationOut:
    out = ConversationOut.model_validate(conv)
    out.unread_count = chat_ops.unread_count(db, conv.id, user_id)
    return out


@router.get("", response_model=Page[ConversationOut])
def list_conversations(user: CurrentUser, db: DbDep, page: PaginationDep) -> Page[ConversationOut]:
    own_seller_id = chat_ops.resolve_seller_id_for_user(db, user.id)
    condition = Conversation.customer_id == user.id
    if own_seller_id is not None:
        condition = or_(condition, Conversation.seller_id == own_seller_id)

    stmt = select(Conversation).where(condition)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    items = [_to_out(db, c, user.id) for c in rows]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def start_conversation(payload: ConversationCreate, user: CurrentUser, db: DbDep) -> ConversationOut:
    seller = db.get(SellerDetail, payload.seller_id)
    if seller is None or seller.approval_status != ApprovalStatus.approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found.")
    if seller.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot start a conversation with your own store.",
        )

    existing = db.scalar(
        select(Conversation).where(
            Conversation.customer_id == user.id,
            Conversation.seller_id == payload.seller_id,
        )
    )
    if existing is not None:
        return _to_out(db, existing, user.id)

    conv = Conversation(
        customer_id=user.id,
        seller_id=payload.seller_id,
        listing_id=payload.listing_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _to_out(db, conv, user.id)


@router.get("/{conversation_id}/messages", response_model=Page[MessageOut])
async def list_messages(
    conversation_id: uuid.UUID, user: CurrentUser, db: DbDep, page: PaginationDep
) -> Page[MessageOut]:
    def _load():
        conv = chat_ops.get_conversation_for_user(db, conversation_id, user.id)
        if conv is None:
            return None
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(
            stmt.order_by(Message.created_at.desc()).limit(page.limit).offset(page.offset)
        ).all()
        marked_ids, sender_id, read_at = chat_ops.mark_conversation_read(db, conversation_id, user.id)
        return list(rows), total, marked_ids, sender_id, read_at

    result = await run_in_threadpool(_load)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    rows, total, marked_ids, sender_id, read_at = result
    if marked_ids and sender_id is not None and manager.is_online(sender_id):
        await manager.send_to_user(
            sender_id,
            {
                "type": "message_read",
                "conversation_id": str(conversation_id),
                "message_ids": [str(i) for i in marked_ids],
                "read_at": read_at.isoformat() if read_at else None,
            },
        )
    return Page(items=list(rows), total=total, limit=page.limit, offset=page.offset)
