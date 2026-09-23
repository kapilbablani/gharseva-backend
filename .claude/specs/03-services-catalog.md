# Spec: Service Catalog

## Scope

This spec defines the service catalog: Repair issues and Service items, each with its own fixed price, exposed via a single read endpoint the Android Home screen fetches from.

This spec does NOT cover:
- Admin editing UI for the catalog (admin edits directly via database access or seed data updates for now)
- Order/checkout logic (a separate spec)
- Electrician-facing catalog views (a separate spec)
- A future "credit toward a bigger final job" billing model (a possible future spec; this spec only handles the upfront fixed price per item)

## Background

**Category** (`repair` / `service`) is a pure UI grouping concept, it decides which of the two sections (Repair or Service) an item appears under on the Home screen. It has no effect on pricing or electrician matching.

**Specialization** is the backend matching concept, invisible to the customer, used to group items into segments for electrician dispatch. It is a fully generic string, any value is valid, there is no fixed set of expected specializations anywhere in the system. Each Repair issue has a unique specialization (a strict 1:1 mapping, each specialization corresponds to exactly one `RepairIssue` row). Each Service item is likewise its own distinct specialization.

## Database

### `RepairIssue`
- `id` — integer, primary key, auto-increment
- `name` — string, e.g. "General repair"
- `category` — string, the professional category this item belongs to (currently always `"electrician"`, exists to support other professions like plumber in a future phase)
- `price` — integer, whole rupees
- `specialization` — string, the matching key, unique per row
- `active` — boolean, default true

### `ServiceItem`
- `id` — integer, primary key, auto-increment
- `name` — string, e.g. "Fan installation"
- `price` — integer, whole rupees
- `category` — string, same meaning as `RepairIssue.category`
- `specialization` — string, the matching key, unique per row
- `active` — boolean, default true

## Seed data

Seed on app startup if these tables are empty. Seeding must be idempotent: running it again (e.g. across restarts) must never duplicate rows.

**RepairIssue rows** (each with `category = "electrician"`):
| name | price | specialization |
|---|---|---|
| General repair (fan / light / switch / socket) | 300 | general_repair |
| AC repair | 1000 | ac_repair |
| Refrigerator repair | 500 | refrigerator_repair |
| Mixer grinder repair | 500 | mixer_grinder_repair |

"General repair" is deliberately one selectable catalog item, not several. A customer with any single general issue (fan, light switch, or socket) selects this one item and pays ₹300 flat, regardless of which specific general issue it actually is.

**ServiceItem rows** (each with `category = "electrician"`):
| name | price | specialization |
|---|---|---|
| Fan installation | 1000 | fan_installation |
| AC installation | 4000 | ac_installation |
| AC gas filling | 5000 | ac_gas_filling |
| Switchboard installation | 800 | switchboard_installation |

## Behavior

### `GET /services`

- No authentication required, this is public catalog data, not user-specific.
- Accepts an optional query parameter `category` (default `"electrician"` if not provided). Filters both `RepairIssue` and `ServiceItem` rows by this value.
- Returns:
```json
{
  "category": "electrician",
  "repair": [
    { "id": 1, "name": "General repair (fan / light / switch / socket)", "price": 300 },
    { "id": 2, "name": "AC repair", "price": 1000 },
    { "id": 3, "name": "Refrigerator repair", "price": 500 },
    { "id": 4, "name": "Mixer grinder repair", "price": 500 }
  ],
  "service": [
    { "id": 1, "name": "Fan installation", "price": 1000 },
    { "id": 2, "name": "AC installation", "price": 4000 },
    { "id": 3, "name": "AC gas filling", "price": 5000 },
    { "id": 4, "name": "Switchboard installation", "price": 800 }
  ]
}
```
- `repair` and `service` are both flat arrays of the same shape (`id`, `name`, `price`).
- Only rows where `active = true` are included.
- Response shapes are Pydantic models, not raw dicts, per `CLAUDE.md`.

## Non-functional requirements

- Seeding must be idempotent, no duplicate rows across restarts.
- This endpoint is read-only.

## Acceptance criteria

- [ ] `GET /services` returns each Repair issue and Service item with its own `price`.
- [ ] General repair shows `price: 300`; AC repair shows `price: 1000`; Refrigerator repair shows `price: 500`; Mixer grinder repair shows `price: 500`.
- [ ] Each Repair issue has a unique `specialization` value (strict 1:1 mapping between `id` and `specialization`).
- [ ] `GET /services?category=electrician` returns the same result as the no-param call.
- [ ] `GET /services?category=plumber` (a category with no seeded rows) returns 200 with empty arrays, not an error.
- [ ] Restarting the server does not duplicate seed rows.