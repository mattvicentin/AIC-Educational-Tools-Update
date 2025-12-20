# Guest Trial Mode (Anonymous Usage)

This document outlines a safe, low‑friction trial that lets new visitors use the app without registering, with strict server‑enforced limits and a seamless upgrade path.

## Goals
- Let first‑time visitors try the core flow instantly.
- Protect costs with hard limits and rate limits.
- Seamless adoption of trial content after signup/login.
- Keep changes localized and reversible.

## Trial UX
- CTA: “Try without account”.
- Anonymous user can (defaults):
  - Create up to 1 room
  - Create up to 1 chat in that room
  - Send up to 10 messages (AI included)
  - Trial expires after 7 days
- Banner shows remaining messages and a Register/Login button.
- On limit: show modal; register → adopt content → continue.

## ENV Toggles
- `TRIAL_ENABLED=true`
- `TRIAL_MAX_ROOMS=1`
- `TRIAL_MAX_CHATS=1`
- `TRIAL_MAX_MESSAGES=10`
- `TRIAL_TTL_DAYS=7`
- `TRIAL_PER_IP_DAILY_MSGS=30`

## Data Model
- New table `trial_sessions`:
  - `id TEXT PK` (128‑bit random)
  - `created_at`, `last_seen_at`, `expires_at`
  - `rooms_used`, `chats_used`, `messages_used`
  - `ip_hash` (optional SHA‑256(IP+secret))
  - `adopted_by_user_id` (audit)
  - Indexes: `(expires_at)`, `(ip_hash)`
- Add nullable `trial_token TEXT` (indexed) on `Room`, `Chat`, `Message`.

## Token & Cookie
- On first anonymous action: generate random token, persist in `trial_sessions`, set cookie `trial_token` (Secure; SameSite=Lax). Cookie is not trusted by itself; DB is the source of truth.

## Server Enforcement
- On create room/chat/message:
  - If logged‑in → normal path.
  - Else → load trial session; check `expires_at` and counters; if over → 403 with signup CTA; else increment and set `trial_token` on the new row.
- Read/Write allowed if user owns/is member OR `resource.trial_token == cookie.trial_token`.

## Adoption on Auth (Seamless Upgrade)
- After login/register (and cookie present):
  - `UPDATE Room/Chat/Message SET user_id=:uid, trial_token=NULL WHERE trial_token=:t` (batched per table).
  - Mark `trial_sessions.adopted_by_user_id=:uid`, clear cookie, redirect back.

## Abuse & Cost Controls
- Rate‑limit POSTs by token and IP (e.g., 30/min token, 60/min IP) via `flask_limiter`.
- Daily per‑IP cap on trial AI messages (`TRIAL_PER_IP_DAILY_MSGS`).
- Max message length; basic content filters.
- Optional CAPTCHA on **trial room creation**.
- Disable invites for trial users (or set `TRIAL_MAX_INVITES=0`).
- Kill switch: `TRIAL_ENABLED=false`.

## Risks & Mitigations
- Cookie clearing → per‑IP/day caps + rate limiting.
- Token sharing → scope limited to that token’s content; caps remain.
- Cost spikes → strict message caps + kill switch.
- Data leakage → only show rows where `trial_token` matches; never rely on IDs alone.
- Adoption mistakes → idempotent updates; short audit trail to revert.

## Rollout & Testing
- Ship behind `TRIAL_ENABLED=false`; enable with conservative limits.
- Unit tests: counters/expiry/adoption and access checks.
- E2E: full trial → limit → signup → adoption flow.

## Minimal Code Touch Points
- New `src/app/trial.py` (session lifecycle, limit checks, adoption helpers).
- Migrations: `trial_sessions` + `trial_token` on `Room/Chat/Message`.
- Update create endpoints to enforce limits for anonymous users.
- Add `owns_via_trial(resource)` helper to guards.
- Trial banner partial shown when cookie present and session active.
