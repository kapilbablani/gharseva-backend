import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.electricians import router as electricians_router
from app.api.routes.orders import router as orders_router
from app.api.routes.services import router as services_router
from app.api.routes.users import router as users_router
from app.core.dispatch import process_expired_rounds
from app.db.models import Base, DispatchRound, DispatchRoundCandidate, ElectricianSkill, Order, OrderSegment, RepairIssue, ServiceItem
from app.db.session import SessionLocal, engine

logger = logging.getLogger(__name__)

app = FastAPI(title="GharSeva API")

Base.metadata.create_all(bind=engine)


def seed_catalog():
    db = SessionLocal()
    try:
        repair_issue_data = [
            {"name": "General repair", "category": "electrician", "price": 300, "specialization": "general_repair"},
            {"name": "AC repair", "category": "electrician", "price": 1000, "specialization": "ac_repair"},
            {"name": "Refrigerator repair", "category": "electrician", "price": 500, "specialization": "refrigerator_repair"},
            {"name": "Mixer grinder repair", "category": "electrician", "price": 500, "specialization": "mixer_grinder_repair"},
        ]

        for data in repair_issue_data:
            existing = db.query(RepairIssue).filter(RepairIssue.name == data["name"]).first()
            if existing:
                existing.price = data["price"]
                existing.specialization = data["specialization"]
                db.add(existing)
            else:
                db.add(RepairIssue(**data))
        db.commit()

        service_item_data = [
            {"name": "Fan installation", "price": 1000, "category": "electrician", "specialization": "fan_installation"},
            {"name": "AC installation", "price": 4000, "category": "electrician", "specialization": "ac_installation"},
            {"name": "AC gas filling", "price": 5000, "category": "electrician", "specialization": "ac_gas_filling"},
            {"name": "Switchboard installation", "price": 800, "category": "electrician", "specialization": "switchboard_installation"},
        ]

        for data in service_item_data:
            existing = db.query(ServiceItem).filter(ServiceItem.name == data["name"]).first()
            if existing:
                existing.price = data["price"]
                existing.specialization = data["specialization"]
                db.add(existing)
            else:
                db.add(ServiceItem(**data))
        db.commit()
    finally:
        db.close()


seed_catalog()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_expired_rounds, "interval", minutes=1)
    scheduler.start()


start_scheduler()

app.include_router(auth_router)
app.include_router(electricians_router)
app.include_router(orders_router)
app.include_router(services_router)
app.include_router(users_router)
