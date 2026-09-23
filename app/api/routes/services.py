from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import RepairIssue, ServiceItem
from app.db.session import get_db

router = APIRouter()


class ItemResponse(BaseModel):
    id: int
    name: str
    price: int


class CatalogResponse(BaseModel):
    category: str
    repair: List[ItemResponse]
    service: List[ItemResponse]


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

    repair_response = [
        ItemResponse(id=issue.id, name=issue.name, price=issue.price) for issue in repair_issues
    ]

    service_response = [
        ItemResponse(id=item.id, name=item.name, price=item.price) for item in service_items
    ]

    return CatalogResponse(
        category=category,
        repair=repair_response,
        service=service_response,
    )
