# GharSeva App - Functionality Overview

Last Updated: 2026-09-23 (Updated after Phase 4: Full specialization generalization, 1:1 repair-specialization mapping)

This document describes the features currently supported by the GharSeva backend API from a customer and electrician perspective.

---

## Authentication & User Roles

The app uses AWS Cognito for authentication. Users are assigned one of two roles via Cognito Groups:
- **Customer**: Can create orders for home repairs
- **Electrician**: Can accept job assignments

Both customers and electricians authenticate with an ID token to access their profiles and role-specific features.

---

## Customer Functionality

### 1. View My Profile
**Endpoint**: `GET /auth/me`
- Returns the customer's authenticated identity
- Information returned: user ID (from Cognito `sub`), email, assigned role

### 2. Create My User Profile
**Endpoint**: `POST /users/me`
- Creates or retrieves the customer's local profile (stored in the app database)
- Syncs the customer's Cognito identity with the app's user table
- Returns: profile ID, email, phone number, role, creation timestamp

### 3. Create a Service Order
**Endpoint**: `POST /orders`
- Customers can place an order for home repair services
- **What you can order**:
  - Repair issues: General repair ₹300, AC repair ₹1000, Refrigerator repair ₹500, Mixer grinder repair ₹500
  - Service items: Fan installation ₹1000, AC installation ₹4000, AC gas filling ₹5000, Switchboard installation ₹800
  - Or both repair issues and service items in a single order
- **Pricing calculation**:
  - Each repair issue and service item has its own fixed price
  - Total amount = sum of all selected items' prices
  - No shared visit charge
- **Validation**: At least one repair issue or service item must be included
- **Returns**: Order ID, customer ID, total amount, order status (`pending_assignment`)

### 4. View My Orders
**Endpoint**: `GET /orders/me`
- Retrieves all orders placed by the customer, sorted by most recent first
- Shows order ID, items ordered, pricing, current status, and creation time
- **Order statuses**:
  - `pending_assignment`: Waiting for electrician assignment
  - `assigned`: One or more electricians have accepted the job

### 5. Logout
**Endpoint**: `POST /auth/logout`
- Logs out the customer from Cognito
- Invalidates the customer's session

---

## Electrician Functionality

### 1. View My Profile
**Endpoint**: `GET /auth/me`
- Returns the electrician's authenticated identity
- Information returned: user ID, email, assigned role

### 2. Create My Electrician Profile
**Endpoint**: `POST /users/me`
- Creates or retrieves the electrician's local profile in the app database
- Returns: profile ID, email, phone number, role, creation timestamp

### 3. Declare My Skills
**Endpoint**: `POST /electricians/me/skills`
- Electricians declare which specializations they can perform
- **Request body**: `{ "specializations": ["general_repair", "ac_repair", "fan_installation"] }`
- **What you can declare**: Any specialization from the catalog (e.g., general_repair, ac_repair, refrigerator_repair, mixer_grinder_repair, fan_installation, ac_installation, ac_gas_filling, switchboard_installation)
- **How it works**: Replaces your existing skills with the new set entirely (delete old, insert new)
- **Returns**: Your electrician ID and current specializations

### 4. View My Skills
**Endpoint**: `GET /electricians/me/skills`
- Returns the specializations you've declared as able to perform
- **Returns**: Your electrician ID and list of specializations
- Used by the app to pre-check boxes on edit screens

### 5. Accept a Job Assignment (Accept a Dispatch Round)
**Endpoint**: `POST /jobs/rounds/{round_id}/accept`
- Electricians receive notifications about available job opportunities (dispatch rounds)
- A dispatch round bundles multiple work segments that a single electrician can handle
- **What happens when you accept**:
  - The round status changes to `filled`
  - All segments in that round are assigned to you
  - The order may be marked as `assigned` (if all segments are now covered)
  - You receive confirmation with the list of segments and total amount
- **Validation**: You can only accept if:
  - You have the required skills for all segments in the round
  - The round is still open (not yet accepted by someone else)
  - You were nominated as a candidate for this round

### 6. Logout
**Endpoint**: `POST /auth/logout`
- Logs out the electrician from Cognito

---

## Order Assignment to Electricians

### How Orders are Segmented

When a customer creates an order, it's automatically broken down into **segments** based on specialization:
- **Repair issue segments**: One segment per repair issue (1:1 mapping with specialization)
  - General repair → `general_repair` segment
  - AC repair → `ac_repair` segment
  - Refrigerator repair → `refrigerator_repair` segment
  - Mixer grinder repair → `mixer_grinder_repair` segment
- **Service item segments**: One segment per service item, each with its own specialization
  - Fan installation → `fan_installation` segment
  - AC installation → `ac_installation` segment
  - And so on...

Example: Order with General repair + AC repair + Fan installation + AC gas filling = 4 segments (one per item)

### How Segments are Assigned to Electricians

The system uses an intelligent **dispatch round mechanism** to match segments with electricians:

#### Step 1: Segment Grouping
After an order is created, the system analyzes open segments and tries to **group them efficiently**:
- It looks for the largest possible group of segments that can be handled by electricians with matching skills
- It prioritizes assigning multiple segments to the same electrician (when possible) to reduce coordination overhead

#### Step 2: Creating a Dispatch Round
Once a group is identified:
- A **dispatch round** is created containing 1 or more segments
- The system finds all electricians who have the required skills for ALL segments in the round
- These electricians become **candidates** for the round
- Each candidate is notified of the opportunity (currently a logging stub, will integrate with push notifications)

#### Step 3: Electrician Acceptance
- Electricians can accept the round via `POST /jobs/rounds/{round_id}/accept`
- First electrician to accept "wins" the round and gets assigned all segments in it
- The round status changes from `open` to `filled`
- Other candidates for that round lose the opportunity

#### Step 4: Remaining Segments
- If segments remain unassigned, the process repeats
- A new dispatch round is created for the next batch of segments
- This continues until all segments are either assigned or no matching electricians exist

#### Step 5: Order Completion
- An order is marked as `assigned` once ALL its segments have been claimed by electricians
- An order can have **multiple electricians** if different segments are assigned to different people

### Example Workflow

**Scenario**: Customer orders General repair (₹300) + AC repair (₹1000) + Fan installation (₹1000) + AC gas filling (₹5000)

1. **Order created**: 4 segments total
   - 1 general_repair segment (₹300)
   - 1 ac_repair segment (₹1000)
   - 1 fan_installation segment (₹1000)
   - 1 ac_gas_filling segment (₹5000)
   - Total order amount: ₹7300

2. **First dispatch round**: System finds Electrician A has skills for general_repair + fan_installation
   - Round created with 2 segments (general_repair ₹300 + fan_installation ₹1000 = ₹1300)
   - Electrician A declared skills: ["general_repair", "fan_installation"]
   - Electrician A is the only candidate
   - Electrician A accepts → Round fills

3. **Second dispatch round**: System finds Electrician B has skills for ac_repair only
   - Round created with 1 segment (ac_repair ₹1000)
   - Electrician B declared skills: ["ac_repair"]
   - Electrician B is the only candidate
   - Electrician B accepts → Round fills

4. **Third dispatch round**: System finds Electrician C has skills for ac_gas_filling
   - Round created with 1 segment (ac_gas_filling ₹5000)
   - Electrician C declared skills: ["ac_repair", "ac_gas_filling", "refrigerator_repair"]
   - Electrician C is the only candidate
   - Electrician C accepts → Round fills

5. **Order status changes to `assigned`**: All 4 segments covered (Electricians A, B, and C)

### Single vs. Multiple Electrician Assignment

- **Single electrician**: If one electrician has all required skills, they get the entire order
- **Multiple electricians**: If no single electrician covers all segments, the order is split across multiple specialists
  - Each electrician is responsible for their assigned segments only
  - Customers and electricians can see the breakdown of who handles what

---

## Data Models Summary

### Repair Issues
- Pre-defined categories of repair work, each with a fixed price and unique specialization (1:1 mapping):
  - **General repair** (₹300) → `general_repair` specialization — Covers fan, light, switch, socket repairs
  - **AC repair** (₹1000) → `ac_repair` specialization
  - **Refrigerator repair** (₹500) → `refrigerator_repair` specialization
  - **Mixer grinder repair** (₹500) → `mixer_grinder_repair` specialization
- Can be marked as active/inactive
- Each repair issue creates one segment with its specialization

### Service Items
- Pre-defined services with fixed prices and unique specializations:
  - Fan installation (₹1000) → `fan_installation`
  - AC installation (₹4000) → `ac_installation`
  - AC gas filling (₹5000) → `ac_gas_filling`
  - Switchboard installation (₹800) → `switchboard_installation`
- Can be marked as active/inactive
- Each service item creates its own segment with its specialization

### Electrician Skills
- Each electrician declares specializations they can perform via `POST /electricians/me/skills`
- Examples: `["general_repair", "ac_repair", "fan_installation"]`
- Any specialization string from the catalog is valid (fully generic, no hardcoded list)
- Skills determine which order segments they are eligible to handle
- The system only offers rounds to electricians whose skills match ALL segments in that round
- Skills can be updated at any time, replacing the entire previous set

### Order Statuses
- `pending_assignment`: No electrician has accepted yet
- `assigned`: At least one electrician has claimed work for this order
- `expired`: (Future) When dispatch rounds expire without being accepted, the order may retry with different candidates

---

## Key Design Principles

1. **Generic Specialization System**: Any new specialization can be added (repair or service) without code changes — just add catalog rows and electricians declare matching skills
2. **1:1 Repair-Specialization Mapping**: Each repair issue has exactly one unique specialization, simplifying segment creation and electrician matching
3. **Skill-Based Matching**: Electricians are only offered work matching their declared specializations (pure string comparison, no hardcoded values)
4. **Efficient Grouping**: The system tries to minimize the number of electricians needed by finding the largest group each electrician can handle
5. **Fair Competition**: When multiple electricians qualify, the first to accept wins
6. **Order Flexibility**: Orders can span multiple electricians for better coverage
7. **Pricing Transparency**: Customers see the full cost breakdown upfront, with no shared visit charges

---

## Future Enhancements (Not Yet Implemented)

- Order cancellation and modifications
- Electrician job completion and reviews
- Payment processing
- Real-time push notifications (currently logging only)
- Dispatch round expiration and retry logic
- Customer tracking of electrician location and ETA
