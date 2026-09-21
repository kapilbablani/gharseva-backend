from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RepairIssue(Base):
    __tablename__ = "repair_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    active = Column(Boolean, default=True)


class ServiceItem(Base):
    __tablename__ = "service_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    active = Column(Boolean, default=True)


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repair_visit_charge = Column(Integer, nullable=False, default=300)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, nullable=False)
    repair_issue_ids = Column(JSON, nullable=False, default=list)
    service_item_ids = Column(JSON, nullable=False, default=list)
    visit_charge_applied = Column(Integer, nullable=False)
    service_total = Column(Integer, nullable=False)
    total_amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending_assignment")
    created_at = Column(DateTime, default=datetime.utcnow)
