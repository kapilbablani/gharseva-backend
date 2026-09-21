#!/usr/bin/env python3
"""
Manual verification script for orders feature implementation.
Tests by directly calling route handlers with mocked dependencies.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.orders import create_order, list_orders
from app.db.models import (
    AppConfig,
    Base,
    Order,
    RepairIssue,
    ServiceItem,
)

# Suppress verbose logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Test counter
passed = 0
failed = 0


def run_test(name: str, condition: bool, details: str = ""):
    """Record test result."""
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if details:
        print(f"        {details}")
    if condition:
        passed += 1
    else:
        failed += 1


def create_test_db():
    """Create a fresh in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal


def seed_test_data(db: Session) -> dict:
    """Populate test database."""
    # Repair issues
    repair_issues = [
        RepairIssue(name="Fan repair", category="electrician"),
        RepairIssue(name="AC repair", category="electrician"),
        RepairIssue(name="Light/switch repair", category="electrician"),
    ]
    db.add_all(repair_issues)
    db.commit()

    # Service items
    service_items = [
        ServiceItem(name="Fan installation", price=1000, category="electrician"),
        ServiceItem(name="AC installation", price=4000, category="electrician"),
        ServiceItem(name="AC gas filling", price=5000, category="electrician"),
    ]
    db.add_all(service_items)
    db.commit()

    # App config
    app_config = AppConfig(repair_visit_charge=300)
    db.add(app_config)
    db.commit()

    # Inactive repair issue
    inactive_issue = RepairIssue(name="Old repair type", category="electrician", active=False)
    db.add(inactive_issue)
    db.commit()

    return {
        "repair_issues": [r.id for r in repair_issues],
        "service_items": [s.id for s in service_items],
        "inactive_issue_id": inactive_issue.id,
    }


async def test_criterion_1():
    """Test: POST /orders with only repair issue IDs."""
    print("\n[TEST 1] POST /orders with only repair issue IDs")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    data = seed_test_data(db)

    claims = {"sub": "user123", "cognito:groups": ["customer"]}

    try:
        from app.api.routes.orders import OrderCreateRequest

        request = OrderCreateRequest(
            repair_issue_ids=[data["repair_issues"][0]],
            service_item_ids=[],
        )

        response = await create_order(request, claims, db)

        run_test(
            "Response returned",
            response is not None,
            f"Got {type(response)}",
        )

        if response:
            run_test(
                "visit_charge_applied = 300",
                response.visit_charge_applied == 300,
                f"Got {response.visit_charge_applied}",
            )
            run_test(
                "service_total = 0",
                response.service_total == 0,
                f"Got {response.service_total}",
            )
            run_test(
                "total_amount = 300",
                response.total_amount == 300,
                f"Got {response.total_amount}",
            )
    except Exception as e:
        run_test("No exception raised", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_2():
    """Test: POST /orders with only service item IDs."""
    print("\n[TEST 2] POST /orders with only service item IDs")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    data = seed_test_data(db)

    claims = {"sub": "user456", "cognito:groups": ["customer"]}

    try:
        from app.api.routes.orders import OrderCreateRequest

        request = OrderCreateRequest(
            repair_issue_ids=[],
            service_item_ids=[data["service_items"][0], data["service_items"][1]],
        )

        response = await create_order(request, claims, db)

        run_test(
            "visit_charge_applied = 0",
            response.visit_charge_applied == 0,
            f"Got {response.visit_charge_applied}",
        )
        run_test(
            "service_total = 5000",
            response.service_total == 5000,
            f"Got {response.service_total}",
        )
        run_test(
            "total_amount = 5000",
            response.total_amount == 5000,
            f"Got {response.total_amount}",
        )
    except Exception as e:
        run_test("No exception raised", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_3():
    """Test: POST /orders with both repair issues and service items."""
    print("\n[TEST 3] POST /orders with both repair issues and service items")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    data = seed_test_data(db)

    claims = {"sub": "user789", "cognito:groups": ["customer"]}

    try:
        from app.api.routes.orders import OrderCreateRequest

        request = OrderCreateRequest(
            repair_issue_ids=[data["repair_issues"][0]],
            service_item_ids=[data["service_items"][1]],
        )

        response = await create_order(request, claims, db)

        run_test(
            "visit_charge_applied = 300",
            response.visit_charge_applied == 300,
            f"Got {response.visit_charge_applied}",
        )
        run_test(
            "service_total = 4000",
            response.service_total == 4000,
            f"Got {response.service_total}",
        )
        run_test(
            "total_amount = 4300",
            response.total_amount == 4300,
            f"Got {response.total_amount}",
        )
    except Exception as e:
        run_test("No exception raised", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_4():
    """Test: POST /orders with both lists empty returns 400."""
    print("\n[TEST 4] POST /orders with both lists empty")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    seed_test_data(db)

    claims = {"sub": "user_empty", "cognito:groups": ["customer"]}

    try:
        from app.api.routes.orders import OrderCreateRequest
        from fastapi import HTTPException

        request = OrderCreateRequest(
            repair_issue_ids=[],
            service_item_ids=[],
        )

        response = await create_order(request, claims, db)
        run_test("Returned 400 error", False, f"Got successful response instead of HTTPException")

    except HTTPException as e:
        run_test(
            "HTTPException with 400 status",
            e.status_code == 400,
            f"Got {e.status_code}",
        )
        run_test(
            "Error message mentions items",
            "item" in e.detail.lower(),
            f"Got: {e.detail}",
        )

        # Verify no order created
        orders = db.query(Order).all()
        run_test(
            "No order created",
            len(orders) == 0,
            f"Found {len(orders)} orders",
        )

    except Exception as e:
        run_test("HTTPException raised", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_5():
    """Test: POST /orders with nonexistent or inactive ID."""
    print("\n[TEST 5] POST /orders with nonexistent or inactive IDs")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    data = seed_test_data(db)

    claims = {"sub": "user_invalid", "cognito:groups": ["customer"]}

    try:
        from app.api.routes.orders import OrderCreateRequest
        from fastapi import HTTPException

        # Test nonexistent ID
        request = OrderCreateRequest(
            repair_issue_ids=[999],
            service_item_ids=[],
        )

        try:
            response = await create_order(request, claims, db)
            run_test("Nonexistent ID returns 400", False, "Got successful response")
        except HTTPException as e:
            run_test(
                "Nonexistent ID returns 400",
                e.status_code == 400,
                f"Got {e.status_code}",
            )
            run_test(
                "Error names the invalid ID",
                "999" in e.detail,
                f"Got: {e.detail}",
            )

        # Verify no order created
        orders = db.query(Order).all()
        run_test(
            "No order created for nonexistent ID",
            len(orders) == 0,
            f"Found {len(orders)} orders",
        )

        # Test inactive ID
        request = OrderCreateRequest(
            repair_issue_ids=[data["inactive_issue_id"]],
            service_item_ids=[],
        )

        try:
            response = await create_order(request, claims, db)
            run_test("Inactive ID returns 400", False, "Got successful response")
        except HTTPException as e:
            run_test(
                "Inactive ID returns 400",
                e.status_code == 400,
                f"Got {e.status_code}",
            )
            run_test(
                "Error names the inactive ID",
                str(data["inactive_issue_id"]) in e.detail,
                f"Got: {e.detail}",
            )

        # Verify still no orders
        orders = db.query(Order).all()
        run_test(
            "No orders created for invalid IDs",
            len(orders) == 0,
            f"Found {len(orders)} orders",
        )

    except Exception as e:
        run_test("No unexpected exceptions", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_6():
    """Test: GET /orders/me returns only customer's own orders, newest first."""
    print("\n[TEST 6] GET /orders/me returns only customer's own orders, newest first")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    data = seed_test_data(db)

    # Create orders
    order1_cust1 = Order(
        customer_id="customer1",
        repair_issue_ids=[data["repair_issues"][0]],
        service_item_ids=[],
        visit_charge_applied=300,
        service_total=0,
        total_amount=300,
        status="pending_assignment",
        created_at=datetime.utcnow(),
    )
    db.add(order1_cust1)
    db.commit()

    order1_cust2 = Order(
        customer_id="customer2",
        repair_issue_ids=[],
        service_item_ids=[data["service_items"][0]],
        visit_charge_applied=0,
        service_total=1000,
        total_amount=1000,
        status="pending_assignment",
        created_at=datetime.utcnow(),
    )
    db.add(order1_cust2)
    db.commit()

    order2_cust1 = Order(
        customer_id="customer1",
        repair_issue_ids=[],
        service_item_ids=[data["service_items"][1]],
        visit_charge_applied=0,
        service_total=4000,
        total_amount=4000,
        status="pending_assignment",
        created_at=datetime.utcnow(),
    )
    db.add(order2_cust1)
    db.commit()

    claims = {"sub": "customer1", "cognito:groups": ["customer"]}

    try:
        orders = await list_orders(claims, db)

        run_test(
            "Customer 1 has 2 orders",
            len(orders) == 2,
            f"Got {len(orders)} orders",
        )

        all_are_customer1 = all(o.customer_id == "customer1" for o in orders)
        run_test(
            "All returned orders belong to customer1",
            all_are_customer1,
            f"Got orders from: {set(o.customer_id for o in orders)}",
        )

        if len(orders) == 2:
            run_test(
                "Orders are newest first",
                orders[0].total_amount == 4000,
                f"First order total: {orders[0].total_amount}, expected 4000",
            )

    except Exception as e:
        run_test("No exception raised", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_7():
    """Test: GET /orders/me for customer with zero orders."""
    print("\n[TEST 7] GET /orders/me for customer with zero orders")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    seed_test_data(db)

    claims = {"sub": "customer_no_orders", "cognito:groups": ["customer"]}

    try:
        orders = await list_orders(claims, db)

        run_test(
            "Response is list",
            isinstance(orders, list),
            f"Got {type(orders)}",
        )
        run_test(
            "Empty list returned",
            len(orders) == 0,
            f"Got {len(orders)} orders",
        )

    except Exception as e:
        run_test("No exception raised", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def test_criterion_8():
    """Test: Access token instead of ID token returns 401."""
    print("\n[TEST 8] Access token instead of ID token returns 401")
    engine, SessionLocal = create_test_db()
    db = SessionLocal()
    data = seed_test_data(db)

    # Simulate access token (missing required ID token claims)
    claims = {"token_use": "access", "client_id": "someclient"}

    try:
        from app.api.routes.orders import OrderCreateRequest
        from fastapi import HTTPException

        request = OrderCreateRequest(
            repair_issue_ids=[data["repair_issues"][0]],
            service_item_ids=[],
        )

        # This should fail because claims is missing 'sub' field
        try:
            response = await create_order(request, claims, db)
            run_test("POST /orders with access token returns 401", False, "Got successful response")
        except HTTPException as e:
            run_test(
                "POST /orders with access token returns 401",
                e.status_code == 401,
                f"Got {e.status_code}",
            )

        # Similar test for GET /orders/me
        try:
            orders = await list_orders(claims, db)
            run_test("GET /orders/me with access token returns 401", False, "Got successful response")
        except HTTPException as e:
            run_test(
                "GET /orders/me with access token returns 401",
                e.status_code == 401,
                f"Got {e.status_code}",
            )

    except Exception as e:
        if not isinstance(e, HTTPException):
            run_test("No unexpected exceptions", False, f"Got {type(e).__name__}: {e}")
    finally:
        db.close()
        engine.dispose()


async def main():
    """Run all tests."""
    global passed, failed

    print("=" * 70)
    print("GharSeva Orders Feature - Manual Verification Script")
    print("=" * 70)

    await test_criterion_1()
    await test_criterion_2()
    await test_criterion_3()
    await test_criterion_4()
    await test_criterion_5()
    await test_criterion_6()
    await test_criterion_7()
    await test_criterion_8()

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\nAll acceptance criteria met!")
        return 0
    else:
        print(f"\n{failed} test(s) failed. Review details above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
