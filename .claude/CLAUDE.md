# CLAUDE.md

## Project overview

GharSeva backend is the API layer for a home services marketplace app, built with FastAPI. It handles authentication (via AWS Cognito) and now has its first database table (user profiles). It will grow to handle service orders, pricing, and electrician assignment. The Android client (Kotlin) is a separate project and out of scope here.

---

## Current architecture

gharseva-backend/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app instance, router registration, DB table creation on startup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Reads .env into a typed Settings object
│   │   └── security.py     # Cognito JWKS fetch + token verification (get_current_user for ID tokens, get_current_access_token for access tokens)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py      # SQLAlchemy engine, get_db dependency
│   │   └── models.py       # SQLAlchemy models (User)
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           ├── auth.py     # GET /auth/me, POST /auth/logout
│           └── users.py    # POST /users/me
├── specs/
│   └── *.md                # SDD spec files, one per feature slice
├── .env                     # Never committed
├── .gitignore
└── requirements.txt

**Where things belong:**
- New endpoints → `app/api/routes/<feature>.py`, one file per feature area, never all in one file
- Auth/token logic → `app/core/security.py` only, never inline in routes
- Config/env reads → `app/core/config.py` only, never `os.environ` scattered through the code
- Database models → `app/db/models.py`, database session/connection logic → `app/db/session.py`, never inline SQLAlchemy engine creation in routes
- New feature specs → `specs/<feature-name>.md` before implementation starts (see SDD workflow below)

---

## Code style

- Python: PEP 8, snake_case for functions and variables, type hints on every function signature
- Request/response shapes: always a Pydantic model, never raw dicts returned from a route
- Route functions: one responsibility only — validate input, call logic, return response
- Async: use `async def` for all route handlers and any I/O-bound calls (Cognito, database)
- Error handling: raise `HTTPException` with an explicit status code, never return a bare string or silently swallow an exception
- Database writes: always `db.commit()` after `db.add(...)`, and refresh the object if returning generated/default fields

---

## Tech constraints

- **FastAPI only** — no Flask, no Django
- **AWS Cognito for auth** — never write custom password hashing, storage, or verification logic; the backend verifies tokens, it does not issue them
- **boto3 for all AWS calls** — no other AWS SDK or raw HTTP calls to AWS services
- **SQLAlchemy for the database** — models in `app/db/models.py`, session handling via `app/db/session.py`'s `get_db` dependency. Currently backed by local SQLite (`DATABASE_URL` in `.env`) for development. Switching to RDS Postgres later only requires changing `DATABASE_URL` and using the already-installed `psycopg2-binary` driver, no code changes to models or routes.
- **No migration tool yet** — tables are created via `Base.metadata.create_all()` on app startup. Introduce Alembic only when a spec explicitly calls for it (schema changes will need it eventually, not yet).
- **No new pip packages** mid-feature without flagging it — keep `requirements.txt` in sync via `pip freeze`
- Python 3.10+ assumed

---

## Identity and roles

- Role (customer vs electrician) is represented via **Cognito Groups**, not a custom attribute. There is no `custom:role` field on this User Pool.
- Two groups exist: `customer` and `electrician`.
- A user's group membership appears in their verified ID token as the `cognito:groups` claim (a list of group names). Always read role from this claim, never from a custom attribute or from anything client-supplied.
- Cognito issues two token types, and they are not interchangeable:
  - **ID token** — identity/profile claims (`sub`, `email`, `cognito:groups`). Required by `GET /auth/me` and `POST /users/me`.
  - **Access token** — session/authorization claims only (`scope`, `client_id`). Required by `POST /auth/logout`, since it's used to call Cognito's `global_sign_out` API on the user's behalf.
- Sending the wrong token type to an endpoint must return 401, not be silently accepted.
- The local `User` table (`app/db/models.py`) mirrors identity by `id` = Cognito `sub`. It is the source of truth for anything Cognito doesn't store (and future foreign keys for orders, etc.), Cognito remains the source of truth for credentials and verification status.

---

## SDD workflow

- Every new feature starts as a spec in `specs/<feature-name>.md` before any code is written
- A spec must state: scope (what it covers and explicitly does not cover), inputs/config needed, expected behavior per endpoint, and any non-functional requirements (logging, caching, error format)
- Do not implement beyond what the active spec describes, flag anything that seems missing from the spec instead of assuming

---

## Implementation workflow

- When asked to implement a spec, work through the files it introduces one at a time, in the order they're introduced in the spec.
- After finishing each file, stop and summarize: what was implemented, any assumptions made, and any deviation from the spec. Do not proceed to the next file until the human has reviewed and confirmed the current one.
- If a spec is ambiguous or missing something needed to implement a file, stop and ask rather than guessing.

---

## Subagent policy

- Always use a builtin explore subagent for codebase exploration before implementing any new feature
- Always use a subagent to verify test results after any implementation
- When asked to plan, delegate codebase research to a subagent before presenting the plan
- Always use a builtin plan subagent in plan mode

---

## Commands

Setup:
    python -m venv venv
    source venv/bin/activate          # Windows: venv\Scripts\activate
    pip install -r requirements.txt

Run dev server:
    uvicorn app.main:app --reload --port 8000

Run all tests:
    pytest

Run a specific test file:
    pytest tests/test_foo.py

Run tests with output visible:
    pytest -s

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /auth/me` | Implemented — verifies ID token, returns `sub`, `email`, `cognito:groups` |
| `POST /auth/logout` | Implemented — verifies access token, calls Cognito `global_sign_out` |
| `POST /users/me` | Implemented — verifies ID token, creates/returns a local `User` profile row keyed by `sub` |

**Do not implement a new route unless an active spec explicitly targets it.**

---

## Warnings and things to avoid

- **Never accept or store a raw password** — Cognito owns credentials entirely, the backend only ever sees tokens
- **Never trust a role or user ID sent in a request body** — always read identity/role from the verified token's `cognito:groups` claim, never from client-supplied fields
- **Never log a full token or secret value** — log the request path and outcome, not the Authorization header contents
- **Never hardcode Cognito User Pool ID, Client ID, AWS region, or DATABASE_URL** — always read from `app/core/config.py`
- **Fetch Cognito's JWKS once and cache it** — never re-fetch the public keys on every single request
- **Never commit `.env`** — it must stay in `.gitignore` at all times
- **Never accept an access token where an ID token is required, or vice versa** — check `token_use` and reject mismatches with 401
- **Never forget `db.commit()`** after `db.add(...)` — a missing commit means data silently never persists despite the endpoint appearing to succeed
- **Never add a new cloud service or swap the database engine** without a spec introducing it first