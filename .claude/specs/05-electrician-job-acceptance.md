# Spec: Electrician Skills and Order Segments

## Scope

This spec introduces electrician specialization data (which repairs and/or services an electrician is skilled to perform), splits each order into segments by specialization, and lets an electrician manage their own declared skills.

**Acceptance/matching of segments to a specific electrician happens entirely in the dispatch rounds spec, not here.** This spec only defines the data (skills, segments) and the endpoints for an electrician to view and set their own skills. There is no "browse available jobs" or "accept a job" endpoint in this spec, that mechanism is a round-based broadcast system defined separately.

This spec does NOT cover:
- Any job acceptance mechanism (see the dispatch rounds spec)
- Job status beyond `open`/`assigned` per segment (no in-progress/completed yet)
- Any admin UI for managing specializations (electricians set their own; admin verification of the electrician account overall is a manual process outside this app)

## Background

Specialization is a fully generic, data-driven string field, not a hardcoded set of values. `RepairIssue.specialization` and `ServiceItem.specialization` can be any slug (`general_repair`, `ac_repair`, `refrigerator_repair`, `mixer_grinder_repair`, `fan_installation`, and so on, per the service catalog spec). Matching between segments and electrician skills is a plain string comparison, "does this segment's specialization appear in this electrician's declared skills," with zero hardcoded branching by specialization name anywhere in the code. Adding a new specialization later requires zero code changes, only new catalog rows and electricians declaring that skill.

Each `RepairIssue` has a unique specialization (a strict 1:1 mapping between item and specialization, per the service catalog spec). This means a segment representing repair work always traces back to exactly one `RepairIssue`, never several.

Pricing is per-item: each `RepairIssue` and `ServiceItem` has its own fixed price. A segment's `amount` is the price of the item(s) it represents.

## Database

### `ElectricianSkill`
- `id` — integer, primary key, auto-increment
- `electrician_id` — string, foreign key to `User.id`
- `specialization` — string, any value matching a `RepairIssue.specialization` or `ServiceItem.specialization` in the catalog

One row per skill the electrician has, an electrician with 3 skills has 3 rows.

### `OrderSegment`
- `id` — integer, primary key, auto-increment
- `order_id` — integer, foreign key to `Order.id`
- `specialization` — string, the matching key (same value space as `ElectricianSkill.specialization`)
- `repair_issue_id` — integer, nullable, foreign key to `RepairIssue.id`, set only if this segment represents a Repair issue, null otherwise
- `service_item_id` — integer, nullable, foreign key to `ServiceItem.id`, set only if this segment represents a Service item, null otherwise
- `amount` — integer, this segment's price, snapshotted at creation, never recomputed later
- `electrician_id` — string, nullable, foreign key to `User.id`, null means still open
- `status` — string, `"open"` or `"assigned"`

`specialization` is the only field matching logic ever reads. `repair_issue_id`/`service_item_id` exist purely for display purposes (naming the segment for a customer or electrician to read), never for matching.

### `Order` (extends the order spec's table)
- `status` is derived, not a simple flat value: `"pending_assignment"` if no segments are assigned yet, `"partially_assigned"` if some but not all segments are assigned, `"assigned"` if every segment has an electrician. Stored as a real column for querying, recomputed and updated every time a segment's assignment changes.

## Order creation

### `POST /orders` (extends the order spec's endpoint)

After creating the `Order` row, create its segments:
- Group the selected `repair_issue_ids` by their `RepairIssue.specialization` value, using a plain groupby over whatever distinct specializations are actually present, not a fixed list of expected values. For each distinct specialization present, create one `OrderSegment` with that `specialization`, `repair_issue_id` set (each specialization maps to exactly one `RepairIssue.id`), `amount` = that item's price, `status = "open"`.
- For each ID in `service_item_ids`, create one `OrderSegment` with `specialization` = that `ServiceItem`'s own specialization, `service_item_id` set, `repair_issue_id = null`, `amount = ServiceItem.price`, `status = "open"`.

`Order.total_amount` is the sum of all its segments' `amount` values.

## Electrician skill management

### `POST /electricians/me/skills`

- Protected by `get_current_electrician` (an ID-token dependency that additionally requires `"electrician"` in the token's `cognito:groups`, returning 403 if absent).
- Request body: `{ "specializations": ["general_repair", "refrigerator_repair", "fan_installation"] }`, a plain list of specialization strings.
- Replaces the caller's existing `ElectricianSkill` rows entirely with the new set (delete old rows, insert new ones).
- Returns the resulting skill set.

### `GET /electricians/me/skills`

- Protected by `get_current_electrician`.
- Returns the caller's current skills.

## Non-functional requirements

- A customer's token must get 403 from both `/electricians/me/skills` endpoints.
- No token is ever logged.

## Acceptance criteria

- [ ] Selecting the single "General repair" catalog item creates one segment priced at exactly ₹300.
- [ ] Selecting General repair + AC repair creates two separate segments (₹300 and ₹1,000), since they're different specializations.
- [ ] Selecting Refrigerator repair + Mixer grinder repair creates two separate segments, proving the grouping logic works generically across whatever specializations exist, not a hardcoded pair.
- [ ] `Order.total_amount` correctly sums every resulting segment's amount, for any combination of repair issues and service items.
- [ ] `POST /electricians/me/skills` correctly replaces a caller's skill set (old skills removed, new skills present) and `GET /electricians/me/skills` reflects it.
- [ ] A customer's token gets 403 from both skill endpoints.