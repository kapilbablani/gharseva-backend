# Spec: Create and List Orders

## Scope

This spec introduces the `Order` table and two endpoints: creating an order from a customer's selected Repair issues and/or Service items, and listing a customer's own past orders.

This spec does NOT cover:
- Segment creation, electrician assignment, or dispatch (see the electrician skills/segments spec and the dispatch rounds spec, both of which extend `POST /orders` with additional behavior beyond what's described here)
- Payment processing (a separate spec; this spec only computes and stores the total)
- Scheduling/time slots (a separate spec)
- Order status transitions beyond creation (status derivation is defined in the electrician skills/segments spec)

## Background

The Android app's Home screen lets a customer select any combination of Repair issue IDs and Service item IDs, computing a running total client-side for display purposes only. That client-side total is never trusted for the actual charge, the true total is computed server-side, from segment amounts (defined in the electrician skills/segments spec), so a stale app or a tampered request can't result in an incorrect charge.

## Database

### `Order`
- `id` — integer, primary key, auto-increment
- `customer_id` — string, foreign key to `User.id`
- `repair_issue_ids` — JSON column (list of integers), the `RepairIssue` IDs selected, empty list if none
- `service_item_ids` — JSON column (list of integers), the `ServiceItem` IDs selected, empty list if none
- `total_amount` — integer, the sum of this order's segment amounts (segments are created by the electrician skills/segments spec's extension of `POST /orders`)
- `status` — string, default `"pending_assignment"`, derived from segment assignment state (see the electrician skills/segments spec)
- `created_at` — datetime, defaults to now

## Behavior

### `POST /orders`

- Protected by `get_current_user` (ID token), the order belongs to whoever is calling.
- Request body: `{ "repair_issue_ids": [1, 2], "service_item_ids": [3] }` (either list may be empty, but not both).
- Validation:
  - If both lists are empty, return 400 ("select at least one item").
  - Look up each ID against the current `RepairIssue`/`ServiceItem` tables. If any ID doesn't exist or isn't `active`, return 400 naming which IDs were invalid.
- Create the `Order` row with `customer_id` from the token's `sub`, `status = "pending_assignment"`.
- Return 201 with the full created order.

### `GET /orders/me`

- Protected by `get_current_user` (ID token).
- Returns a list of the caller's own orders (`customer_id` matches the token's `sub`), newest first.
- Returns an empty list (not an error) if the customer has no orders yet.

## Non-functional requirements

- The client never supplies a price or total, only IDs, the server computes everything.
- `repair_issue_ids`/`service_item_ids` must never include an ID belonging to an inactive or nonexistent catalog entry, validated before the order is created.
- Response models are Pydantic, not raw dicts, per `CLAUDE.md`.
- No token or other sensitive value is logged.

## Acceptance criteria

- [ ] `POST /orders` with only repair issue IDs, only service item IDs, or a combination of both, creates an order with a correct `total_amount`.
- [ ] `POST /orders` with both lists empty returns 400, no order created.
- [ ] `POST /orders` with a nonexistent or inactive ID returns 400 naming the invalid ID, no order created.
- [ ] `GET /orders/me` returns only the calling customer's own orders, never another customer's, newest first.
- [ ] A customer with zero orders gets 200 with an empty list from `GET /orders/me`, not an error.
- [ ] An access token (instead of ID token) sent to either endpoint returns 401.