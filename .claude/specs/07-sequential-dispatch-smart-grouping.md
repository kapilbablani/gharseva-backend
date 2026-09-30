# Spec: Sequential Dispatch with Smart Grouping & Cascade Timeouts

## Scope

This spec replaces the broadcast-all-at-once dispatch model with a sequential, cascade-based system that:

1. **Smart Grouping:** Find the segment grouping that minimizes the total number of electricians needed for an order
2. **Sequential Queuing:** For each segment group (dispatch round), offer jobs one electrician at a time, not all at once
3. **Workload-Aware Ordering:** Queue candidates ordered by current pending workload (fewest pending jobs first), ensuring even job distribution across electricians
4. **Cascade on Timeout/Rejection:** If an electrician doesn't respond within 1 minute or explicitly rejects, automatically promote the next electrician in queue and send them the offer
5. **Parallel Multi-Segment:** Multiple independent segment groups (different specializations) process their sequential queues simultaneously
6. **Full Status Visibility:** Electricians see complete job offer history with all statuses (pending_queue, currently_offered, timeout, rejected, accepted, missed)

Real notification delivery remains stubbed; integration happens in a separate spec without changing this core logic.

This spec does NOT cover:
- Real push notification delivery (stub remains)
- Electrician availability/busy status tracking
- Customer communication about electrician assignment timeline
- Dynamic timeout based on offer complexity and responder speed (future optimization)
- Predictive acceptance modeling / ML-based queue reordering (future optimization)
- Segment bundling by complexity/effort (future optimization)
- Auto-incentive boost for cascaded rounds (future optimization)
- What happens if entire queue exhausted with no acceptance (round expires, re-dispatch triggered)

## Background

Current system broadcasts to all eligible electricians simultaneously, creating race conditions and giving customers no control over coordination. Proposed system offers jobs sequentially with fallback, reducing race conditions and ensuring customers deal with minimum electricians.

An order may split into multiple independent dispatch rounds (segment groups) if no single electrician can handle all. Each round has its own queue of candidates. Rounds with different specializations queue in parallel; rounds with same specialization in one group queue sequentially.

## Database

### `DispatchRoundCandidate` (Updated)

Add new fields to track queue state:

- `id` — integer, primary key, auto-increment
- `round_id` — integer, foreign key to `DispatchRound.id`
- `electrician_id` — string, foreign key to `User.id`
- `queue_position` — integer, position in queue (0 = currently offered, 1+ = pending). Unique per (round_id, queue_position)
- `status` — string: `"pending_queue"` | `"currently_offered"` | `"accepted"` | `"rejected"` | `"timeout"` | `"missed"`
  - `pending_queue`: Waiting their turn in queue
  - `currently_offered`: Notification sent, awaiting response (1-minute window)
  - `accepted`: Electrician accepted the job
  - `rejected`: Electrician explicitly declined (new endpoint)
  - `timeout`: Electrician didn't respond within 1 minute
  - `missed`: Electrician dismissed/marked unavailable (future UX feature, not in this spec)
- `offered_at` — datetime, when this electrician was transitioned to `currently_offered` (nullable until first offer)
- `response_at` — datetime, when they accepted/rejected (nullable until response)
- `created_at` — datetime, when candidate was first created (for queue ordering by pending workload)

### `DispatchRound` (Unchanged)

Same schema as before; no changes needed.

### `OrderSegment` (Unchanged)

Same schema; no changes needed.

## Smart Grouping Algorithm

Goal: Find the segment grouping that results in the fewest total electricians needed.

### Algorithm Steps

Given an order's currently-open segments:

1. **Generate all feasible groupings:**
   - A "feasible grouping" is a partition of open segments where each partition (group) has at least one electrician whose skills cover all segments in that group
   - For order with 4 segments [A, B, C, D], feasible groupings might include:
     - [A+B+C] + [D] (2 groups = 2+ electricians)
     - [A+B] + [C+D] (2 groups = 2+ electricians)
     - [A+B] + [C] + [D] (3 groups = 3+ electricians)
     - etc.

2. **Count electricians per grouping:**
   - For each feasible grouping, count the minimum electricians needed to cover all groups
   - Example: [A+B+C] + [D] needs min 2 electricians if E1 covers A+B+C and E2 covers D

3. **Select the grouping with minimum electrician count:**
   - If tied (multiple groupings need same number of electricians), prefer equal segment distribution
   - Example: If both `[A+B+C]+[D]` and `[A+C]+[B+D]` require 2 electricians, pick `[A+C]+[B+D]` (2+2 segments) over `[A+B+C]+[D]` (3+1 segments)
   - Rationale: Equal distribution balances workload across electricians and reduces coordination complexity

4. **Create one `DispatchRound` per group in the chosen grouping**

5. **Queue candidates for each round** (see "Queuing" section below)

6. **Send offer only to position-0 candidates** across all rounds (not all candidates)

### Example Grouping Decision

Order: [AC repair, Fan repair, AC install, Fan install]

Electricians:
- E1: [ac_repair, ac_install]
- E2: [fan_repair, fan_install]
- E3: [ac_repair, ac_install, fan_repair] (has 3)

Feasible groupings:
- [AC repair + AC install] + [Fan repair + Fan install] = 2 groups, min 2 electricians (E1 + E2) ✓
- [AC repair + AC install + Fan repair] + [Fan install] = 2 groups, min 2 electricians (E3 + E2) ✓
- [AC repair + Fan repair] + [AC install + Fan install] = 2 groups, no single electrician covers [AC repair + Fan repair] ✗
- All 4 together = 1 group, no single electrician covers all 4 ✗

Valid groupings: 2 feasible options, both result in 2 electricians
- Option 1: [AC repair + AC install] + [Fan repair + Fan install] = 2+2 segments (equal distribution) ✓
- Option 2: [AC repair + AC install + Fan repair] + [Fan install] = 3+1 segments (unequal distribution)

**Selection (tiebreaker—equal distribution):** [AC repair + AC install] + [Fan repair + Fan install]
- Reason: Both options need 2 electricians, but Option 1 has balanced segment counts (2+2 vs 3+1)
- Balanced distribution reduces workload variance and improves customer coordination

Result: 2 rounds (Round 1: AC services, Round 2: Fan services), total 2 electricians

## Queuing Mechanism

### Round Candidate Queue Creation

For each `DispatchRound` in the chosen grouping:

1. Find all electricians whose skills fully cover all segments in this round
2. **Order candidates by workload (ascending):**
   - Count each candidate's current pending jobs (segments in status `"assigned"` with `completed_at = NULL`)
   - Sort by pending job count: fewest pending first
   - Tiebreaker: use `created_at` (older registration first) for deterministic ordering
   - Rationale: Electricians with fewer pending jobs get offered first, ensuring even distribution
3. Create `DispatchRoundCandidate` rows:
   - First candidate: `queue_position = 0`, `status = "currently_offered"`, `offered_at = now()`
   - Rest: `queue_position = 1, 2, 3...`, `status = "pending_queue"`, `offered_at = NULL`
4. Call `send_job_offer_notification()` **only** for position-0 candidate

### Cascade Promotion (Timeout/Rejection)

When a `currently_offered` candidate times out or rejects:

1. Mark their `status = "timeout"` or `"rejected"`, set `response_at = now()`
2. Find the next candidate in queue (lowest `queue_position > 0` not in {accepted, rejected, timeout})
3. Decrement all higher positions to fill the gap, ensuring no gaps in queue_position
4. Promote the next candidate: `queue_position = 0`, `status = "currently_offered"`, `offered_at = now()`
5. Send notification to newly promoted candidate
6. If no candidates left (all timeout/rejected/accepted), mark round as `"expired"` and re-trigger dispatch

## Behavior

### `app/core/dispatch.py`

**`compute_and_broadcast_rounds(order_id)` (Updated):**
- Call `_find_smart_grouping(db, order_id)` instead of `_find_best_grouping()`
- Returns the best grouping (tuple of segment groups) that minimizes electricians
- For each group, create `DispatchRound` and queue candidates
- **Send notification only to position-0 candidates**
- Recursively process remaining segments (if any exist after all rounds created)

**`_find_smart_grouping(db, order_ids, segment_map) -> list[list[int]] | None` (New):**
- Generate all feasible groupings of open segments
- For each, count minimum electricians needed
- Return the grouping with lowest electrician count
- Handle edge cases: no feasible grouping (segment with zero matching electricians)

**`_find_all_feasible_groupings(db, segment_ids) -> list[list[list[int]]]` (New):**
- Generate all valid partitions of segment IDs
- Filter to only "feasible" ones (each group has at least one matching electrician)
- Return all candidates for `_find_smart_grouping` to choose from

**`_count_electricians_for_grouping(db, grouping: list[list[int]]) -> int` (New):**
- For each group in grouping, find matching electricians
- Count distinct electricians needed (min set cover)
- Return total count

### Background Scheduler (Updated)

**`process_cascade_timeouts()` (Enhanced from `process_expired_rounds()`):**
- Run every 30 seconds
- For each `DispatchRound` with `status = "open"`:
  - For each `DispatchRoundCandidate` with `status = "currently_offered"`:
    - If `now() - offered_at >= 60 seconds` (1-minute timeout):
      - Mark as `status = "timeout"`, set `response_at = now()`
      - Call `promote_next_candidate_in_queue(round_id)` (see below)
  - If round has no candidates in `{"pending_queue", "currently_offered"}`:
    - Mark round as `"expired"`
    - Re-trigger `compute_and_broadcast_rounds` for order's remaining open segments

**`promote_next_candidate_in_queue(round_id)` (New):**
- Get the candidate with next-lowest `queue_position` not in {accepted, rejected, timeout}
- If found:
  - Set their `queue_position = 0`, `status = "currently_offered"`, `offered_at = now()`
  - Decrement all other `queue_position` values to compact
  - Send notification
- If none found:
  - Round expires (no one left to try)

### `POST /orders` (Extends existing endpoint)

- After creating order and segments, call `compute_and_broadcast_rounds(order.id)` (same as before)

### `POST /jobs/rounds/{round_id}/accept` (Updated)

- Protected by `get_current_electrician`
- Validate round exists and `status = "open"`
- **NEW:** Validate caller is a candidate with `status = "currently_offered"` (not `"pending_queue"`)
- Atomically:
  - Set round `status = "filled"`
  - Set candidate `status = "accepted"`, `response_at = now()`
  - Assign all segments to electrician, status `"assigned"`
  - Recompute `Order.status`
- If round already filled by another electrician, return 409
- Return assigned segments and amount

### `POST /jobs/rounds/{round_id}/reject` (New)

- Protected by `get_current_electrician`
- Validate round exists and `status = "open"`
- Validate caller is a candidate with `status = "currently_offered"`
- Set candidate `status = "rejected"`, `response_at = now()`
- Call `promote_next_candidate_in_queue(round_id)` to auto-offer to next electrician
- Return success (or promotion details)

### `GET /jobs/me/offers` (New)

- Protected by `get_current_electrician`
- List all `DispatchRoundCandidate` entries for this electrician
- Return:
  - `round_id`, `status`, `queue_position`, `offered_at`, `response_at`
  - Segment details (specializations, amount)
  - Order customer info
  - Order ID
- Sort by `offered_at` descending (most recent first)
- Optionally filter by status (e.g., `?status=currently_offered` to see only active offers)

## Non-functional Requirements

- No token is ever logged
- Smart grouping algorithm only operates on open segments, never re-offers assigned ones
- Cascade promotions happen atomically; no race condition between timeout and manual rejection
- Notification function signature may expand (e.g., `queue_position`, `total_in_queue`), but still stubbed
- All status values are visible in job history for electrician transparency

## Acceptance Criteria

- [ ] Creating an order where one electrician covers all segments results in one `DispatchRound`, one `DispatchRoundCandidate` at position 0 with status `currently_offered`, rest (if any) at positions 1+ with status `pending_queue`
- [ ] Creating an order with 4 segments and multiple feasible groupings (e.g., 3+1 vs 2+2) selects the grouping that minimizes total electricians needed
- [ ] When multiple groupings tie on electrician count (e.g., both [A+B+C]+[D] and [A+C]+[B+D] need 2 electricians), system picks the one with equal segment distribution ([A+C]+[B+D] preferred over [A+B+C]+[D])
- [ ] Candidates are ordered by current pending workload (ascending): electrician with fewest assigned jobs appears at position 0
- [ ] Workload-aware ordering tiebreaker: when two electricians have same pending job count, use `created_at` (older registration first)
- [ ] Only position-0 candidate receives initial notification, not all candidates
- [ ] A candidate at position 0 who doesn't respond within 60 seconds is marked `timeout`, and position-1 candidate is promoted to position-0 with status `currently_offered` and receives notification
- [ ] A currently-offered electrician can accept the job via `POST .../accept`, marking status `accepted` and assigning segments
- [ ] A currently-offered electrician can reject the job via `POST .../reject`, marking status `rejected` and promoting next candidate
- [ ] `GET /jobs/me/offers` returns all candidates for this electrician with all statuses (pending_queue, currently_offered, timeout, rejected, accepted) and complete details
- [ ] Multiple rounds for the same order (different segment groups) process in parallel: both can have position-0 offers at the same time
- [ ] Atomicity: two candidates accepting at nearly the same time results in only one assignment, the other stays pending/promoted
- [ ] After all candidates in a round's queue are exhausted (all timeout/rejected/accepted), round expires and dispatch re-triggers for remaining open segments
- [ ] Manual testing: verify smart grouping picks 2+2 over 3+1 when both result in same electrician count (equal segment distribution tiebreaker)
- [ ] Manual testing: verify workload-aware ordering places electrician with 0 pending jobs before one with 3 pending jobs, regardless of skill registration order

