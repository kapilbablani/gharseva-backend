from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.orders import router as orders_router
from app.api.routes.services import router as services_router
from app.api.routes.users import router as users_router
from app.db.models import AppConfig, Base, Order, RepairIssue, ServiceItem
from app.db.session import SessionLocal, engine

app = FastAPI(title="GharSeva API")

Base.metadata.create_all(bind=engine)


def seed_catalog():
    db = SessionLocal()
    try:
        if db.query(RepairIssue).count() == 0:
            repair_issues = [
                RepairIssue(name="Fan repair", category="electrician"),
                RepairIssue(name="AC repair", category="electrician"),
                RepairIssue(name="Light/switch repair", category="electrician"),
                RepairIssue(name="Socket repair", category="electrician"),
                RepairIssue(name="Other", category="electrician"),
            ]
            db.add_all(repair_issues)
            db.commit()

        if db.query(ServiceItem).count() == 0:
            service_items = [
                ServiceItem(name="Fan installation", price=1000, category="electrician"),
                ServiceItem(name="AC installation", price=4000, category="electrician"),
                ServiceItem(name="AC gas filling", price=5000, category="electrician"),
                ServiceItem(name="Switchboard installation", price=800, category="electrician"),
            ]
            db.add_all(service_items)
            db.commit()

        if db.query(AppConfig).count() == 0:
            app_config = AppConfig(repair_visit_charge=300)
            db.add(app_config)
            db.commit()
    finally:
        db.close()


seed_catalog()

app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(services_router)
app.include_router(users_router)
