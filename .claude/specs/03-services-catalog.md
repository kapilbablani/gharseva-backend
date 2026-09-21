# Spec: Service Catalog

## Scope

This spec introduces the service catalog data (Repair issues + Service items with prices) as real database tables, seeded with the pricing already established in the app's design, and exposes it via a single read endpoint the Android Home screen can fetch from.

This spec does NOT cover:
- Any admin UI or endpoint to edit the catalog (admin can edit directly via database access or a seed script update for now; a real admin panel is a future spec)
- Orders, cart, or checkout logic (a later spec, this only covers "what can be selected and at what price," not "what the customer picked")
- Any electrician-facing catalog view (same data, but that's a separate screen/spec)

## Background

Per the app's existing design: customers choose from two categories on Home.
- **Repair**: a flat ₹300 visit charge covers any number of repair issues fixed in one visit (fan repair, AC repair, light/switch repair, socket repair, other). Repair issues themselves have no individual price, only the flat visit charge applies.
- **Service**: fixed-price, per-item jobs (e.g. Fan installation ₹1,000, AC installation ₹4,000, AC gas filling ₹5,000, Switchboard installation ₹800). Each item has its own price, multiple items can be selected together.

Phase 1 supports one professional category only: `electrician`. Phase 2 (a future spec, out of scope here) will add plumber, mason, carpenter, and painter. To avoid a data model migration later, every catalog row is tagged with a `category` field now, even though today every row has the same value (`electrician`) and the app has no category-picker UI yet. This spec does not build that picker screen, Home goes straight to Repair/Service, implicitly for the only category that currently exists.

## Database

New models in `app/db/models.py`:

### `RepairIssue`
- `id` — integer, primary key, auto-increment
- `name` — string, e.g. "Fan repair"
- `category` — string, e.g. "electrician" (every row uses this same value for now, exists so Phase 2's plumber/mason/carpenter/painter categories can be added later as new rows, not a schema change)
- `active` — boolean, default true (lets an item be hidden without deleting it later)

### `ServiceItem`
- `id` — integer, primary key, auto-increment
- `name` — string, e.g. "Fan installation"
- `price` — integer (store as whole rupees, no decimals needed for this pricing)
- `category` — string, e.g. "electrician" (same reasoning as `RepairIssue.category`)
- `active` — boolean, default true

### App-wide config value
- Add a simple `AppConfig` table (or a single-row settings table) with a `repair_visit_charge` integer field, seeded to `300`. Don't hardcode this value in the endpoint, read it from the database, so it can be changed later without a code deploy.

## Seed data

On app startup (alongside the existing `Base.metadata.create_all()` call in `main.py`), seed the tables if they're empty (check row count first, don't re-insert on every restart). Every row below gets `category = "electrician"`.

**RepairIssue rows:**
- Fan repair
- AC repair
- Light/switch repair
- Socket repair
- Other

**ServiceItem rows:**
- Fan installation — ₹1,000
- AC installation — ₹4,000
- AC gas filling — ₹5,000
- Switchboard installation — ₹800

**AppConfig:**
- `repair_visit_charge` = 300

## Behavior

### `GET /services` (`app/api/routes/services.py`, new route file)

- No authentication required, this is public catalog data, not user-specific.
- Accepts an optional query parameter `category` (default `"electrician"` if not provided, since that's the only category that exists in Phase 1). Filters both `RepairIssue` and `ServiceItem` rows by this value. This parameter exists now so the endpoint doesn't need to change shape when Phase 2 adds more categories, the Android app simply isn't sending anything but the default yet.
- Returns:
```json
{
  "category": "electrician",
  "repair": {
    "visit_charge": 300,
    "issues": [
      { "id": 1, "name": "Fan repair" },
      { "id": 2, "name": "AC repair" },
      { "id": 3, "name": "Light/switch repair" },
      { "id": 4, "name": "Socket repair" },
      { "id": 5, "name": "Other" }
    ]
  },
  "service": [
    { "id": 1, "name": "Fan installation", "price": 1000 },
    { "id": 2, "name": "AC installation", "price": 4000 },
    { "id": 3, "name": "AC gas filling", "price": 5000 },
    { "id": 4, "name": "Switchboard installation", "price": 800 }
  ]
}
```
- Only rows where `active = true` are included.
- Response shapes are Pydantic models, not raw dicts, per `CLAUDE.md`'s code style.

## Non-functional requirements

- Seeding must be idempotent, running it twice (e.g. across server restarts) must not create duplicate rows.
- This endpoint is read-only, no `POST`/`PUT`/`DELETE` in this spec.

## Acceptance criteria

- [ ] `GET /services` (no query param) returns 200 with the exact repair issues, service items, and visit charge listed above, and `"category": "electrician"` in the response.
- [ ] `GET /services?category=electrician` returns the identical result to the no-param call.
- [ ] `GET /services?category=plumber` (a category with no seeded rows yet) returns 200 with empty `issues`/`service` arrays, not an error, proving the filter genuinely works and the endpoint is ready for Phase 2 categories without code changes.
- [ ] Restarting the server does not duplicate seed data (row counts stay the same across restarts).
- [ ] The response matches the JSON shape above exactly, correct field names (`category`, `visit_charge`, `issues`, `service`, `price`).