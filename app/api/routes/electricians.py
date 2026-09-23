import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, update
from sqlalchemy.orm import Session

from app.core.security import get_current_electrician
from app.db.models import DispatchRound, DispatchRoundCandidate, ElectricianSkill, Order, OrderSegment
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["electricians"])


class OrderSegmentResponse(BaseModel):
    id: int
    order_id: int
    specialization: str
    amount: int
    service_item_id: int | None
    status: str
    electrician_id: str | None
    created_at: str

    class Config:
        from_attributes = True


class RoundAcceptanceResponse(BaseModel):
    round_id: int
    segments: list[OrderSegmentResponse]
    total_amount: int

    class Config:
        from_attributes = True


class SkillsRequest(BaseModel):
    specializations: list[str]


class SkillsResponse(BaseModel):
    electrician_id: str
    specializations: list[str]


@router.post("/me/skills", response_model=SkillsResponse)
async def set_skills(
    request: SkillsRequest,
    claims: dict[str, Any] = Depends(get_current_electrician),
    db: Session = Depends(get_db),
) -> SkillsResponse:
    electrician_id = claims.get("sub")
    if not electrician_id:
        logger.error("Missing sub claim in token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    db.query(ElectricianSkill).filter(ElectricianSkill.electrician_id == electrician_id).delete()
    db.commit()

    for specialization in request.specializations:
        skill = ElectricianSkill(
            electrician_id=electrician_id,
            specialization=specialization
        )
        db.add(skill)

    db.commit()

    logger.info(f"Updated skills for electrician {electrician_id}: {request.specializations}")

    return SkillsResponse(
        electrician_id=electrician_id,
        specializations=request.specializations
    )


@router.get("/me/skills", response_model=SkillsResponse)
async def get_skills(
    claims: dict[str, Any] = Depends(get_current_electrician),
    db: Session = Depends(get_db),
) -> SkillsResponse:
    electrician_id = claims.get("sub")
    if not electrician_id:
        logger.error("Missing sub claim in token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    skills = db.query(ElectricianSkill).filter(ElectricianSkill.electrician_id == electrician_id).all()
    specializations = [skill.specialization for skill in skills]

    logger.info(f"Retrieved skills for electrician {electrician_id}: {specializations}")

    return SkillsResponse(
        electrician_id=electrician_id,
        specializations=specializations
    )


@router.post("/jobs/rounds/{round_id}/accept", response_model=RoundAcceptanceResponse)
async def accept_round(
    round_id: int,
    claims: dict[str, Any] = Depends(get_current_electrician),
    db: Session = Depends(get_db),
) -> RoundAcceptanceResponse:
    electrician_id = claims.get("sub")
    if not electrician_id:
        logger.error("Missing sub claim in token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    dispatch_round = db.query(DispatchRound).filter(DispatchRound.id == round_id).first()
    if not dispatch_round:
        logger.info(f"Round {round_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")

    if dispatch_round.status != "open":
        logger.info(f"Round {round_id} is not open (status={dispatch_round.status})")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This round has already been {dispatch_round.status}"
        )

    candidate = db.query(DispatchRoundCandidate).filter(
        and_(
            DispatchRoundCandidate.round_id == round_id,
            DispatchRoundCandidate.electrician_id == electrician_id
        )
    ).first()

    if not candidate:
        logger.info(f"Electrician {electrician_id} is not a candidate for round {round_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a candidate for this round"
        )

    stmt = (
        update(DispatchRound)
        .where(and_(DispatchRound.id == round_id, DispatchRound.status == "open"))
        .values(status="filled")
    )
    result = db.execute(stmt)
    db.commit()

    if result.rowcount == 0:
        logger.info(f"Round {round_id} was filled by someone else (atomic update returned 0 rows)")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This round has already been accepted by another electrician"
        )

    for segment_id in dispatch_round.segment_ids:
        segment = db.query(OrderSegment).filter(OrderSegment.id == segment_id).first()
        if segment:
            segment.status = "assigned"
            segment.electrician_id = electrician_id
            db.add(segment)

    db.commit()

    assigned_segments = db.query(OrderSegment).filter(
        OrderSegment.id.in_(dispatch_round.segment_ids)
    ).all()

    total_amount = sum(seg.amount for seg in assigned_segments)

    order = db.query(Order).filter(Order.id == dispatch_round.order_id).first()
    if order:
        open_segments = db.query(OrderSegment).filter(
            and_(
                OrderSegment.order_id == order.id,
                OrderSegment.status == "open"
            )
        ).count()

        if open_segments == 0:
            order.status = "assigned"
            db.add(order)
            db.commit()

    logger.info(f"Round {round_id} accepted by electrician {electrician_id}, {len(assigned_segments)} segments assigned")

    return RoundAcceptanceResponse(
        round_id=round_id,
        segments=[
            OrderSegmentResponse(
                id=seg.id,
                order_id=seg.order_id,
                specialization=seg.specialization,
                amount=seg.amount,
                service_item_id=seg.service_item_id,
                status=seg.status,
                electrician_id=seg.electrician_id,
                created_at=seg.created_at.isoformat() if hasattr(seg.created_at, 'isoformat') else str(seg.created_at),
            )
            for seg in assigned_segments
        ],
        total_amount=total_amount
    )
