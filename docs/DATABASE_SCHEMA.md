# GharSeva Database Schema

Last Updated: 2026-09-23 (After Phase 4: Full Generalization)

This document describes the complete database schema for the GharSeva backend, including all tables, columns, relationships, and sample data.

---

## Table Overview

| Table | Purpose |
|-------|---------|
| `users` | Customer and electrician profiles, synced with Cognito |
| `repair_issues` | Pre-defined repair categories with per-item pricing and specialization |
| `service_items` | Pre-defined services with fixed pricing and specialization |
| `orders` | Customer orders, containing selected repair issues and service items |
| `order_segments` | Segments of orders, grouped by specialization, with individual amounts |
| `electrician_skills` | Electrician qualifications (which repairs/services they can perform) |
| `dispatch_rounds` | Active or completed job offer rounds to electrician groups |
| `dispatch_round_candidates` | Electricians nominated for a specific dispatch round |

---

## Table Schemas & Sample Data

### 1. `users` Table

**Purpose:** Store customer and electrician profiles, synced from AWS Cognito

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | String | NO | PRIMARY KEY | Cognito `sub` claim, globally unique user identifier |
| `email` | String | YES | | User's email from Cognito |
| `phone_number` | String | YES | | User's phone number (optional) |
| `role` | String | NO | | User's role: `"customer"` or `"electrician"` |
| `created_at` | DateTime | NO | DEFAULT NOW | When the user profile was created locally |

**Sample Data:**

| id | email | phone_number | role | created_at |
|----|-------|--------------|------|------------|
| customer1 | alice@example.com | 9876543210 | customer | 2026-09-20 10:15:00 |
| customer2 | bob@example.com | 9876543211 | customer | 2026-09-21 14:30:00 |
| elec1 | priya@example.com | 9876543212 | electrician | 2026-09-19 08:00:00 |
| elec2 | rahul@example.com | 9876543213 | electrician | 2026-09-19 09:00:00 |
| elec3 | geeta@example.com | 9876543214 | electrician | 2026-09-22 11:00:00 |

---

### 2. `repair_issues` Table

**Purpose:** Pre-defined repair work categories with per-item pricing and specialization

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique repair issue ID |
| `name` | String | NO | | Name of the repair (e.g., "General repair") |
| `category` | String | NO | | Professional category (currently `"electrician"`) |
| `price` | Integer | NO | | Fixed price in rupees for this repair |
| `specialization` | String | NO | | Skill type (plain string, e.g., `"general_repair"`, `"ac_repair"`, `"refrigerator_repair"`) |
| `active` | Boolean | NO | DEFAULT TRUE | Whether this repair is available for ordering |

**Sample Data:**

| id | name | category | price | specialization | active |
|----|------|----------|-------|-----------------|--------|
| 1 | Fan/Light/Socket/SwitchBoard repair | electrician | 300 | general_repair | true |
| 2 | AC repair | electrician | 1000 | ac_repair | true |
| 3 | Refrigerator repair | electrician | 500 | refrigerator_repair | true |
| 4 | Mixer grinder repair | electrician | 500 | mixer_grinder_repair | true |

---

### 3. `service_items` Table

**Purpose:** Pre-defined services with fixed pricing and specialization

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique service item ID |
| `name` | String | NO | | Name of the service (e.g., "Fan installation") |
| `price` | Integer | NO | | Fixed price in rupees for this service |
| `category` | String | NO | | Professional category (currently `"electrician"`) |
| `specialization` | String | NO | | Unique specialization slug for this service |
| `active` | Boolean | NO | DEFAULT TRUE | Whether this service is available for ordering |

**Sample Data:**

| id | name | price | category | specialization | active |
|----|------|-------|----------|-----------------|--------|
| 1 | Fan installation | 1000 | electrician | fan_installation | true |
| 2 | AC installation | 4000 | electrician | ac_installation | true |
| 3 | AC gas filling | 5000 | electrician | ac_gas_filling | true |
| 4 | Switchboard installation | 800 | electrician | switchboard_installation | true |

---

### 4. `orders` Table

**Purpose:** Store customer orders with selected repair issues and service items

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique order ID |
| `customer_id` | String | NO | FK → `users.id` | Customer who placed the order |
| `repair_issue_ids` | JSON | NO | DEFAULT [] | Array of selected `repair_issues.id` |
| `service_item_ids` | JSON | NO | DEFAULT [] | Array of selected `service_items.id` |
| `total_amount` | Integer | NO | | Total price (sum of all selected items) |
| `status` | String | NO | DEFAULT "pending_assignment" | Order status: `"pending_assignment"` or `"assigned"` |
| `created_at` | DateTime | NO | DEFAULT NOW | When the order was placed |

**Sample Data:**

| id | customer_id | repair_issue_ids | service_item_ids | total_amount | status | created_at |
|----|-------------|------------------|------------------|--------------|--------|------------|
| 1 | customer1 | [1, 2] | [1] | 2300 | pending_assignment | 2026-09-22 10:00:00 |
| 2 | customer1 | [3] | [3] | 5500 | pending_assignment | 2026-09-22 11:30:00 |
| 3 | customer2 | [1] | [1, 2] | 5300 | assigned | 2026-09-21 15:00:00 |

**Breakdown:**
- Order 1: General repair (₹300) + AC repair (₹1000) + Fan installation (₹1000) = **₹2300**
- Order 2: Refrigerator repair (₹500) + AC gas filling (₹5000) = **₹5500**
- Order 3: General repair (₹300) + Fan installation (₹1000) + AC installation (₹4000) = **₹5300**

**Note:** JSON arrays stored as text, e.g., `[1, 2]` represents repair issue IDs 1 and 2 (from the 4-row catalog).

---

### 5. `order_segments` Table

**Purpose:** Break down orders into specialization-based segments, one per electrician assignment

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique segment ID |
| `order_id` | Integer | NO | FK → `orders.id` | Which order this segment belongs to |
| `specialization` | String | NO | | Segment specialization (plain string, e.g., `"general_repair"`, `"ac_repair"`, `"fan_installation"`) |
| `repair_issue_id` | Integer | YES | FK → `repair_issues.id` | Set only for repair issue segments (for traceability/context). Due to 1:1 mapping between repair_issue_id and specialization, repair segments always have this value. |
| `service_item_id` | Integer | YES | FK → `service_items.id` | Set only for service item segments (for traceability/context). Mutually exclusive with repair_issue_id. |
| `amount` | Integer | NO | | Price for this segment (sum of items in the group) |
| `status` | String | NO | DEFAULT "open" | Segment status: `"open"` or `"assigned"` |
| `electrician_id` | String | YES | FK → `users.id` | Electrician assigned to this segment (null if open) |
| `created_at` | DateTime | NO | DEFAULT NOW | When the segment was created |

**Sample Data:**

| id | order_id | specialization | repair_issue_id | service_item_id | amount | status | electrician_id | created_at |
|----|----------|-----------------|-----------------|-----------------|--------|--------|----------------|------------|
| 1 | 1 | general_repair | 1 | NULL | 300 | assigned | elec1 | 2026-09-22 10:05:00 |
| 2 | 1 | fan_installation | NULL | 1 | 1000 | assigned | elec1 | 2026-09-22 10:05:00 |
| 3 | 2 | ac_repair | 2 | NULL | 1000 | open | NULL | 2026-09-22 11:35:00 |
| 4 | 2 | ac_gas_filling | NULL | 3 | 5000 | open | NULL | 2026-09-22 11:35:00 |
| 5 | 3 | general_repair | 1 | NULL | 300 | assigned | elec1 | 2026-09-21 15:10:00 |
| 6 | 3 | fan_installation | NULL | 1 | 1000 | assigned | elec1 | 2026-09-21 15:10:00 |
| 7 | 3 | ac_installation | NULL | 2 | 4000 | assigned | elec2 | 2026-09-21 16:00:00 |

**Segment Grouping Logic:**
- **Repair issue segments:** One segment per distinct repair_issue_id, with repair_issue_id always populated, service_item_id always NULL
  - Example: Repair issue 1 (general_repair, ₹300) → Segment with repair_issue_id=1, amount=300
- **Service item segments:** One segment per service_item_id, with service_item_id always populated, repair_issue_id always NULL
  - Example: Service item 1 (fan_installation, ₹1000) → Segment with service_item_id=1, amount=1000
- **Design:** 1:1 mapping between repair_issue_id and specialization ensures symmetry with service_item_id design
- **Example:** Order with repairs [1] + service items [1] = 2 segments (repair_issue_id=1 + service_item_id=1)

---

### 6. `electrician_skills` Table

**Purpose:** Define what specializations each electrician is qualified to perform

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique skill record ID |
| `electrician_id` | String | NO | FK → `users.id` | Electrician who has this skill |
| `specialization` | String | NO | | Plain string specialization (e.g., `"general_repair"`, `"ac_repair"`, `"fan_installation"`, `"refrigerator_repair"`) |
| `created_at` | DateTime | NO | DEFAULT NOW | When the skill was added |

**Sample Data:**

| id | electrician_id | specialization | created_at |
|----|----------------|-----------------|------------|
| 1 | elec1 | general_repair | 2026-09-19 08:30:00 |
| 2 | elec1 | fan_installation | 2026-09-19 08:30:00 |
| 3 | elec2 | general_repair | 2026-09-19 09:15:00 |
| 4 | elec2 | ac_installation | 2026-09-19 09:15:00 |
| 5 | elec3 | ac_repair | 2026-09-22 11:30:00 |
| 6 | elec3 | ac_gas_filling | 2026-09-22 11:30:00 |
| 7 | elec3 | refrigerator_repair | 2026-09-22 11:30:00 |

**Interpretation:**
- `elec1`: Can handle general_repair and fan_installation
- `elec2`: Can handle general_repair and ac_installation
- `elec3`: Can handle ac_repair, ac_gas_filling, and refrigerator_repair
- **Matching logic is now generic:** A segment matches an electrician if the segment's `specialization` value appears in that electrician's skill rows

---

### 7. `dispatch_rounds` Table

**Purpose:** Track active or completed job offer rounds to electrician candidates

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique dispatch round ID |
| `order_id` | Integer | NO | FK → `orders.id` | Which order this round serves |
| `segment_ids` | JSON | NO | | Array of `order_segments.id` being offered in this round |
| `status` | String | NO | DEFAULT "open" | Round status: `"open"` (waiting), `"filled"` (accepted), `"expired"` (timeout) |
| `created_at` | DateTime | NO | DEFAULT NOW | When the round was created |
| `expires_at` | DateTime | NO | | When this round expires (15 minutes after creation) |

**Sample Data:**

| id | order_id | segment_ids | status | created_at | expires_at |
|----|----------|-------------|--------|------------|------------|
| 1 | 1 | [1, 2] | filled | 2026-09-22 10:05:30 | 2026-09-22 10:20:30 |
| 2 | 2 | [3] | open | 2026-09-22 11:36:00 | 2026-09-22 11:51:00 |
| 3 | 2 | [4] | open | 2026-09-22 11:36:00 | 2026-09-22 11:51:00 |
| 4 | 3 | [5, 6] | filled | 2026-09-21 15:10:45 | 2026-09-21 15:25:45 |
| 5 | 3 | [7] | filled | 2026-09-21 16:00:00 | 2026-09-21 16:15:00 |

**Round Lifecycle:**
1. Created (status = "open") when order is placed or previous round expires
2. Filled (status = "filled") when an electrician accepts
3. Expired (status = "expired") after 15 minutes if no one accepts, then new rounds created for remaining segments

---

### 8. `dispatch_round_candidates` Table

**Purpose:** Track which electricians are nominated as candidates for each dispatch round

**Columns:**

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | Integer | NO | PRIMARY KEY, AUTOINCREMENT | Unique candidate record ID |
| `round_id` | Integer | NO | FK → `dispatch_rounds.id` | Which round this candidate is nominated for |
| `electrician_id` | String | NO | FK → `users.id` | Electrician being offered this round |
| `notified_at` | DateTime | NO | DEFAULT NOW | When this candidate was notified (for tracking duplicate notifications) |

**Sample Data:**

| id | round_id | electrician_id | notified_at |
|----|----------|----------------|------------|
| 1 | 1 | elec1 | 2026-09-22 10:05:35 |
| 2 | 2 | elec3 | 2026-09-22 11:36:05 |
| 3 | 3 | elec3 | 2026-09-22 11:36:05 |
| 4 | 4 | elec1 | 2026-09-21 15:11:00 |
| 5 | 5 | elec2 | 2026-09-21 16:00:05 |

**Matching Logic:**
- Round 1: Segments [1, 2] (general_repair + fan_installation) → Only elec1 qualifies (has both skills)
- Round 2: Segment [3] (ac_repair) → Only elec3 qualifies
- Round 3: Segment [4] (ac_gas_filling) → Only elec3 qualifies
- Round 4: Segments [5, 6] (general_repair + fan_installation) → Only elec1 qualifies (elec2 doesn't have fan_installation skill)
- Round 5: Segment [7] (ac_installation) → Only elec2 qualifies

---

## Key Relationships & Constraints

### Foreign Keys

```
users
  ├─ orders.customer_id → users.id
  ├─ orders.electrician_id → users.id (REMOVED in Phase 2)
  ├─ order_segments.electrician_id → users.id
  ├─ electrician_skills.electrician_id → users.id
  └─ dispatch_round_candidates.electrician_id → users.id

orders
  ├─ order_segments.order_id → orders.id
  └─ dispatch_rounds.order_id → orders.id

repair_issues
  └─ order_segments.repair_issue_id → repair_issues.id

service_items
  └─ order_segments.service_item_id → service_items.id
     (electrician_skills.service_item_id removed in Phase 4)

order_segments
  └─ dispatch_rounds.segment_ids → order_segments.id (as JSON array)

dispatch_rounds
  └─ dispatch_round_candidates.round_id → dispatch_rounds.id
```

### Key Design Patterns

**1. JSON Arrays in orders and dispatch_rounds:**
- `orders.repair_issue_ids`: Stores selected repair issue IDs
- `orders.service_item_ids`: Stores selected service item IDs
- `dispatch_rounds.segment_ids`: Stores segment IDs in a round

**2. Specialization-Based Segmentation (with Source Traceability):**
- **Repair issue segments:** One segment per `repair_issue_id`, with 1:1 mapping to specialization (e.g., repair_issue_id 1 → general_repair)
- **Service item segments:** One segment per `service_item_id`, each with unique specialization (fan_installation, ac_installation, etc.)
- **Symmetry:** Both repair and service segments carry their source ID (`repair_issue_id` or `service_item_id`) for traceability, mutually exclusive per segment
- **Matching:** Uses only `specialization` (string comparison), never the source IDs; source IDs exist for display/context only
- No hardcoded specialization types: system is fully generic

**3. Skill Matching (Generic):**
- Electricians have one row per specialization they can perform
- Matching: segment's `specialization` value must exist in electrician's skill `specialization` values (set membership)
- Works with any specialization string, no special cases or branching logic needed

**4. Dispatch Round Flow:**
- Order created → segments created → dispatch rounds created
- Rounds broadcast to matching electricians
- First to accept "wins" → round marked "filled" → remaining segments get new rounds

---

## Example: Complete Order Flow

**Scenario:** Customer alice places order: General repair (ID 1), AC repair (ID 2), Fan installation (service item ID 1), Refrigerator repair (ID 3)

**Cost breakdown:**
- General repair (ID 1): ₹300
- AC repair (ID 2): ₹1000
- Fan installation (service item 1): ₹1000
- Refrigerator repair (ID 3): ₹500
- **Total: ₹2800**

### 1. Order Created
```sql
INSERT INTO orders (customer_id, repair_issue_ids, service_item_ids, total_amount, status)
VALUES ('customer1', '[1, 2, 3]', '[1]', 2800, 'pending_assignment');
-- order_id = 1
```

### 2. Segments Created (One per Repair/Service Item)
Each repair issue gets one segment (with repair_issue_id), each service item gets one segment (with service_item_id).

```sql
INSERT INTO order_segments (order_id, specialization, repair_issue_id, service_item_id, amount, status)
VALUES 
  (1, 'general_repair', 1, NULL, 300, 'open'),        -- repair issue 1
  (1, 'ac_repair', 2, NULL, 1000, 'open'),            -- repair issue 2
  (1, 'refrigerator_repair', 3, NULL, 500, 'open'),   -- repair issue 3
  (1, 'fan_installation', NULL, 1, 1000, 'open');     -- service item 1
-- segment_ids = [1, 2, 3, 4]
```

### 3. Dispatch Rounds Created (Generic Matching)

**Round 1: General repair + Fan installation**
```sql
INSERT INTO dispatch_rounds (order_id, segment_ids, status, expires_at)
VALUES (1, '[1, 4]', 'open', '2026-09-22 10:20:30');
-- round_id = 1

-- Matching logic: elec1 has skills [general_repair, fan_installation]
-- Segments need: [general_repair, fan_installation]
-- Result: elec1 covers all required specializations ✓

INSERT INTO dispatch_round_candidates (round_id, electrician_id)
VALUES (1, 'elec1');
```

**Round 2: AC repair (no match initially, will be offered alone)**
```sql
INSERT INTO dispatch_rounds (order_id, segment_ids, status, expires_at)
VALUES (1, '[2]', 'open', '2026-09-22 10:20:30');
-- round_id = 2

-- Only elec3 has ac_repair skill
INSERT INTO dispatch_round_candidates (round_id, electrician_id)
VALUES (1, 'elec3');
```

**Round 3: Refrigerator repair**
```sql
INSERT INTO dispatch_rounds (order_id, segment_ids, status, expires_at)
VALUES (1, '[3]', 'open', '2026-09-22 10:20:30');
-- round_id = 3

-- Only elec3 has refrigerator_repair skill
INSERT INTO dispatch_round_candidates (round_id, electrician_id)
VALUES (1, 'elec3');
```

### 4. Electricians Accept Rounds

**elec1 accepts round 1:**
```sql
UPDATE dispatch_rounds SET status = 'filled' WHERE id = 1;
UPDATE order_segments SET electrician_id = 'elec1', status = 'assigned' WHERE id IN (1, 4);
-- elec1 now handles: general_repair (₹300) + fan_installation (₹1000) = ₹1300
```

**elec3 accepts round 2:**
```sql
UPDATE dispatch_rounds SET status = 'filled' WHERE id = 2;
UPDATE order_segments SET electrician_id = 'elec3', status = 'assigned' WHERE id = 2;
-- elec3 now handles: ac_repair (₹1000)
```

**elec3 accepts round 3:**
```sql
UPDATE dispatch_rounds SET status = 'filled' WHERE id = 3;
UPDATE order_segments SET electrician_id = 'elec3', status = 'assigned' WHERE id = 3;
-- elec3 now handles: ac_repair (₹1000) + refrigerator_repair (₹500) = ₹1500 total
```

### 5. Order Status Updated
```sql
UPDATE orders SET status = 'assigned' WHERE id = 1;
-- All segments assigned, order complete
```

**Result:** Order handled by 2 electricians:
- **elec1**: General repair + Fan installation (2 segments, ₹1300 total)
- **elec3**: AC repair + Refrigerator repair (2 segments, ₹1500 total)

---

## Migration Notes (Phase 1-4)

### Phase 1-3: Initial Schema & Specialization Support
- ✅ Moved to per-item pricing
- ✅ Added specialization columns to repair_issues and service_items
- ✅ Introduced segment-level assignments

### Phase 4: Full Generalization (Current)
**Generalization of Specialization System:**
- ✅ Removed hardcoded specialization values (`"general_repair"`, `"ac_repair"`, `"service_item"`)
- ✅ Renamed `ElectricianSkill.skill_type` → `ElectricianSkill.specialization`
- ✅ Removed `ElectricianSkill.service_item_id` (no longer needed)
- ✅ Renamed `OrderSegment.segment_type` → `OrderSegment.specialization`
- ✅ Added `OrderSegment.repair_issue_id` for symmetry with `service_item_id` (1:1 mapping, traceability only)
- ✅ Updated matching logic to generic string comparison (set membership)
- ✅ Simplified segment creation: one segment per repair_issue_id + one per service_item_id

**Catalog Update:**
- Changed from 5 repair issues (4 general + 1 AC) to 4 repair issues with 1:1 specialization mapping:
  1. General repair (₹300) → general_repair
  2. AC repair (₹1000) → ac_repair
  3. Refrigerator repair (₹500) → refrigerator_repair
  4. Mixer grinder repair (₹500) → mixer_grinder_repair

### Key Design Changes
| Aspect | Before | After |
|--------|--------|-------|
| Specialization storage | `skill_type`, `segment_type` (hardcoded) | `specialization` (any string) |
| Skill matching | Three-way branch (general_repair, ac_repair, service_item) | Generic set membership |
| Segment source tracking | `service_item_id` only | Both `repair_issue_id` AND `service_item_id` (symmetric, mutually exclusive) |
| Repair-to-specialization | Many-to-one (grouping) | One-to-one (1:1 mapping) |
| Segment creation | Hardcoded if/elif for each type | Dynamic: one per repair_issue_id + one per service_item_id |
| Catalog | Hardcoded 4+1 items | Generalized, each repair has unique specialization |
| ElectricianSkill structure | One row per skill type + service_item_id | One row per specialization |

### Removed/Kept Columns
- ❌ Removed: `ElectricianSkill.service_item_id` (no longer needed for matching)
- ✅ Added: `OrderSegment.repair_issue_id` (for display/traceability, not matching)
- ✅ Kept: `OrderSegment.service_item_id` (for display/traceability, not matching)
