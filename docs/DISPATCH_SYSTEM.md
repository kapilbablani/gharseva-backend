# Dispatch System: Automatic Order-to-Electrician Assignment

The system manages order-to-electrician assignment via an automatic 5-phase process in `app/core/dispatch.py`. This happens immediately when a customer creates an order.

---

## Phase 1: Segment Creation

When an order is created, each repair issue and service item becomes one **segment**:
- Each repair issue → one segment with specialization from that issue
- Each service item → one segment with specialization from that item
- Example: Order with 2 repairs + 1 service item = 3 segments

Segments store:
- `order_id` — which order they belong to
- `specialization` — skill required (e.g., `"general_repair"`, `"ac_installation"`)
- `amount` — price of this segment
- `status` — `"open"` initially (becomes `"assigned"` when electrician accepts)
- `electrician_id` — null initially (set when assigned)

---

## Phase 2: Grouping Algorithm

`_find_best_grouping()` looks at all open segments for an order and finds the **largest group** that a single electrician can handle.

**Logic:**
1. Start with all open segments
2. Try to find an electrician whose skills cover all of them
3. If found, use that group
4. If not found, try smaller groups (drop one segment, try again)
5. Return the largest matching group (or `None` if no single electrician can handle any subset)

**Why largest-first:** Minimizes the number of electricians needed per order, reducing coordination overhead.

**Matching rule:** A segment matches an electrician if the segment's `specialization` exists in the electrician's skill rows. Pure string comparison, no hardcoded logic.

---

## Phase 3: Dispatch Round Creation

Once a grouping is found:

1. Create a **dispatch round** with the grouped segment IDs
   - `order_id` — which order
   - `segment_ids` — JSON array of the grouped segment IDs
   - `status` — `"open"` (waiting for acceptance)
   - `expires_at` — 15 minutes from now

2. Find all electricians whose skills cover **all** segments in the round
   - If electrician has `["general_repair", "fan_installation"]` and round needs both, they qualify
   - If electrician only has `["general_repair"]`, they don't qualify

3. Create **dispatch round candidates** for each matching electrician
   - Store: `round_id`, `electrician_id`, `notified_at`

---

## Phase 4: Notification & Acceptance

**Notification (currently a logging stub):**
- `send_job_offer_notification()` logs: electrician ID, round ID, segment names, total amount
- Future: integrate push notifications

**Acceptance:**
- Electrician calls `POST /jobs/rounds/{round_id}/accept`
- The endpoint verifies:
  - Round exists and is `"open"`
  - Electrician is a candidate for this round
- If valid, **atomically**:
  - Mark round as `"filled"`
  - Assign all segments in the round to this electrician
  - Set segment status to `"assigned"`
- If another electrician accepted first (race condition), return 409 Conflict

---

## Phase 5: Repeat or Complete

After a round is accepted:

1. **Check for remaining open segments** in the order
   - If none, update order status to `"assigned"` — complete
   - If some remain, go back to Phase 2 with the new open segments

2. **Process repeats** until all segments are assigned or no electrician can handle any remaining group

3. **Order is `"assigned"`** once all segments are covered

---

## Example Workflow

**Order:** General repair (₹300) + AC repair (₹1000) + Fan installation (₹1000)

**Electricians:**
- Elec A: skills `["general_repair", "fan_installation"]`
- Elec B: skills `["ac_repair"]`

**Step 1 — Segments created:**
1. Segment 1: `general_repair`, ₹300
2. Segment 2: `ac_repair`, ₹1000
3. Segment 3: `fan_installation`, ₹1000

**Step 2 — Grouping:** Find largest group matching an electrician
- All 3 segments? No single electrician has all three
- Segments 1+3 (general + fan)? Elec A qualifies ✓
- Use this grouping

**Step 3 — Round created:**
- Round 1: `segment_ids=[1, 3]`, candidates: Elec A

**Step 4 — Elec A accepts:**
- Segments 1 & 3 marked `"assigned"` to Elec A

**Step 5 — Repeat:**
- Segment 2 still open
- Grouping: Segment 2 alone? Elec B qualifies ✓
- Round 2 created: `segment_ids=[2]`, candidates: Elec B
- Elec B accepts → Segment 2 assigned
- No open segments remain → Order status becomes `"assigned"`

**Final result:** 2 electricians, 2 rounds, order complete

---

## Key Design Properties

1. **Fairness** — First electrician to accept wins; no favoritism
2. **Atomicity** — Round acceptance is atomic; no double-assignments
3. **Genericity** — Specializations are plain strings; no hardcoded types
4. **Efficiency** — Algorithm prioritizes larger groups to reduce electrician count
5. **Extensibility** — New specializations can be added without code changes
