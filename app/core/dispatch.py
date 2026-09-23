import logging
from datetime import datetime, timedelta
from itertools import combinations

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import DispatchRound, DispatchRoundCandidate, ElectricianSkill, Order, OrderSegment
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def send_job_offer_notification(electrician_id: str, round_id: int, segment_names: list[str], total_amount: int):
    logger.info(f"[STUB] Would notify {electrician_id} of round {round_id}: {segment_names}, ₹{total_amount}")


def compute_and_broadcast_rounds(order_id: int):
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return

        _broadcast_for_open_segments(db, order)
    finally:
        db.close()


def _broadcast_for_open_segments(db: Session, order: Order):
    open_segments = db.query(OrderSegment).filter(
        OrderSegment.order_id == order.id,
        OrderSegment.status == "open"
    ).all()

    if not open_segments:
        logger.info(f"Order {order.id}: no open segments, dispatch complete")
        return

    open_segment_ids = [s.id for s in open_segments]
    segment_map = {s.id: s for s in open_segments}

    best_grouping = _find_best_grouping(db, open_segment_ids, segment_map)

    if not best_grouping:
        for segment_id in open_segment_ids:
            segment = segment_map[segment_id]
            round_expires_at = datetime.utcnow() + timedelta(minutes=15)
            dispatch_round = DispatchRound(
                order_id=order.id,
                segment_ids=[segment_id],
                status="open",
                expires_at=round_expires_at
            )
            db.add(dispatch_round)

        db.commit()
        logger.warning(f"Order {order.id}: no electricians found for open segments, created zero-candidate rounds")
        return

    best_segment_ids, candidate_electricians = best_grouping

    round_expires_at = datetime.utcnow() + timedelta(minutes=15)
    dispatch_round = DispatchRound(
        order_id=order.id,
        segment_ids=best_segment_ids,
        status="open",
        expires_at=round_expires_at
    )
    db.add(dispatch_round)
    db.flush()

    for electrician_id in candidate_electricians:
        candidate = DispatchRoundCandidate(
            round_id=dispatch_round.id,
            electrician_id=electrician_id
        )
        db.add(candidate)

    db.commit()

    segment_names = [segment_map[seg_id].specialization for seg_id in best_segment_ids]
    segment_total = sum(segment_map[seg_id].amount for seg_id in best_segment_ids)

    for electrician_id in candidate_electricians:
        send_job_offer_notification(electrician_id, dispatch_round.id, segment_names, segment_total)

    logger.info(f"Broadcast round {dispatch_round.id} for order {order.id} with {len(best_segment_ids)} segments to {len(candidate_electricians)} candidates")

    remaining_segment_ids = [s_id for s_id in open_segment_ids if s_id not in best_segment_ids]
    if remaining_segment_ids:
        _broadcast_for_open_segments(db, order)


def _find_best_grouping(db: Session, open_segment_ids: list[int], segment_map: dict) -> tuple[list[int], list[str]] | None:
    if not open_segment_ids:
        return None

    all_electricians = db.query(ElectricianSkill.electrician_id).distinct().all()
    electrician_ids = [e[0] for e in all_electricians if e[0]]

    for group_size in range(len(open_segment_ids), 0, -1):
        for segment_combo in combinations(open_segment_ids, group_size):
            segment_combo_list = list(segment_combo)
            matching_electricians = _find_electricians_covering_segments(
                db, segment_combo_list, segment_map, electrician_ids
            )

            if matching_electricians:
                return (segment_combo_list, matching_electricians)

    return None


def _find_electricians_covering_segments(
    db: Session, segment_ids: list[int], segment_map: dict, electrician_ids: list[str]
) -> list[str]:
    matching_electricians = []

    for electrician_id in electrician_ids:
        skills = db.query(ElectricianSkill).filter(
            ElectricianSkill.electrician_id == electrician_id
        ).all()

        skill_specializations = {s.specialization for s in skills}

        covers_all = True
        for segment_id in segment_ids:
            segment = segment_map.get(segment_id)
            if not segment:
                covers_all = False
                break

            if segment.specialization not in skill_specializations:
                covers_all = False
                break

        if covers_all:
            matching_electricians.append(electrician_id)

    return matching_electricians


def process_expired_rounds():
    db = SessionLocal()
    try:
        expired_rounds = db.query(DispatchRound).filter(
            and_(
                DispatchRound.status == "open",
                DispatchRound.expires_at < datetime.utcnow()
            )
        ).all()

        for round_obj in expired_rounds:
            if round_obj.status != "open":
                continue

            round_obj.status = "expired"
            db.add(round_obj)
            db.flush()

            order = db.query(Order).filter(Order.id == round_obj.order_id).first()
            if order:
                _broadcast_for_open_segments(db, order)

        db.commit()

        if expired_rounds:
            logger.info(f"Processed {len(expired_rounds)} expired rounds")
    except Exception as e:
        logger.error(f"Error processing expired rounds: {e}")
        db.rollback()
    finally:
        db.close()
