from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
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
    price = Column(Integer, nullable=False, default=0)
    specialization = Column(String, nullable=False, default="general_repair")
    active = Column(Boolean, default=True)


class ServiceItem(Base):
    __tablename__ = "service_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    specialization = Column(String, nullable=False, default="")
    active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, nullable=False)
    repair_issue_ids = Column(JSON, nullable=False, default=list)
    service_item_ids = Column(JSON, nullable=False, default=list)
    total_amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending_assignment")
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderSegment(Base):
    __tablename__ = "order_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    specialization = Column(String, nullable=False)
    repair_issue_id = Column(Integer, ForeignKey("repair_issues.id"), nullable=True)
    service_item_id = Column(Integer, ForeignKey("service_items.id"), nullable=True)
    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="open")
    electrician_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ElectricianSkill(Base):
    __tablename__ = "electrician_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    electrician_id = Column(String, ForeignKey("users.id"), nullable=False)
    specialization = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DispatchRound(Base):
    __tablename__ = "dispatch_rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    segment_ids = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class DispatchRoundCandidate(Base):
    __tablename__ = "dispatch_round_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey("dispatch_rounds.id"), nullable=False)
    electrician_id = Column(String, ForeignKey("users.id"), nullable=False)
    notified_at = Column(DateTime, default=datetime.utcnow)
