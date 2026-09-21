# Spec: Create and List Orders

## Scope

This spec introduces the `Order` table and two endpoints: creating an order from a customer's selected Repair issues and/or Service items, and listing a customer's own past orders.

This spec does NOT cover:
- Electrician assignment/matching (a later spec, orders created here have no electrician attached yet, they're just recorded as placed)
- Payment processing (a later spec, this spec does not integrate any payment gateway, it only computes and stores the total)
- Scheduling/time slots (a later spec; if the Android cart screen collects a preferred time, that field can be added to this spec's request shape later, out of scope for now)
- Order status transitions beyond creation (no "in progress," "completed," etc. yet)

## Background

The Android app's Home screen (already implemented) lets a customer select any combination of Repair issue IDs and Service item IDs, computing a running total client-side for display purposes only. That client-side total must never be trusted for the actual charge, this spec recomputes the total server-side from the current database prices, so a stale app, a tampered request, or a race with a price change can't result in an incorrect charge.

## Database

New model in `app/db/models.py`:

### `Order`
- `id` — integer, primary key, auto-increment
- `customer_id` — string, foreign key to `User.id`
- `repair_issue_ids` — JSON column (list of integers), the `RepairIssue` IDs selected, empty list if none
- `service_item_ids` — JSON column (list of integers), the `ServiceItem` IDs selected, empty list if none
- `visit_charge_applied` — integer, the visit charge amount actually applied (0 if no repair issues were selected, otherwise the `AppConfig.repair_visit_charge` value at the time of creation, stored so a later price change doesn't retroactively alter historical orders)
- `service_total` — integer, sum of the selected service items' prices at the time of creation (same reasoning, stored not recomputed later)
- `total_amount` — integer, `visit_charge_applied + service_total`
- `status` — string, default `"pending_assignment"` (the only status this spec produces; future specs will add transitions like assigned, in_progress, completed)
- `created_at` — datetime, defaults to now

## Behavior

### `POST /orders` (`app/api/routes/orders.py`, new route file)

- Protected by `get_current_user` (ID token), the order belongs to whoever is calling.
- Request body: `{ "repair_issue_ids": [1, 2], "service_item_ids": [3] }` (either list may be empty, but not both, an order with nothing selected is invalid).
- Validation:
  - If both lists are empty, return 400 with a clear message ("select at least one item").
  - Look up each ID against the current `RepairIssue`/`ServiceItem` tables. If any ID doesn't exist or isn't `active`, return 400 naming which IDs were invalid, don't silently drop them or silently succeed with a wrong total.
- Computation (server-side, never trust any price/total sent by the client, only IDs):
  - If `repair_issue_ids` is non-empty, `visit_charge_applied` = current `AppConfig.repair_visit_charge`, otherwise 0.
  - `service_total` = sum of the current `price` for each ID in `service_item_ids`.
  - `total_amount` = `visit_charge_applied + service_total`.
- Create the `Order` row with `customer_id` from the token's `sub`, `status = "pending_assignment"`.
- Return 201 with the full created order (all fields above, including the resolved `total_amount`, so the app doesn't need to recompute anything client-side to display a confirmation).

### `GET /orders/me` (`app/api/routes/orders.py`, same file)

- Protected by `get_current_user` (ID token).
- Returns a list of the caller's own orders (`customer_id` matches the token's `sub`), newest first.
- Each item in the same shape as the `POST /orders` response.
- Returns an empty list (not an error) if the customer has no orders yet.

## Non-functional requirements

- All prices/totals are computed and stored server-side at creation time; the client never supplies a price or total in the request body, only IDs.
- `repair_issue_ids`/`service_item_ids` must never include an ID belonging to a different, inactive, or nonexistent catalog entry, validated before the order is created, not after.
- Response models are Pydantic, not raw dicts, per `CLAUDE.md`.
- No token or other sensitive value is logged.

## Acceptance criteria

- [ ] `POST /orders` with only repair issue IDs creates an order with the visit charge applied and `service_total = 0`.
- [ ] `POST /orders` with only service item IDs creates an order with `visit_charge_applied = 0` and the correct summed `service_total`.
- [ ] `POST /orders` with both creates an order with the visit charge applied once plus the correct service total, matching the combined-selection math from the original design (e.g. ₹300 + ₹4,000 = ₹4,300).
- [ ] `POST /orders` with both lists empty returns 400, no order created.
- [ ] `POST /orders` with a nonexistent or inactive ID returns 400 naming the invalid ID, no order created.
- [ ] `GET /orders/me` returns only the calling customer's own orders, never another customer's, newest first.
- [ ] A customer with zero orders gets `200` with an empty list from `GET /orders/me`, not an error.
- [ ] An access token (instead of ID token) sent to either endpoint returns 401, consistent with the rest of the app's token-type rules.