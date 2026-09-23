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

- Protected by the existing `get_current_user` dependency (requires an ID token with verified claims).
- Extract the following from the verified token claims: `sub`, `email` (optional), `phone_number` (optional), `cognito:groups` (required, must be a non-empty list).
- If `cognito:groups` is missing or empty, return 400 with message "User must belong to a group" — a user must belong to a Cognito Group before a profile can be created; this indicates an issue with upstream Cognito setup, not a normal case.
- Query the `User` table for an existing row where `id == sub`.
  - If found, return 200 with the existing user's data (unchanged). This call is idempotent; calling it multiple times returns the same result without creating duplicates.
  - If not found, create a new `User` row with: `id` = `sub`, `email` = email from claims (may be None), `phone_number` = phone_number from claims (may be None), `role` = first element of `cognito:groups` list (since each user must belong to at least one group). Commit to database, then return 201 with the newly created user's data.
- Response is a Pydantic model (`UserResponse`) with fields: `id`, `email` (nullable), `phone_number` (nullable), `role`, `created_at`.
- All returned User objects must be serialized through the response Pydantic model to ensure consistent JSON shape, never return raw SQLAlchemy objects.

## Non-functional requirements

- Role is always derived from the token's `cognito:groups`, never accepted from a request body, there is no request body for this endpoint at all, everything needed comes from the verified token.
- Do not log full token contents. Logging the outcome (created vs already-existed vs rejected) by `sub` is fine.
- Database session must be properly closed after each request (via the `get_db` dependency's generator pattern), no leaked connections.

## Acceptance criteria

- [ ] Calling `POST /users/me` for the first time with a valid ID token creates a User row in the database and returns 200 with the correct `id`, `email`, `phone_number`, `role`, `created_at`.
- [ ] Calling it again with the same token returns 200 with the same data (no changes to the row, fully idempotent), verified by checking the database has exactly one row for that `sub` with no duplicate entries.
- [ ] A token whose `cognito:groups` is missing or empty returns 400 with detail "User must belong to a group", not a 500 crash.
- [ ] Missing or invalid Authorization header returns 401 with detail "Invalid or expired token" (delegated to the shared `get_current_user` dependency).
- [ ] An access token (instead of ID token) sent to this endpoint returns 401 (wrong token type; delegated to the shared `get_current_user` dependency which requires an ID token).
- [ ] The response is always a JSON object with `id`, `email` (may be null), `phone_number` (may be null), `role` (non-null), and `created_at` (ISO 8601 datetime string), never a partial or raw SQLAlchemy object.