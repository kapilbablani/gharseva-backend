# CLAUDE.md

## Project overview

GharSeva backend is the API layer for a home services marketplace app, built with FastAPI. It will handle authentication (via AWS Cognito), and later grow to handle service orders, pricing, and electrician assignment. The Android client (Kotlin) is a separate project and out of scope here. This project is currently empty, nothing has been scaffolded yet.

---

## Target architecture

This structure does not exist yet. Build it exactly as laid out here, do not invent a different layout.

gharseva-backend/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app instance, router registration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Reads .env into a typed Settings object
│   │   └── security.py     # Cognito JWKS fetch + token verification
│   └── api/
│       ├── __init__.py
│       └── routes/
│           ├── __init__.py
│           └── auth.py     # Auth-related endpoints only
├── specs/
│   └── *.md                # SDD spec files, one per feature slice
├── .env                     # Never committed
├── .gitignore
└── requirements.txt

**Where things belong:**
- New endpoints → `app/api/routes/<feature>.py`, one file per feature area, never all in one file
- Auth/token logic → `app/core/security.py` only, never inline in routes
- Config/env reads → `app/core/config.py` only, never `os.environ` scattered through the code
- New feature specs → `specs/<feature-name>.md` before implementation starts (see SDD workflow below)

---

## Code style

- Python: PEP 8, snake_case for functions and variables, type hints on every function signature
- Request/response shapes: always a Pydantic model, never raw dicts returned from a route
- Route functions: one responsibility only — validate input, call logic, return response
- Async: use `async def` for all route handlers and any I/O-bound calls (Cognito, database once added)
- Error handling: raise `HTTPException` with an explicit status code, never return a bare string or silently swallow an exception

---

## Tech constraints

- **FastAPI only** — no Flask, no Django
- **AWS Cognito for auth** — never write custom password hashing, storage, or verification logic; the backend verifies tokens, it does not issue them
- **boto3 for all AWS calls** — no other AWS SDK or raw HTTP calls to AWS services
- **No database yet** — do not assume SQLAlchemy, RDS, or any ORM exists until a spec explicitly introduces it
- **No new pip packages** mid-feature without flagging it — keep `requirements.txt` in sync via `pip freeze`
- Python 3.10+ assumed

---

## Identity and roles

- Role (customer vs electrician) is represented via **Cognito Groups**, not a custom attribute. There is no `custom:role` field on this User Pool.
- Two groups exist: `customer` and `electrician`.
- A user's group membership appears in their verified token as the `cognito:groups` claim (a list of group names). Always read role from this claim, never from a custom attribute or from anything client-supplied.

---

## SDD workflow

- Every new feature starts as a spec in `specs/<feature-name>.md` before any code is written
- A spec must state: scope (what it covers and explicitly does not cover), inputs/config needed, expected behavior per endpoint, and any non-functional requirements (logging, caching, error format)
- Do not implement beyond what the active spec describes, flag anything that seems missing from the spec instead of assuming
- Since the project is empty, the very first task is creating the folder structure above with empty `__init__.py` files, this does not need its own spec, everything after it does

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
| `GET /auth/me` | Implemented |
| `POST /auth/logout` | Implemented |

**Nothing is implemented yet. Do not implement any route unless an active spec explicitly targets it.**

---

## Warnings and things to avoid

- **Never accept or store a raw password** — Cognito owns credentials entirely, the backend only ever sees tokens
- **Never trust a role or user ID sent in a request body** — always read identity/role from the verified token's `cognito:groups` claim, never from client-supplied fields
- **Never log a full token or secret value** — log the request path and outcome, not the Authorization header contents
- **Never hardcode Cognito User Pool ID, Client ID, or AWS region** — always read from `app/core/config.py`
- **Fetch Cognito's JWKS once and cache it** — never re-fetch the public keys on every single request
- **Never commit `.env`** — it must stay in `.gitignore` at all times
- **Never add a database, ORM, or new cloud service** without a spec introducing it first