## Social Sign‑In (Google & GitHub) – Implementation Plan

This document outlines how to add “Sign in with Google” and “Sign in with GitHub” to AI Collab Online using OAuth 2.0/OpenID Connect, without changing any code yet.

### Goals
- Let users sign in/up with Google or GitHub in addition to password auth
- Support account linking (attach a provider to an existing user)
- Preserve secure flows (state, HTTPS, exact redirect URIs)

---

## Google (OpenID Connect)

### Scopes
- `openid email profile` (minimum)

### Required environment variables
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` (e.g., `https://collab.up.railway.app/auth/google/callback`)

### Redirect URIs to register in Google Cloud Console
- Production: `https://collab.up.railway.app/auth/google/callback`
- Local dev (optional): `http://localhost:5000/auth/google/callback`

### Routes
- `GET /auth/google/login` → starts the OAuth flow (builds auth URL, sets `state`)
- `GET /auth/google/callback` → validates `state`, exchanges code for tokens, verifies ID token, extracts email/name/photo

### Mapping to users
- If logged in and initiating “connect”: link Google (`google_id`) to the current user
- If logged out:
  - If email exists on a password account → either auto-link after password confirmation or prompt to link
  - Else create a new user with `google_id`, `email`, `display_name`

### Security considerations
- Enforce exact redirect URIs and HTTPS
- Validate `state` param
- Verify `email_verified` claim for Google
- Handle token errors/refresh gracefully

---

## GitHub

### Scopes
- `read:user user:email`

### Required environment variables
- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_REDIRECT_URI` (e.g., `https://collab.up.railway.app/auth/github/callback`)

### Redirect URIs to register in GitHub OAuth App
- Production: `https://collab.up.railway.app/auth/github/callback`
- Local dev (optional): `http://localhost:5000/auth/github/callback`

### Routes
- `GET /auth/github/login` → starts OAuth
- `GET /auth/github/callback` → exchanges code for token, fetches primary verified email, name

### Mapping to users
- If logged in: link `github_id`
- If logged out: match by email (verified), else create new user

### Security considerations
- Validate `state`
- Only use verified primary emails from GitHub API
- Guard against missing email scope (fallback prompt or failure)

---

## Account Linking Policy
- When a provider email matches an existing account:
  - Option A (safer default): require password login once to confirm linking
  - Option B (lower friction): auto-link if email verified by provider
- Allow manual “Connect Google/GitHub” from Profile to link additional providers

---

## UI/UX
- On Login/Register:
  - Add buttons: “Continue with Google”, “Continue with GitHub”
  - Maintain password login
  - Preserve `next` param for post-login redirect (allowlist internal paths)
- On Profile:
  - Show connected providers; allow disconnect

---

## Implementation Steps
1) Dependencies: prefer `Authlib` for OAuth/OIDC (lightweight, well‑maintained)
2) Provider clients: configure Google & GitHub with client id/secret and redirect URIs
3) Routes:
   - `/auth/google/login`, `/auth/google/callback`
   - `/auth/github/login`, `/auth/github/callback`
4) User model: add `google_id`, `github_id` (nullable, unique) and provider metadata fields
5) Session/auth: integrate with existing session mechanism; set logged‑in user on success
6) Linking logic: if logged in, attach provider; if not, match by email or create
7) UI: add provider buttons to login/register; add “Connect”/“Disconnect” in Profile
8) Redirect safety: sanitize and allowlist `next` redirects
9) Logging/Audit: log provider, user, timestamps; error reasons (no PII in logs)
10) Tests: provider callback happy path, invalid state, missing email, existing email linking, disconnect

---

## Risks & Safety Precautions
- **Email collision**: a provider email matches an existing password account
  - Mitigation: require password confirmation for linking or email confirmation link
- **Unverified email** (GitHub): provider may return unverified email
  - Mitigation: only accept verified primary emails; prompt otherwise
- **Redirect abuse** (`next` param): open redirect risk
  - Mitigation: allowlist internal paths or require same‑origin; default to dashboard
- **Token/security errors**: expired/invalid codes or tokens
  - Mitigation: robust error handling; replay protection via `state`; time‑boxed sessions; HTTPS only
- **Privacy**: storing provider IDs and avatars
  - Mitigation: store minimal data; allow unlinking; document in Privacy Policy
- **Rate limiting**: protect login endpoints
  - Mitigation: apply light per‑IP rate limits; CAPTCHA if suspicious

---

## Testing Checklist
- Google login → new user created with verified email
- GitHub login → verified primary email retrieved; new user created
- Existing user linking (logged in) → provider attached; no duplicate users
- Email collision flow → linking requires confirmation; no silent takeover
- `next` redirect stays on same origin; falls back safely when invalid
- Disconnect providers works and leaves password login intact

---

## Ops Notes
- Exact redirect URIs must match provider app settings
- Configure env vars in Railway for production and in `.env` for local
- Keep a rollback path (feature flag) to hide buttons if a provider has an outage


