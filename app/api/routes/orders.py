import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dispatch import compute_and_broadcast_rounds
from app.core.security import get_current_user
from app.db.models import Order, OrderSegment, RepairIssue, ServiceItem
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderCreateRequest(BaseModel):
    repair_issue_ids: list[int] = []
    service_item_ids: list[int] = []


class OrderResponseModel(BaseModel):
    id: int
    customer_id: str
    repair_issue_ids: list[int]
    service_item_ids: list[int]
    total_amount: int
    status: str
    created_at: str

    class Config:
        from_attributes = True


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrderResponseModel)
async def create_order(
    request: OrderCreateRequest,
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponseModel:
    customer_id = claims.get("sub")
    if not customer_id:
        logger.error("Missing sub claim in token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repair_issue_ids = request.repair_issue_ids or []
    service_item_ids = request.service_item_ids or []

    if not repair_issue_ids and not service_item_ids:
        logger.info(f"Order creation rejected: both lists empty for customer {customer_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="select at least one item",
        )

    invalid_ids = []

    if repair_issue_ids:
        for issue_id in repair_issue_ids:
            issue = db.query(RepairIssue).filter(RepairIssue.id == issue_id).first()
            if not issue or not issue.active:
                invalid_ids.append(issue_id)

    if service_item_ids:
        for item_id in service_item_ids:
            item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
            if not item or not item.active:
                invalid_ids.append(item_id)

    if invalid_ids:
        logger.info(f"Order creation rejected: invalid IDs {invalid_ids} for customer {customer_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IDs: {invalid_ids}",
        )

    repair_issues = db.query(RepairIssue).filter(RepairIssue.id.in_(repair_issue_ids)).all() if repair_issue_ids else []
    service_items = db.query(ServiceItem).filter(ServiceItem.id.in_(service_item_ids)).all() if service_item_ids else []

    service_total = sum(item.price for item in service_items)
    repair_total = sum(issue.price for issue in repair_issues)
    total_amount = repair_total + service_total

    order = Order(
        customer_id=customer_id,
        repair_issue_ids=repair_issue_ids,
        service_item_ids=service_item_ids,
        total_amount=total_amount,
        status="pending_assignment",
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    specialization_groups = {}
    for issue in repair_issues:
        if issue.specialization not in specialization_groups:
            specialization_groups[issue.specialization] = []
        specialization_groups[issue.specialization].append(issue)

    for specialization, issues in specialization_groups.items():
        amount = sum(issue.price for issue in issues)
        repair_issue_id = issues[0].id if issues else None
        segment = OrderSegment(
            order_id=order.id,
            specialization=specialization,
            repair_issue_id=repair_issue_id,
            amount=amount,
            status="open"
        )
        db.add(segment)

    for item_id in service_item_ids:
        service_item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
        if service_item:
            segment = OrderSegment(
                order_id=order.id,
                specialization=service_item.specialization,
                service_item_id=item_id,
                amount=service_item.price,
                status="open"
            )
            db.add(segment)

    db.commit()

    logger.info(f"Order {order.id} created for customer {customer_id} with total ₹{total_amount}")

    compute_and_broadcast_rounds(order.id)

    return OrderResponseModel(
        id=order.id,
        customer_id=order.customer_id,
        repair_issue_ids=order.repair_issue_ids,
        service_item_ids=order.service_item_ids,
        total_amount=order.total_amount,
        status=order.status,
        created_at=order.created_at.isoformat() if hasattr(order.created_at, 'isoformat') else str(order.created_at),
    )


@router.get("/me", response_model=list[OrderResponseModel])
async def list_orders(
    claims: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderResponseModel]:
    customer_id = claims.get("sub")
    if not customer_id:
        logger.error("Missing sub claim in token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    logger.info(f"Retrieved {len(orders)} orders for customer {customer_id}")

    return [
        OrderResponseModel(
            id=order.id,
            customer_id=order.customer_id,
            repair_issue_ids=order.repair_issue_ids,
            service_item_ids=order.service_item_ids,
            total_amount=order.total_amount,
            status=order.status,
            created_at=order.created_at.isoformat() if hasattr(order.created_at, 'isoformat') else str(order.created_at),
        )
        for order in orders
    ]
