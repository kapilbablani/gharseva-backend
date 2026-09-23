# CLAUDE.md

GharSeva backend is FastAPI + SQLAlchemy + AWS Cognito. Auth via Cognito Groups (customer/electrician). Orders split into specialization-based segments; dispatch system automatically finds matching electricians. Complete through Phase 4.

## Architecture

```
app/
├── main.py              # FastAPI app, DB init, catalog init
├── core/
│   ├── config.py        # Settings from .env
│   ├── security.py      # Cognito token verification
│   └── dispatch.py      # Segment grouping & round creation
├── db/
│   ├── session.py       # SQLAlchemy session
│   └── models.py        # All 8 models (User, Order, Segment, etc)
└── api/routes/
    ├── auth.py          # /auth/me, /auth/logout
    ├── users.py         # /users/me
    ├── services.py      # /services (catalog)
    ├── orders.py        # /orders, /orders/me
    └── electricians.py  # /electricians/me/skills, /jobs/rounds/{id}/accept
docs/
├── APP_FUNCTIONALITY.md   # Feature overview
├── DATABASE_SCHEMA.md     # Complete schema
├── DISPATCH_SYSTEM.md     # Dispatch algorithm
└── CATALOG_REFERENCE.md   # Items & specializations
```

**Code placement:**
- Routes → `app/api/routes/<feature>.py` (one file per area)
- Auth/token logic → `app/core/security.py` only
- Config → `app/core/config.py` only (never `os.environ` inline)
- Models → `app/db/models.py`, sessions → `app/db/session.py`
- Specs → `specs/<name>.md` before implementation

## Code style

- PEP 8, snake_case, type hints on all functions
- Request/response as Pydantic models, never raw dicts
- Route functions: one responsibility (validate, call, return)
- Async: use `async def` for all route handlers and I/O
- Error handling: raise `HTTPException(status_code=..., detail=...)`
- Database: always `db.commit()` after `db.add(...)`

## Tech stack

- **FastAPI only** (no Flask, no Django)
- **AWS Cognito for auth** (never custom password logic)
- **boto3 for AWS calls** (never raw HTTP to AWS)
- **SQLAlchemy** (SQLite dev, Postgres prod; `psycopg2-binary` included)
- **Tables via `Base.metadata.create_all()`** on startup (no migrations yet)
- No new packages mid-feature without flagging
- Python 3.10+

## Identity & roles

- Role via Cognito Groups: `customer` or `electrician`
- ID token: identity claims (`sub`, `email`, `cognito:groups`) — for profile routes
- Access token: session claims (`scope`, `client_id`) — for logout
- Never accept wrong token type; verify `token_use`, return 401 on mismatch
- Local `User` table (keyed by Cognito `sub`) — profile data only
- Always read role from `cognito:groups`, never from request body

## Setup & run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

## Security

- Never accept/store raw passwords — Cognito owns credentials
- Never trust role/user ID from request body
- Never log full tokens or secrets
- Never hardcode Cognito IDs or DATABASE_URL (use `config.py`)
- Fetch Cognito JWKS once and cache it
- Never commit `.env`
- Always verify token type (`token_use`)
- Never forget `db.commit()`

## SDD (Software Design Document) Workflow

Every new feature starts as a spec in `specs/<feature-name>.md` **before any code is written**.

**Spec contents:**
- Scope: what it covers and explicitly does not cover
- Inputs/config needed
- Expected behavior per endpoint
- Non-functional requirements (logging, caching, error format)

**Implementation rule:** Do not implement beyond what the spec describes. Flag anything missing from the spec instead of assuming.

## Implementation Workflow

When asked to implement a spec:

1. **Work through files one at a time**, in the order introduced in the spec
2. **After finishing each file**, stop and summarize:
   - What was implemented
   - Any assumptions made
   - Any deviation from the spec
3. **Do not proceed to the next file** until the human has reviewed and confirmed the current one
4. **If a spec is ambiguous**, stop and ask rather than guessing
5. **Do not implement new routes without a spec.**

This step-by-step approach keeps implementation aligned with intent and catches issues early.

## Subagent Policy

- **Always use a builtin explore subagent** for codebase exploration before implementing any new feature
- **When asked to plan**, delegate codebase research to a subagent before presenting the plan
- **Always use a builtin plan subagent** in plan mode
