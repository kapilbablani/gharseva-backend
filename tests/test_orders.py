from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.orders import router as orders_router
from app.db.models import AppConfig, Base, Order, RepairIssue, ServiceItem, User
from app.db.session import get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user(sub="user123"):
    def _get_current_user():
        return {"sub": sub, "cognito:groups": ["customer"], "token_use": "id", "email": "test@example.com"}
    return _get_current_user


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.query(Order).delete()
    db.query(ServiceItem).delete()
    db.query(RepairIssue).delete()
    db.query(AppConfig).delete()
    db.query(User).delete()
    db.commit()
    db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seed_data(db):
    repair_issues = [
        RepairIssue(id=1, name="Fan repair", category="electrician", active=True),
        RepairIssue(id=2, name="AC repair", category="electrician", active=True),
        RepairIssue(id=3, name="Socket repair", category="electrician", active=False),
    ]
    service_items = [
        ServiceItem(id=1, name="Fan installation", price=1000, category="electrician", active=True),
        ServiceItem(id=2, name="AC installation", price=4000, category="electrician", active=True),
        ServiceItem(id=3, name="Other service", price=500, category="electrician", active=False),
    ]
    app_config = AppConfig(id=1, repair_visit_charge=300)

    db.add_all(repair_issues)
    db.add_all(service_items)
    db.add(app_config)
    db.commit()
    return db


class TestCreateOrder:
    def test_create_order_with_repair_issues_only(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [1, 2], "service_item_ids": []},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["repair_issue_ids"] == [1, 2]
        assert data["service_item_ids"] == []
        assert data["visit_charge_applied"] == 300
        assert data["service_total"] == 0
        assert data["total_amount"] == 300
        assert data["status"] == "pending_assignment"

    def test_create_order_with_service_items_only(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [], "service_item_ids": [1, 2]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["repair_issue_ids"] == []
        assert data["service_item_ids"] == [1, 2]
        assert data["visit_charge_applied"] == 0
        assert data["service_total"] == 5000
        assert data["total_amount"] == 5000

    def test_create_order_with_both(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [1], "service_item_ids": [1, 2]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["visit_charge_applied"] == 300
        assert data["service_total"] == 5000
        assert data["total_amount"] == 5300

    def test_create_order_empty_lists_returns_400(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [], "service_item_ids": []},
        )
        assert response.status_code == 400
        assert "select at least one item" in response.json()["detail"]
        assert TestingSessionLocal().query(Order).count() == 0

    def test_create_order_nonexistent_repair_id_returns_400(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [999], "service_item_ids": []},
        )
        assert response.status_code == 400
        assert "Invalid IDs" in response.json()["detail"]
        assert TestingSessionLocal().query(Order).count() == 0

    def test_create_order_inactive_repair_id_returns_400(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [3], "service_item_ids": []},
        )
        assert response.status_code == 400
        assert "Invalid IDs" in response.json()["detail"]
        assert TestingSessionLocal().query(Order).count() == 0

    def test_create_order_nonexistent_service_id_returns_400(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [], "service_item_ids": [999]},
        )
        assert response.status_code == 400
        assert "Invalid IDs" in response.json()["detail"]

    def test_create_order_inactive_service_id_returns_400(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.post(
            "/orders",
            json={"repair_issue_ids": [], "service_item_ids": [3]},
        )
        assert response.status_code == 400
        assert "Invalid IDs" in response.json()["detail"]


class TestListOrders:
    def test_list_customer_orders_newest_first(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        order1 = Order(
            customer_id="user123",
            repair_issue_ids=[1],
            service_item_ids=[],
            visit_charge_applied=300,
            service_total=0,
            total_amount=300,
            status="pending_assignment",
        )
        order2 = Order(
            customer_id="user123",
            repair_issue_ids=[],
            service_item_ids=[1],
            visit_charge_applied=0,
            service_total=1000,
            total_amount=1000,
            status="pending_assignment",
        )
        db = TestingSessionLocal()
        db.add(order1)
        db.commit()
        db.refresh(order1)
        db.add(order2)
        db.commit()
        db.refresh(order2)
        db.close()

        response = client.get("/orders/me")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == order2.id
        assert data[1]["id"] == order1.id

    def test_list_orders_empty(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        response = client.get("/orders/me")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_orders_only_own_orders(self, client, seed_data):
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user("user123")

        order1 = Order(
            customer_id="user123",
            repair_issue_ids=[1],
            service_item_ids=[],
            visit_charge_applied=300,
            service_total=0,
            total_amount=300,
            status="pending_assignment",
        )
        order2 = Order(
            customer_id="user456",
            repair_issue_ids=[1],
            service_item_ids=[],
            visit_charge_applied=300,
            service_total=0,
            total_amount=300,
            status="pending_assignment",
        )
        db = TestingSessionLocal()
        db.add(order1)
        db.add(order2)
        db.commit()
        db.close()

        response = client.get("/orders/me")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["customer_id"] == "user123"
