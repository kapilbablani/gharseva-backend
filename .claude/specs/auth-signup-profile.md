# Spec: Auth Signup Profile

## Scope

This spec covers creating a local profile record for a user right after they successfully sign up via Cognito, regardless of whether they signed up with password, OTP, or Google. It introduces the first database table in this project.

This spec does NOT cover:
- Any Cognito-side signup logic (handled entirely by the Android app talking to Cognito directly, not by this backend)
- Editing or updating profile fields after creation (a later spec)
- Admin approval/verification workflows for electricians (a later spec)
- Orders, pricing, or any non-auth data
- Production database provisioning (RDS setup). For now, the database connects via a `DATABASE_URL` env var, pointing at a local SQLite file for development. Swapping this to RDS Postgres later requires no code change, only a different `DATABASE_URL` value and the `psycopg2-binary` driver already in `requirements.txt`.

The backend's job here is narrow: once Cognito confirms an account exists, make sure a matching profile row exists in our own database too, so we have a place to store anything Cognito doesn't (and so future features like orders can reference a real foreign key).

## Background

Cognito owns identity (credentials, verification, tokens). It does not own our application's data. After a user signs up and Cognito confirms their account, the Android app will call this backend once to ensure a corresponding profile row exists here, keyed by the same `sub` (Cognito's user ID) that appears in every token.

This must be safe to call more than once. The Android app may call this endpoint on every login, not just once after signup, to keep things simple on the client side. This endpoint must not create duplicate rows or error out if the profile already exists, it should just confirm/return the existing one.

## Inputs / Configuration

New env var, added to `.env` and read via `app/core/config.py`:
- `DATABASE_URL` (e.g. `sqlite:///./gharseva.db` for local dev)

Incoming requests must include:
- `Authorization: Bearer <ID token>` header (this endpoint requires an ID token, same as `/auth/me`, since it needs `email` and `cognito:groups`)

## New dependency

Add `sqlalchemy` to `requirements.txt` (already present) if not already installed, no new packages beyond what's already there.

## Database

Introduce a `Base` and a database session pattern in a new file, `app/db/session.py`:
- SQLAlchemy engine created from `DATABASE_URL`
- A `get_db` FastAPI dependency that yields a session and closes it after the request

Introduce a `User` model in a new file, `app/db/models.py`:
- `id` — string, primary key, set to the Cognito `sub` (not an auto-increment integer, since Cognito already gives us a stable unique ID)
- `email` — string, nullable
- `phone_number` — string, nullable
- `role` — string, not nullable (`customer` or `electrician`, taken from the token's `cognito:groups`, first group if multiple)
- `created_at` — datetime, defaults to now

On app startup (in `app/main.py`), call `Base.metadata.create_all(engine)` so the table is created automatically for local SQLite dev, this is fine for now, a real migration tool (Alembic) can be introduced later once schema changes become frequent.

## Behavior

### `POST /users/me` (`app/api/routes/users.py`, a new route file)

- Protected by the existing `get_current_user` dependency (ID token).
- Look up a `User` row by `id == sub` from the token.
- If it exists, return it as-is (200), do not modify it. This call is idempotent.
- If it does not exist, create it using `sub`, `email`, `phone_number` (if present in the token), and `role` derived from `cognito:groups` (take the first group name; if `cognito:groups` is empty or missing, return 400, a user must belong to a group before a profile can be created, this indicates something went wrong upstream in Cognito setup, not a normal case).
- Return the created or existing row as JSON: `id`, `email`, `phone_number`, `role`, `created_at`.
- Response model must be a Pydantic model, not the raw SQLAlchemy object.

## Non-functional requirements

- Role is always derived from the token's `cognito:groups`, never accepted from a request body, there is no request body for this endpoint at all, everything needed comes from the verified token.
- Do not log full token contents. Logging the outcome (created vs already-existed vs rejected) by `sub` is fine.
- Database session must be properly closed after each request (via the `get_db` dependency's generator pattern), no leaked connections.

## Acceptance criteria

- [ ] Calling `POST /users/me` for the first time with a valid ID token creates a row and returns 200 with the correct `id`, `email`, `phone_number`, `role`.
- [ ] Calling it again with the same token returns 200 with the same data, and does not create a second row (verify by checking the table has exactly one row for that `sub`).
- [ ] A token whose `cognito:groups` is missing or empty returns 400, not a 500 crash.
- [ ] Missing or invalid Authorization header returns 401 (same behavior as `/auth/me`, via the shared dependency).
- [ ] An access token (instead of ID token) sent to this endpoint returns 401 (wrong token type, same rule as `/auth/me`).