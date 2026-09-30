# Dispatch System: Sequential Dispatch with Smart Grouping

This document describes the dispatch system implementation as specified in `specs/07-sequential-dispatch-smart-grouping.md`. The system automatically assigns orders to electricians using smart grouping and sequential queuing with workload-aware candidate ordering and cascade timeouts.

## System Overview

The dispatch system consists of six core components:

1. **Smart Grouping:** Find the segment grouping that minimizes total electricians needed for an order
2. **Sequential Queuing:** Offer jobs one electrician at a time per dispatch round, not broadcast
3. **Workload-Aware Ordering:** Queue candidates by current pending workload (fewest jobs first) for even distribution
4. **Cascade on Timeout:** After 1 minute with no response, automatically promote the next candidate
5. **Parallel Multi-Segment:** Independent segment groups (different specializations) queue simultaneously
6. **Full Visibility:** Electricians see complete offer history with all statuses

---

## Segment vs Multi-Segment Orders

### What is a Segment?

A **segment** is a single unit of work tied to ONE specialization. When a customer places an order with multiple services, each service/repair becomes one segment.

**Example 1: Single Segment (Simple Order)**

```
Customer orders: "Fix my AC"
→ System creates 1 segment
   - Segment 1: specialization = "ac_repair", amount = ₹1000

Dispatch result: 1 electrician needed
```

**Example 2: Four Segments (Complex Order)**

```
Customer orders: "Fix my AC, repair my fan, install new AC unit, install fan"
→ System creates 4 segments
   - Segment 1: "ac_repair" (repair issue), ₹800
   - Segment 2: "fan_repair" (repair issue), ₹500
   - Segment 3: "ac_install" (service item), ₹2000
   - Segment 4: "fan_install" (service item), ₹1000
   
Total order value: ₹4300

Dispatch result: 1, 2, 3, or 4 electricians depending on who has skills
```

**Example 3: Two Segments (Same Specialization)**

```
Customer orders: "Fix two AC units"
→ System creates 2 segments
   - Segment 1: "ac_repair", ₹800
   - Segment 2: "ac_repair", ₹800
   
→ System bundles them together (same specialization)
   - Dispatch Round: [Segment 1 + Segment 2]
   - Offered to electricians with "ac_repair" skill

Dispatch result: 1 electrician can do both, or fallback to 2 if needed
```

---

## Smart Grouping Algorithm

### Goal

Find the way to split an order's segments such that the **total number of electricians needed is minimized**, while also **reducing customer coordination burden**.

### How It Works

Given segments [A, B, C, D] with 4 different specializations, the system:

1. Generates all possible groupings (ways to partition segments)
2. For each grouping, checks if it's "feasible" (each group has electricians who can do all)
3. Counts electricians needed for each feasible grouping
4. Picks the one with fewest electricians
5. **Tiebreaker (if multiple groupings tie on electrician count):** Prefer equal segment distribution across rounds
   - Example: If both `[A+B+C]+[D]` and `[A+C]+[B+D]` need 2 electricians, pick `[A+C]+[B+D]` (2+2 segments) over `[A+B+C]+[D]` (3+1 segments)

### Real-World Example: The 4-Service Order

**Order:** [AC repair, Fan repair, AC install, Fan install]

**Available Electricians:**
- E1: skills [ac_repair, ac_install]
- E2: skills [fan_repair, fan_install]
- E3: skills [ac_repair, ac_install, fan_repair] (jack of all trades)
- E4: skills [fan_repair] (specialist)

**Possible Groupings:**

| Grouping | Groups | Electrician Assignment | Total Count | Feasible? |
|----------|--------|------------------------|-------------|-----------|
| [A+B+C+D] | 1 | No one has all 4 | N/A | ❌ |
| [A+B+C] + [D] | 2 | E3 for ABC, E2/E4 for D | 2 | ✅ |
| [A+B] + [C+D] | 2 | E3 for AB, no one for CD | N/A | ❌ |
| [A+C] + [B+D] | 2 | E1 for AC, E2/E4 for BD | 2 | ✅ |
| [A+D] + [B+C] | 2 | E1 for AD? (E1 has A,D? no, E1 has ac_repair+ac_install) | N/A | ❌ |
| [A] + [B] + [C] + [D] | 4 | E1 for A, E3/E2/E4 for B, E1 for C, E2/E4 for D | 2-3 | ✅ |

**Valid groupings:** [A+B+C]+[D] and [A+C]+[B+D] both result in 2 electricians

**Tiebreaker (when multiple groupings have same electrician count):** Prefer equal segment distribution.
- [A+B+C]+[D] = 3 segments + 1 segment (unequal)
- [A+C]+[B+D] = 2 segments + 2 segments (equal) ✓

**System picks:** [A+C]+[B+D]
- Round 1: [AC repair, AC install] → offered to E1 first
- Round 2: [Fan repair, Fan install] → offered to E2 first

**Customer deals with:** Min 2 electricians (optimal, balanced workload)

---

## Workload-Aware Candidate Ordering

When queuing candidates for a dispatch round, they are ordered by current pending workload, not random registration order.

**How it works:**
```
Round created for [AC repair, AC install]
Matching electricians: E1, E3, E5

Current workload:
  E1: 3 pending jobs (assigned, not yet completed)
  E3: 0 pending jobs (free/available)
  E5: 1 pending job

Sort by ascending workload:
→ E3 (0 jobs) at position 0 ← offered first
→ E5 (1 job) at position 1
→ E1 (3 jobs) at position 2
```

**Benefits:**
- Prevents overloading one electrician while others are free
- Ensures more balanced work distribution
- Reduces cascade timeouts from overburdened electricians
- Improves customer coordination (more likely all jobs accepted on first or second offer)

---

## Sequential Queuing: The 1-Minute Cascade

When a dispatch round is created, all matching electricians form a queue ordered by workload. Only the electrician at position 0 receives an offer at any given time.

**How it works:**
```
Round created for [AC repair, AC install]
→ Order by workload, create queue: [E3(pos 0, free), E5(pos 1), E1(pos 2)]
→ T=0s: Notify ONLY E3 (position 0)
→ T=0 to T=60s: Wait for E3's response (1-minute window)
→ T=45s: E3 accepts ✅ → Round filled, dispatch complete
    OR
→ T=65s: E3 times out → Mark E3 "timeout"
         → Promote E5 to position 0
         → Notify E5 (new 1-minute timer)
         → E5 accepts or times out
         → Continue cascade until someone accepts
```

**Why 1-minute timeout?**
- Provides a clear, bounded response window for electricians
- Prevents customer from waiting indefinitely for first offer
- System automatically escalates without requiring manual intervention
- Balance between responsiveness and giving electricians time to review offer

---

## Multi-Segment Order: Parallel Independent Groups

### Scenario: Order with 2 Independent Specialization Groups

**Order:** [AC repair, AC install] (Group A: 2 ac_* segments) + [Fan repair, Fan install] (Group B: 2 fan_* segments)

**Smart Grouping:** 
- [AC repair + AC install] → 1 round
- [Fan repair + Fan install] → 1 round
- Total: 2 rounds, likely 2 electricians

**Sequential Dispatch (Parallel Execution):**

```
T=0s:
  Round A: E1 (ac_repair+ac_install) offered → started 1-min timer
  Round B: E2 (fan_repair+fan_install) offered → started 1-min timer
  
  Both rounds are simultaneously waiting for responses!

T=30s:
  Round A: E1 accepts ✅ → Round A done
  Round B: E2 still waiting

T=65s:
  Round B: E2 times out → Promote E4 to position 0
           E4 offered → started 1-min timer

T=90s:
  Round B: E4 accepts ✅ → Round B done

Result: Order completed, served by E1 (Round A) + E4 (Round B)
Customer coordination: 2 electricians
```

**Key point:** Round A didn't wait for Round B. Both queued independently, in parallel.

---

## Detailed Scenarios: Best, Worst, and Realistic Cases

### Best Case: One Electrician Handles Everything

```
Order: [AC repair, AC install, Fan repair, Fan install]

Electrician E_unicorn has: [ac_repair, ac_install, fan_repair, fan_install]

Smart Grouping Result:
  - All 4 segments can be grouped together
  - 1 electrician needed
  
Dispatch:
  Round 1: [seg1, seg2, seg3, seg4] → E_unicorn at position 0
  T=30s: E_unicorn accepts
  
Customer deals with: 1 electrician ✅ (ideal)
```

---

### Realistic Case: Two Electrician Split (Different Specializations)

```
Order: [AC repair, AC install] + [Fan repair, Fan install]
       (2 ac_* + 2 fan_*)

Electricians:
- E1: [ac_repair, ac_install]
- E2: [fan_repair, fan_install]
- E3: [ac_repair, fan_repair] (partial skills)

Smart Grouping:
  Option A: [AC repair + AC install] + [Fan repair + Fan install]
    → E1 can do A, E2 can do B → 2 electricians ✓
  Option B: Try grouping [AC repair + AC install + Fan repair] + [Fan install]
    → E1+E3 together? No, each round needs ONE electrician who has ALL
    → E3 covers 2 of 3 in first group, but not all → not feasible
  
  Pick Option A: 2 electricians needed (optimal)

Dispatch:
  Round 1: [AC repair, AC install]
    Queue: [E1(pos 0), E3(pos 1)]
    T=0: E1 offered
    
  Round 2: [Fan repair, Fan install]
    Queue: [E2(pos 0)]
    T=0: E2 offered (parallel with Round 1)
    
Timeline:
  T=30s: E1 accepts Round 1 ✅
  T=30s: E2 accepts Round 2 ✅
  
Customer deals with: 2 electricians (optimal for this skill distribution)
```

---

### Worst Case: One Electrician Per Segment

```
Order: [AC repair, Fan repair, Plumbing repair, Electrical repair]

Electricians:
- E1: [ac_repair] only
- E2: [fan_repair] only
- E3: [plumbing_repair] only
- E4: [electrical_repair] only

Smart Grouping:
  - No 2-segment grouping has a match (no electrician has multiple skills)
  - Falls back to 1 segment each
  
Dispatch:
  Round 1: [AC repair] → E1
  Round 2: [Fan repair] → E2
  Round 3: [Plumbing repair] → E3
  Round 4: [Electrical repair] → E4
  
Customer deals with: 4 electricians (unavoidable, no overlap in skills)
```

---

### Complex Case: Cascade Timeout & Promotion

Real-world scenario: Customer orders AC repair + AC install + general wire repair (3 specializations, 2 independent groups).

```
Order: [AC repair (₹800), AC install (₹2000), General repair (₹300)]

Electricians:
- E1: [ac_repair, ac_install] — AC specialist
- E2: [ac_repair, ac_install] — AC specialist
- E3: [general_repair] — General handyman

Workload:
- E1: 3 pending jobs
- E2: 0 pending jobs (free)
- E3: 1 pending job

Smart Grouping:
  Round 1: [AC repair + AC install] → E1, E2 qualify
  Round 2: [General repair] → E3 qualifies
  Total: 2 rounds, minimum 2 electricians

Candidate Queue (ordered by workload):

Round 1:
  Queue: [E2(pos 0, 0 jobs), E1(pos 1, 3 jobs)]

Round 2:
  Queue: [E3(pos 0, 1 job)]

Dispatch (T=0s, both rounds start in parallel):

Round 1: [AC repair + AC install]
  T=0s: E2 offered (status: currently_offered, 1-minute timer starts)
        → Notification sent to E2
        
Round 2: [General repair]
  T=0s: E3 offered (status: currently_offered, 1-minute timer starts)
        → Notification sent to E3

Timeline:

  T=35s: E2 accepts Round 1 ✅
         → E2 status: accepted
         → Segments assigned to E2
         → Round 1 complete
         
  T=60s: E3 still hasn't responded to Round 2 → TIMEOUT
         → E3 status: timeout, response_at = now
         → No more candidates in Round 2 queue
         → Round expires, re-trigger dispatch for remaining open segments

Result: 
  - Round 1 assigned to E2 (accepted on first offer, benefited from workload-aware ordering)
  - Round 2 cascaded once (E3 timed out)
  - E1 was never offered because E2 (with 0 jobs) was at position 0 and accepted
  - Customer deals with E2 for AC work; General repair needs re-dispatch

Job History for E1: empty (never offered, workload too high)
Job History for E2: status = "accepted" (Round 1)
Job History for E3: status = "timeout" (Round 2)
```

**Key Benefit of Workload-Aware Ordering:**
- E2 (free) was offered first, not E1 (overbooked with 3 jobs)
- Result: Faster acceptance, no unnecessary cascade, better electrician utilization

---

## Queue Position & Status Tracking

### What Each Status Means

| Status | Meaning | Next Action |
|--------|---------|------------|
| `pending_queue` | Waiting their turn (someone ahead still being offered) | Wait for cascade |
| `currently_offered` | Active offer, 1-min response window open | Accept, reject, or timeout after 60s |
| `accepted` | Successfully accepted the job | Segments assigned, round complete |
| `rejected` | Explicitly declined (via reject endpoint) | Next candidate promoted |
| `timeout` | Didn't respond within 1 minute | Next candidate promoted |
| `missed` | (Future) Marked unavailable by electrician | Next candidate promoted |

### Example: Job History for Electrician

```
GET /jobs/me/offers
→ Returns all offers electrician has received:

[
  {
    id: 1,
    round_id: 101,
    order_id: 5001,
    status: "accepted",
    queue_position: 0,
    offered_at: "2026-09-24T10:00:00Z",
    response_at: "2026-09-24T10:02:30Z",
    segments: [
      { specialization: "ac_repair", amount: 800 },
      { specialization: "ac_install", amount: 2000 }
    ],
    total_amount: 2800,
    customer_name: "Rajesh Patel"
  },
  {
    id: 2,
    round_id: 102,
    order_id: 5002,
    status: "timeout",
    queue_position: 0,
    offered_at: "2026-09-24T10:05:00Z",
    response_at: "2026-09-24T10:06:01Z",
    segments: [
      { specialization: "fan_repair", amount: 500 }
    ],
    total_amount: 500,
    customer_name: "Priya Singh"
  },
  {
    id: 3,
    round_id: 103,
    order_id: 5003,
    status: "pending_queue",
    queue_position: 1,
    offered_at: null,
    response_at: null,
    segments: [
      { specialization: "plumbing_repair", amount: 1200 }
    ],
    total_amount: 1200,
    customer_name: "Vikram Gupta"
  }
]
```

**Notable fields:**
- `offered_at`: When the offer was sent (1-minute timeout clock starts from here).
- `response_at`: When they actually accepted/rejected/timed out (60 seconds after offered_at = timeout).
- `queue_position`: Their position in the queue (0 = currently offered, 1+ = waiting their turn)

---

## Parallel Multi-Segment Processing: Technical Detail

### When Rounds Process in Parallel

**Parallel:** Multiple rounds for the same order with DIFFERENT specializations

```
Order with [AC segments] + [Fan segments] + [Plumbing segments]
→ Round A (AC), Round B (Fan), Round C (Plumbing) all created
→ All three queues process simultaneously
→ No waiting for A to finish before B starts
```

**Sequential (within a group):** Multiple segments with SAME specialization

```
Order with [AC repair 1, AC repair 2, AC install]
→ Smart grouping creates:
   - Round A: [AC repair 1 + AC repair 2 + AC install] (if 1 E has all)
   - OR splits if needed

If split into separate rounds (rare):
   - Round A1: [AC repair 1]
   - Round A2: [AC repair 2]
   - Round A3: [AC install]
→ These still queue independently, but may have same electricians in queues
→ No blocking between them (both A2 and A3 can be offered while A1 awaits)
```

---

## Future Optimizations (Roadmap)

The following optimizations are designed but not yet implemented. They will be added in future phases:

### 2. Dynamic Timeout Based on Offer Complexity & Responsiveness
Timeout duration scales with offer complexity (segment count) and electrician's historical response time.

**Formula:**
```
timeout = BASE_60s + (segment_count - 1)*10s + electrician_adjustment

Electrician categories (based on historical avg response time):
  Fast (≤20s): -10 seconds
  Normal (21-45s): 0 seconds
  Slow (≥46s): +15 seconds

Final timeout: clamped to [50s, 120s]
```

**Benefits:**
- Small offers (1 segment) get shorter timeout (faster cascade)
- Complex offers (3+ segments) get longer timeout (more review time)
- Slow responders get more time (reduce false timeouts)
- Fast responders get tighter windows (they're responsive anyway)

**Implementation requirement:** Need 10-20 historical offers per electrician to establish baseline response time.

### 3. Electrician Preference & Availability Slots
Allow electricians to configure:
- Maximum concurrent jobs (e.g., "only 2 at a time")
- Unavailable time windows (e.g., lunch breaks, scheduled maintenance)
- Preferred specializations or job categories
- Preferred job sizes (small, medium, large)

**Impact:** Reduces rejections, more accurate queue building, better retention.

### 4. Segment Bundling by Complexity/Effort
Current: Tiebreaker prefers equal segment *count* (2+2 over 3+1).
Future: Weight by estimated *effort* (duration, complexity, travel time).

**Example:** If [AC repair (30min) + AC install (2hr)] vs [AC repair (30min) + Fan repair (20min)] are tied on electrician count, choose by work balance rather than just count.

**Impact:** Electricians don't get disproportionately long/short jobs; better effort parity.

### 5. Surge Incentives on Cascade Exhaustion
When a round cascades 2+ times with timeouts, auto-offer:
- 5-10% commission boost on that round
- Or higher priority for next offer

**Impact:** Prevents deadlocked orders; creates natural incentive mechanism during high-load periods.

### 6. ML-Based Acceptance Prediction
Train model: *"Will this electrician likely accept this offer?"* 

Input: offer attributes (size, specialization, amount), electrician history (profile, recent activity, response patterns), time of day.

Output: Acceptance probability (0-1).

Use score to reorder queue beyond just workload, placing highest-probability candidates first.

**Impact:** Dramatically fewer cascades; faster fulfillment; better matching.

---

## Implementation Notes

1. **Smart Grouping** runs once when order is created
2. **Cascade Timeout Check** runs every 30 seconds (background job)
3. **Parallel Processing:** Multiple rounds have independent dynamic timers, all running concurrently
4. **Atomicity:** Acceptance and rejection are atomic; no double-bookings even with race conditions
5. **Backwards Compat:** Existing `/accept` endpoint updated to check `currently_offered` status; existing `/reject` stub becomes real endpoint
6. **Notifications:** Same `send_job_offer_notification()` stub, signature may expand to include queue position, timeout duration, and total queue length
