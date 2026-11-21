"""Order requests: customer creates, seller quotes, customer confirms.

Forward-only lifecycle (pending -> quoted -> confirmed); no cancellation yet.
Messaging is order-scoped: creating an order also creates its conversation.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbDep, PaginationDep, require_seller
from app.core import chat_ops
from app.core.ws_manager import manager, push_sync
from app.models.conversation import Conversation
from app.models.enums import ApprovalStatus, OrderStatus
from app.models.listing import Listing
from app.models.order import Order
from app.models.seller import SellerDetail
from app.models.user import User
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderOut, OrderQuote

router = APIRouter(prefix="/me/orders", tags=["orders"])

SellerUser = Depends(require_seller)


def _to_out(db: Session, order: Order) -> OrderOut:
    out = OrderOut.model_validate(order)
    conv_id = db.scalar(select(Conversation.id).where(Conversation.order_id == order.id))
    out.conversation_id = conv_id
    return out


def _order_for_user(db: Session, order_id: uuid.UUID, user: User) -> Order:
    """Return the order only if the caller is its customer or its seller-user."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if order.customer_id == user.id:
        return order
    own_seller_id = chat_ops.resolve_seller_id_for_user(db, user.id)
    if own_seller_id is not None and order.seller_id == own_seller_id:
        return order
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, user: CurrentUser, db: DbDep) -> OrderOut:
    listing = db.get(Listing, payload.listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    seller = db.get(SellerDetail, listing.seller_id)
    if seller is None or seller.approval_status != ApprovalStatus.approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not available.")
    if seller.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot order from your own store.",
        )

    order = Order(
        customer_id=user.id,
        seller_id=seller.id,
        listing_id=listing.id,
        listing_title=listing.title,
        quantity=payload.quantity,
        requested_date=payload.requested_date,
        delivery_address=payload.delivery_address,
        customization=payload.customization,
    )
    db.add(order)
    db.flush()  # assign order.id before creating the conversation

    conversation = Conversation(
        order_id=order.id,
        customer_id=user.id,
        seller_id=seller.id,
        listing_id=listing.id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(order)
    out = _to_out(db, order)
    # Live-notify the seller over the shared per-user socket (same one chat
    # uses) so their Orders tab/badge updates without a manual refresh.
    if manager.is_online(seller.user_id):
        push_sync(seller.user_id, {"type": "order_created", "order": out.model_dump(mode="json")})
    return out


@router.get("", response_model=Page[OrderOut])
def list_orders(user: CurrentUser, db: DbDep, page: PaginationDep) -> Page[OrderOut]:
    own_seller_id = chat_ops.resolve_seller_id_for_user(db, user.id)
    condition = Order.customer_id == user.id
    if own_seller_id is not None:
        condition = or_(condition, Order.seller_id == own_seller_id)

    stmt = select(Order).where(condition)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Order.created_at.desc()).limit(page.limit).offset(page.offset)
    ).all()
    items = [_to_out(db, o) for o in rows]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: uuid.UUID, user: CurrentUser, db: DbDep) -> OrderOut:
    order = _order_for_user(db, order_id, user)
    return _to_out(db, order)


@router.post("/{order_id}/quote", response_model=OrderOut)
def quote_order(order_id: uuid.UUID, payload: OrderQuote, db: DbDep, user: User = SellerUser) -> OrderOut:
    order = _order_for_user(db, order_id, user)
    own_seller_id = chat_ops.resolve_seller_id_for_user(db, user.id)
    if own_seller_id is None or order.seller_id != own_seller_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order.")
    if order.status != OrderStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order is {order.status.value}; only pending orders can be quoted.",
        )

    order.final_price = payload.final_price
    order.currency = payload.currency
    order.final_date = payload.final_date
    order.delivery_method = payload.delivery_method
    order.seller_notes = payload.seller_notes
    order.quoted_at = datetime.now(timezone.utc)
    order.status = OrderStatus.quoted
    db.commit()
    db.refresh(order)
    out = _to_out(db, order)
    # Live-notify the customer so their order updates without a manual refresh.
    if manager.is_online(order.customer_id):
        push_sync(order.customer_id, {"type": "order_quoted", "order": out.model_dump(mode="json")})
    return out


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: uuid.UUID, user: CurrentUser, db: DbDep) -> OrderOut:
    order = _order_for_user(db, order_id, user)
    if order.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the customer can confirm this order.",
        )
    if order.status != OrderStatus.quoted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order is {order.status.value}; only quoted orders can be confirmed.",
        )

    order.confirmed_at = datetime.now(timezone.utc)
    order.status = OrderStatus.confirmed
    db.commit()
    db.refresh(order)
    out = _to_out(db, order)
    # Live-notify the seller so their order updates without a manual refresh.
    seller_user_id = db.scalar(select(SellerDetail.user_id).where(SellerDetail.id == order.seller_id))
    if seller_user_id is not None and manager.is_online(seller_user_id):
        push_sync(seller_user_id, {"type": "order_confirmed", "order": out.model_dump(mode="json")})
    return out
