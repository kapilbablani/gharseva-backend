# Spec: Auth Token Verification

## Scope

This spec covers verifying a Cognito-issued token and using that verification to power two endpoints: `GET /auth/me` and `POST /auth/logout`.

This spec does NOT cover:
- Signup or profile creation
- Password, OTP, or Google login flows themselves (all handled by Cognito directly from the Android app, not by this backend)
- Role-based authorization / permission checks (a later spec)
- Any database reads or writes

The backend's job here is narrow: given a token the Android app already obtained from Cognito, confirm it's genuine and not expired, and use it to identify the caller.

## Background

The Android app authenticates directly against AWS Cognito (via Amplify), regardless of whether the user logs in with password, OTP, or Google. Cognito returns an ID token and an access token. The Android app attaches one of these as a Bearer token on every request to this backend. This backend never sees a password, OTP code, or Google credential, only the resulting token.

## Inputs / Configuration

Read from `.env` via `app/core/config.py` (already implemented):
- `COGNITO_USER_POOL_ID`
- `COGNITO_APP_CLIENT_ID`
- `AWS_REGION`

Incoming requests to protected routes must include:
- `Authorization: Bearer <token>` header

## Behavior

### Token verification (`app/core/security.py`)

1. On first use, fetch Cognito's public JWKS (JSON Web Key Set) from:
   `https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json`
2. Cache the fetched keys in memory. Do not re-fetch on every request. Only re-fetch if a token's `kid` (key ID) isn't found in the cached set (handles Cognito's occasional key rotation).
3. Verify the incoming token using `python-jose`:
   - Signature is valid against the matching public key
   - Token is not expired (`exp` claim)
   - `aud` (or `client_id`, depending on token type) matches `COGNITO_APP_CLIENT_ID`
   - `iss` (issuer) matches the expected Cognito User Pool URL
4. On success, return the decoded claims (at minimum: `sub`, `email` if present, `custom:role` if present).
5. On any failure (expired, malformed, bad signature, wrong audience/issuer, missing header), raise an `HTTPException` with status 401 and a generic message ("Invalid or expired token"). Do not leak details about which specific check failed.
6. Expose this as a reusable FastAPI dependency (e.g. `get_current_user`) that any protected route can depend on.

### `GET /auth/me` (`app/api/routes/auth.py`)

- Protected by the `get_current_user` dependency.
- Returns the decoded claims from the token as the response body: `sub`, `email` (if present), `custom:role` (if present).
- Returns 401 if the token is missing, malformed, or fails verification (handled by the dependency itself).

### `POST /auth/logout` (`app/api/routes/auth.py`)

- Protected by the `get_current_user` dependency (must be a valid, currently-active token to log out).
- Takes the caller's access token (from the Authorization header) and calls Cognito's `global_sign_out` via `boto3`, which invalidates all of that user's active sessions/tokens.
- Returns 200 with a simple confirmation body on success (e.g. `{"message": "Logged out"}`).
- If the Cognito call fails (e.g. token already invalid, network error), return an appropriate error status (502 for a Cognito-side failure, 401 if the token was already invalid) with a generic message, do not leak AWS error internals to the client.

## Non-functional requirements

- Never log the full token, only log that a request succeeded or failed and why (in general terms, e.g. "token verification failed: expired").
- JWKS keys must be cached, not fetched per-request.
- No secrets (Cognito keys, AWS credentials) are ever returned in any response body.
- This code must work identically regardless of whether the original login was via password, OTP, or Google, since token structure and verification are the same across all three.

## Acceptance criteria

- [ ] A valid, unexpired token from a real Cognito test user returns 200 from `GET /auth/me` with correct claims.
- [ ] A missing Authorization header returns 401 from `GET /auth/me`.
- [ ] An expired or tampered token returns 401 from `GET /auth/me`.
- [ ] `POST /auth/logout` with a valid token returns 200, and the same token can no longer be used successfully afterward.
- [ ] JWKS fetch happens once and is reused across multiple requests (verify via a log line or debugger, not by re-fetching every call).