## DB-backed trial mode (Option 2)

Purpose: Allow anonymous visitors to try the app (e.g., create 1 room, 1 chat, send up to N messages) without registration, with limits enforced server-side. On signup, migrate guest-created content to the new account.

### Goals
- Let users experience value before signup
- Prevent easy evasion (incognito/cookie clearing)
- Keep storage and cost bounded
- Clean upgrade path from guest → registered user

### High-level design
- New `TrialSession` row tracks a trial’s counters, status, and expiry
- Anonymous visitors get a signed `trial_id` cookie mapped to `TrialSession`
- Server enforces limits on create/send endpoints; read-only remains open
- On signup, content created under `trial_id` is adopted into the user account

### Data model (new + changes)
- `trial_session` (new)
  - `id` (UUID/PK), `created_at`, `expires_at` (e.g., now + 7 days)
  - `ip_address`, `user_agent_hash` (light correlation only)
  - `rooms_created`, `chats_created`, `messages_sent`
  - `status` (active, exhausted, expired, adopted)
- Content linkage (nullable, indexed):
  - `room.trial_session_id`
  - `chat.trial_session_id`
  - `message.trial_session_id` (optional)

Alembic migration:
- create `trial_session`
- add `trial_session_id` columns
- add indexes on `trial_session_id`

### Session lifecycle
- On first anonymous visit:
  - create a `TrialSession`, set signed httpOnly `trial_id` cookie
  - default caps via env (e.g., TRIAL_MAX_ROOMS=1, TRIAL_MAX_CHATS=1, TRIAL_MAX_MSG=6)
- Per request:
  - resolve `TrialSession` by cookie; if missing, attempt IP+UA lookup (best-effort only)
  - if expired/exhausted → block writes; allow read-only

### Enforcement points
- Decorator `@require_trial_or_login(caps=...)`
  - If logged-in: pass
  - If guest: check `TrialSession` counters vs caps
  - On success: perform action, increment counters, persist `trial_session_id` on created rows
  - On exceed: 403 JSON or redirect with CTA to register
- Apply to:
  - POST /room/create (cap rooms)
  - POST /room/<id>/chat/create (cap chats)
  - POST /chat/<id> (cap messages)
  - Optional: AI endpoints with rate-limits (to control spend)

### UX
- Banner in navbar/pages: “Trial: X messages remaining” + Register button
- When cap hit: modal explaining limits and benefits of registering, disable further writes
- Keep viewing allowed so links don’t dead-end

### Upgrade path (guest → registered user)
- On signup while an active `trial_id` cookie is present:
  - Reassign ownership:
    - rooms: set `owner_id = user.id`
    - chats: set `created_by = user.id`
    - messages (optional): set `user_id` for trial-authored messages
  - Null out `trial_session_id` on migrated rows
  - Mark trial as `adopted` (and optionally expire it)
- Idempotent: if process runs twice, no duplicates

### Operational limits & cleanup
- Expire trials after N days (env-configurable)
- Background job (daily) to:
  - mark expired trials
  - optionally purge orphaned trial content after a grace period
  - aggregate metrics

### Safety precautions & abuse mitigation
- Server-side counters
  - Enforce on the backend; never trust client counters
  - Block writes when exceeded; always re-check on server
- Light correlation: IP + UA
  - Helps detect trivial abuse, but expect false positives with shared networks
  - Never use IP as identity; only as a signal
- Rate limiting & cost control
  - Add per-IP/window rate limits for POST endpoints (e.g., 10/min)
  - Add per-trial caps for AI endpoints (tokens/messages) to protect API spend
  - Fail closed on unusual spikes (return friendly error and show CTA)
- Resource caps
  - Limit max rooms/chats/messages per trial
  - Constrain message size and attachment types (if any)
- Content moderation (optional but recommended)
  - Apply basic filters or provider safety settings for AI prompts/outputs
  - Log flagged content for review (respecting privacy)
- Data privacy & PII
  - Avoid storing raw IPs long-term; consider hashing with salt and a short retention window
  - Document what is stored for trials (privacy policy)
  - Keep `trial_id` cookie signed, httpOnly, same-site
- Security & integrity
  - Ensure CSRF/CSRF-exemptions consistent with anonymous POSTs
  - Validate ownership on read/write (trial or user must own content)
  - Use server-generated IDs; validate payload sizes and types
  - Do not allow trial accounts to access other users’ content by ID
- UX safety
  - Make the trial state clear to avoid user confusion when limits hit
  - Provide smooth registration flow; ensure no data loss on upgrade

### Risks & mitigations
- Incognito/device hopping to evade caps
  - Mitigation: DB-backed counters + light IP/UA correlation; keep caps low; rate limit writes
- Shared IP effects (schools/labs)
  - Mitigation: use trial counters first; IP controls as soft signals only
- DB growth from trial content
  - Mitigation: strict caps, expirations, scheduled cleanup
- Unexpected AI cost/spend
  - Mitigation: per-trial AI caps; global per-minute/hour circuit breakers; log and alert on spikes
- Legal/compliance
  - Update privacy policy (what is collected, retention, purpose)
  - Add Terms update noting trial limits and data handling
- Operational complexity
  - Keep migration logic simple and idempotent; write tests
  - Feature-flag the trial rollout; begin with small caps

### Implementation steps (summary)
1) Migration: add `trial_session` + `trial_session_id` columns
2) Helpers: create/resolve `TrialSession`, set cookie
3) Decorator: `@require_trial_or_login` with counter enforcement
4) Apply decorator to create/send endpoints; wire counter increments
5) UX: banner + modal; show counts; handle 403 responses
6) Adoption: transfer ownership on signup; mark session adopted
7) Limits & jobs: add rate limiting + daily cleanup
8) Docs: privacy/terms updates; admin metrics dashboard (optional)

### Config (env)
- TRIAL_ENABLED=true
- TRIAL_MAX_ROOMS=1
- TRIAL_MAX_CHATS=1
- TRIAL_MAX_MSG=6
- TRIAL_TTL_DAYS=7
- TRIAL_AI_MAX_REQUESTS=6 (optional)


