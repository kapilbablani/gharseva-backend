# Spec: Round-Based Job Dispatch with Escalation

## Scope

This is the electrician job acceptance mechanism: an active, round-based broadcast-and-escalate system. For each order, the system finds the smallest possible grouping of its open segments coverable by a single electrician's skillset, broadcasts that group to every matching electrician, and waits a fixed window for a response. If no one accepts (or no one qualifies), the group splits further and re-broadcasts, recursively, down to individual segments if needed.

Real push notification delivery is stubbed as a placeholder function that logs instead of sending, a separate future spec wires this to real Firebase Cloud Messaging without changing this spec's core logic.

This spec does NOT cover:
- Real FCM integration (the stub stands in for it)
- Location/distance-based ranking (skill-match only)
- Any electrician-facing UI (a separate Android spec; this backend spec's accept endpoint only needs to work correctly via direct API calls)
- What happens if literally no electrician anywhere can cover a given segment (an operational edge case needing future manual intervention, not solved here)

## Background

An order has one `OrderSegment` per distinct specialization present among what was selected. `specialization` is a fully generic string, matching is pure string comparison against `ElectricianSkill.specialization`, no hardcoded set of expected values anywhere.

## Database

### `DispatchRound`
- `id` — integer, primary key, auto-increment
- `order_id` — integer, foreign key to `Order.id`
- `segment_ids` — JSON column (list of integers), which `OrderSegment` IDs this round offers as one bundle
- `status` — string: `"open"`, `"filled"`, or `"expired"`
- `created_at` — datetime, defaults to now
- `expires_at` — datetime, `created_at + 15 minutes`

### `DispatchRoundCandidate`
- `id` — integer, primary key, auto-increment
- `round_id` — integer, foreign key to `DispatchRound.id`
- `electrician_id` — string, foreign key to `User.id`
- `notified_at` — datetime, defaults to now

## Grouping algorithm

Given an order's currently-open segments:

1. For each electrician with any `ElectricianSkill` rows, compute which open segments they could fully cover, a plain check of whether each segment's `specialization` is in that electrician's declared specializations.
2. Find the largest group of open segments that at least one electrician's skills fully cover. This is the best grouping for this round.
3. Broadcast that group: create one `DispatchRound`, and one `DispatchRoundCandidate` row for every electrician whose skills fully cover the entire group (no partial credit).
4. Any segments not included in the best group get their own separate, smaller grouping(s), computed the same way, recursively, broadcast as independent `DispatchRound`s in parallel.
5. If a segment has zero electricians anywhere with a matching skill, it still gets its own `DispatchRound` with zero candidates, which expires every cycle without acceptance, a known gap flagged above, not solved here.

This computation runs once when an order is created, and again whenever a round expires with no acceptance (only for that round's still-open segments, already-filled segments elsewhere in the same order are left alone).

## Behavior

### `app/core/dispatch.py`

- `compute_and_broadcast_rounds(order_id)`: implements the grouping algorithm for an order's currently-open segments, creates the round(s) and candidates, calls `send_job_offer_notification(...)` once per candidate per round.
- `send_job_offer_notification(electrician_id, round_id, segment_names, total_amount)`: stub, logs the call clearly. A future spec replaces this with real FCM sending, using the same function signature.

### Background scheduler

- On app startup, start an APScheduler job running every 1 minute.
- Each run: find all `DispatchRound`s where `status = "open"` AND `expires_at < now()`. For each, mark it `"expired"`, then re-run `compute_and_broadcast_rounds` for that order's still-open segments.
- Guard against double-processing the same round if the scheduler somehow overlaps runs, by re-checking `status = "open"` before acting.

### `POST /orders` (extends the existing endpoint)

- After creating the order and its segments, call `compute_and_broadcast_rounds(order.id)` to kick off the first round(s).

### `POST /jobs/rounds/{round_id}/accept`

- Protected by `get_current_electrician`.
- If the round doesn't exist, 404. If its `status` isn't `"open"`, 409 (already filled or expired).
- If the caller isn't a listed candidate for this round (no `DispatchRoundCandidate` row), 403.
- Atomically (re-checking `status = "open"` at write time, not just read time): set the round's `status = "filled"`, assign every segment in `segment_ids` to the caller (`electrician_id`, `status = "assigned"`), recompute `Order.status`.
- If the round was already filled by someone else by the time this runs (a race), return 409, don't double-assign.
- Return the assigned segments and their combined amount.

## Non-functional requirements

- No token is ever logged.
- The grouping algorithm only ever operates on currently-open segments, never re-offers an already-assigned one.
- Fully testable without any real push notification service, verify through the stub's log output and direct API calls.

## Acceptance criteria

- [ ] Creating an order where one electrician's skills cover every segment results in exactly one `DispatchRound` containing all segments, with that electrician (and any others who also fully qualify) as candidates.
- [ ] Creating an order where no single electrician covers everything, but two separate electricians together do, results in two independent `DispatchRound`s, each with the correct respective candidates.
- [ ] Accepting a round assigns exactly its segments to the caller, and correctly updates `Order.status`.
- [ ] An electrician who is not a candidate for a round gets 403 attempting to accept it.
- [ ] Two candidates for the same round, both attempting to accept at nearly the same time, result in only one success, the other gets 409.
- [ ] Manually setting a round's `expires_at` to the past and waiting for the scheduler's next run correctly marks it expired and creates the next, smaller-grouped round(s) for its still-open segments.
- [ ] A segment with zero matching electricians still gets a `DispatchRound` created (zero candidates), which expires every cycle without ever being accepted, confirmed via logs, expected, not a crash.
- [ ] The stub notification function is called exactly once per candidate per round, confirmed via log output.