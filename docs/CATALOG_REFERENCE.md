# Catalog Reference: Repair Issues & Service Items

The catalog consists of pre-defined repair issues and service items, each with a fixed price and unique specialization. Initialized on app startup in `app/main.py`.

---

## Repair Issues

4 repair categories, each with 1:1 mapping to a specialization:

| ID | Name | Price (₹) | Specialization | Description |
|---|---|---|---|---|
| 1 | General repair | 300 | `general_repair` | Fan, light, switch, socket repairs |
| 2 | AC repair | 1000 | `ac_repair` | Air conditioner repair |
| 3 | Refrigerator repair | 500 | `refrigerator_repair` | Refrigerator repair |
| 4 | Mixer grinder repair | 500 | `mixer_grinder_repair` | Mixer grinder repair |

All created with `active=True` on startup. Every repair issue has a **unique specialization** (1:1 mapping).

---

## Service Items

4 service offerings, each with unique specialization:

| ID | Name | Price (₹) | Specialization | Description |
|---|---|---|---|---|
| 1 | Fan installation | 1000 | `fan_installation` | Install a new fan |
| 2 | AC installation | 4000 | `ac_installation` | Install a new air conditioner |
| 3 | AC gas filling | 5000 | `ac_gas_filling` | AC gas refill |
| 4 | Switchboard installation | 800 | `switchboard_installation` | Install electrical switchboard |

All created with `active=True` on startup. Each service item has a **unique specialization**.

---

## Specialization Names

Specializations are **generic strings** — no hardcoded enum or validation:
- Repair issue specializations: `general_repair`, `ac_repair`, `refrigerator_repair`, `mixer_grinder_repair`
- Service item specializations: `fan_installation`, `ac_installation`, `ac_gas_filling`, `switchboard_installation`

To add a new repair or service:
1. Add a row to `repair_issues` or `service_items` with a new `specialization` value
2. Electricians declare matching specializations via `POST /electricians/me/skills`
3. No code changes needed — dispatch matching is purely string-based

---

## How Catalog is Used

1. **Order creation** (`POST /orders`):
   - Customer sends `repair_issue_ids` and `service_item_ids`
   - Backend validates all IDs exist and are `active=True`
   - Looks up prices and specializations from the catalog
   - Creates one segment per repair issue and one per service item

2. **Pricing**:
   - Total order amount = sum of all item prices
   - No shared visit charge or base fee
   - Transparent, per-item pricing

3. **Skill matching**:
   - Each segment has `specialization` from its catalog item
   - Electricians declare specializations they can perform
   - Dispatch system matches purely by specialization string

---

## Deactivating Items

Items have an `active` boolean field. To deactivate a repair issue or service item:
- Update the database directly (no admin UI yet)
- `UPDATE repair_issues SET active=False WHERE id=1;`
- `UPDATE service_items SET active=False WHERE id=1;`
- Deactivated items cannot be selected in new orders but don't affect existing orders

---

## Initialization Logic

On app startup (`app/main.py`), if items don't exist:
```python
# Repair issues
RepairIssue(name="General repair", category="electrician", price=300, specialization="general_repair", active=True)
RepairIssue(name="AC repair", category="electrician", price=1000, specialization="ac_repair", active=True)
RepairIssue(name="Refrigerator repair", category="electrician", price=500, specialization="refrigerator_repair", active=True)
RepairIssue(name="Mixer grinder repair", category="electrician", price=500, specialization="mixer_grinder_repair", active=True)

# Service items
ServiceItem(name="Fan installation", category="electrician", price=1000, specialization="fan_installation", active=True)
ServiceItem(name="AC installation", category="electrician", price=4000, specialization="ac_installation", active=True)
ServiceItem(name="AC gas filling", category="electrician", price=5000, specialization="ac_gas_filling", active=True)
ServiceItem(name="Switchboard installation", category="electrician", price=800, specialization="switchboard_installation", active=True)
```

All items are `category="electrician"` (for future expansion to other professions) and `active=True` by default.
