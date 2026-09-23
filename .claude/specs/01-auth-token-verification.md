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

Role (customer vs electrician) is represented via Cognito Groups, not a custom attribute. Two groups exist on the User Pool: `customer` and `electrician`. A user's group membership appears in their token as the `cognito:groups` claim (a list of group names). This spec only surfaces that claim, it does not yet enforce anything based on it, enforcement is a later, separate spec.

Cognito issues two different tokens after login, and they are not interchangeable:
- **ID token** — carries identity/profile claims (`sub`, `email`, `cognito:groups`, etc). Use this for anything that answers "who is this user."
- **Access token** — carries session/authorization claims (`scope`, `client_id`, `token_use`), deliberately does not carry profile info. Use this for calling AWS APIs on the user's behalf, such as Cognito's `global_sign_out`.

The Android app receives both from Amplify on every login and must send the correct one to each endpoint below.

## Inputs / Configuration

Read from `.env` via `app/core/config.py` (already implemented):
- `COGNITO_USER_POOL_ID`
- `COGNITO_APP_CLIENT_ID`
- `AWS_REGION`

Incoming requests to protected routes must include:
- `Authorization: Bearer <token>` header
- `GET /auth/me` expects an **ID token**
- `POST /auth/logout` expects an **access token**

## Behavior

### Token verification (`app/core/security.py`)

1. On first use, fetch Cognito's public JWKS (JSON Web Key Set) asynchronously from:
   `https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json`
2. Cache the fetched keys in memory (global variable). Do not re-fetch on every request. Once cached, reuse the cached keys for all subsequent token verifications.
3. For each incoming token, extract its unverified header to get the `kid` (key ID) and find the matching key in the cached set.
4. If the matching key is not found in the cached set, immediately return 401 (do not re-fetch; a missing key indicates an invalid or revoked token).
5. Verify the incoming token using `python-jose` (jose library) with the matched public key:
   - Signature is valid against the public key
   - Token is not expired (`exp` claim, verified automatically by jwt.decode)
   - `iss` (issuer) matches the expected Cognito User Pool URL exactly
   - `token_use` claim matches what's expected for this route: `id` for ID-token routes, `access` for access-token routes. Reject if it doesn't match, this stops an access token from being used where an ID token is required, and vice versa.
   - For an ID token, manually verify `aud` matches `COGNITO_APP_CLIENT_ID` (disable automatic verification with `options={"verify_aud": False}` during jwt.decode, then check manually). For an access token, manually verify `client_id` matches `COGNITO_APP_CLIENT_ID` (access tokens don't have an `aud` claim on Cognito).
6. On success, return the decoded claims dict. For an ID token, this includes `sub`, `email` if present, `cognito:groups` if present. `cognito:groups` is a list (e.g. `["electrician"]`) reflecting which Cognito Group(s) the user belongs to, this is how role is represented, there is no `custom:role` attribute on this pool. For an access token, claims are more limited (`sub`, `scope`, `client_id`), which is expected and fine since it's only used for the logout call.
7. On any failure (expired, malformed, bad signature, wrong audience/issuer, wrong token_use, missing header, key not found), raise an `HTTPException` with status 401 and a generic message ("Invalid or expired token"). Do not leak details about which specific check failed. Log failures at INFO level in general terms (e.g., "token verification failed: expired", "token verification failed: key not found").
8. Expose reusable FastAPI dependencies:
   - `get_current_user(authorization: Optional[str] = Header(None))` — requires and verifies an ID token, for routes that need identity/profile info. Returns decoded claims dict.
   - `get_current_access_token(authorization: Optional[str] = Header(None))` — requires and verifies an access token, for routes that need to call an AWS API on the user's behalf. Returns decoded claims dict.
   Both share the same underlying verification logic, they only differ in which `token_use` they require.

### `GET /auth/me` (`app/api/routes/auth.py`)

- Protected by the `get_current_user` dependency, which requires and verifies an **ID token**.
- Returns the decoded claims from the token as the response body: `sub`, `email` (if present), `cognito:groups` (if present).
- Returns 401 if the token is missing, malformed, is an access token instead of an ID token, or otherwise fails verification (handled by the dependency itself).

### `POST /auth/logout` (`app/api/routes/auth.py`)

- Protected by the `get_current_access_token` dependency, which requires and verifies an **access token** (must be valid and currently-active to log out).
- Takes the caller's access token (from the Authorization header) and calls Cognito's `global_sign_out` via `boto3`, which invalidates all of that user's active sessions/tokens.
- Returns 200 with a simple confirmation body on success (e.g. `{"message": "Logged out"}`).
- Returns 401 if the token is missing, malformed, is an ID token instead of an access token, or otherwise fails verification.
- If the Cognito call itself fails (e.g. token already invalid, network error), return an appropriate error status (502 for a Cognito-side failure) with a generic message, do not leak AWS error internals to the client.

## Non-functional requirements

- Never log the full token, only log that a request succeeded or failed and why (in general terms, e.g. "token verification failed: expired").
- JWKS keys must be cached, not fetched per-request.
- No secrets (Cognito keys, AWS credentials) are ever returned in any response body.
- This code must work identically regardless of whether the original login was via password, OTP, or Google, since token structure and verification are the same across all three.

## Acceptance criteria

- [ ] A valid, unexpired **ID token** from a real Cognito test user returns 200 from `GET /auth/me` with response body containing `sub` (non-null), `email` (null if not in token), and `cognito_groups` (null if not in token, otherwise a list of group names).
- [ ] Sending a valid **access token** to `GET /auth/me` returns 401 with detail "Invalid or expired token" (token_use mismatch).
- [ ] A missing Authorization header returns 401 with detail "Invalid or expired token" from `GET /auth/me`.
- [ ] A malformed Authorization header (e.g., missing "Bearer" prefix or wrong format) returns 401 with detail "Invalid or expired token".
- [ ] An expired token returns 401 with detail "Invalid or expired token".
- [ ] A token with invalid signature returns 401 with detail "Invalid or expired token".
- [ ] A token whose `aud` claim (for ID token) or `client_id` claim (for access token) doesn't match the configured `COGNITO_APP_CLIENT_ID` returns 401 with detail "Invalid or expired token".
- [ ] A token with `kid` (key ID) that doesn't match any key in the cached JWKS returns 401 with detail "Invalid or expired token" (no re-fetch attempted).
- [ ] `POST /auth/logout` with a valid, currently-active **access token** returns 200 with response body `{"message": "Logged out"}`, and that same access token can no longer be used successfully afterward (calling Cognito's `global_sign_out` invalidates it).
- [ ] Sending a valid **ID token** to `POST /auth/logout` returns 401 with detail "Invalid or expired token" (token_use mismatch).
- [ ] JWKS is fetched asynchronously once on first use and cached in memory, reused for all subsequent requests without re-fetching (verify by observing a single JWKS fetch on startup, then no additional fetches during multiple requests).
- [ ] If Cognito's `global_sign_out` fails with `NotAuthorizedException`, return 401 with detail "Invalid or expired token".
- [ ] If Cognito's `global_sign_out` fails with any other error, return 502 with detail "Service temporarily unavailable" (do not leak AWS error codes to the client).