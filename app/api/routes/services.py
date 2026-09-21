from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AppConfig, RepairIssue, ServiceItem
from app.db.session import get_db

router = APIRouter()


class RepairIssueResponse(BaseModel):
    id: int
    name: str


class RepairResponse(BaseModel):
    visit_charge: int
    issues: List[RepairIssueResponse]


class ServiceItemResponse(BaseModel):
    id: int
    name: str
    price: int


class CatalogResponse(BaseModel):
    category: str
    repair: RepairResponse
    service: List[ServiceItemResponse]


@router.get("/services", response_model=CatalogResponse)
async def get_services(category: str = "electrician", db: Session = Depends(get_db)):
    repair_issues = (
        db.query(RepairIssue)
        .filter(RepairIssue.category == category, RepairIssue.active)
        .all()
    )

    service_items = (
        db.query(ServiceItem)
        .filter(ServiceItem.category == category, ServiceItem.active)
        .all()
    )

    app_config = db.query(AppConfig).first()
    visit_charge = app_config.repair_visit_charge if app_config else 300

    repair_response = RepairResponse(
        visit_charge=visit_charge,
        issues=[RepairIssueResponse(id=issue.id, name=issue.name) for issue in repair_issues],
    )

    service_response = [
        ServiceItemResponse(id=item.id, name=item.name, price=item.price) for item in service_items
    ]

    return CatalogResponse(
        category=category,
        repair=repair_response,
        service=service_response,
    )
