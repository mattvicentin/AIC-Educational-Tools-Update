### Incident Report: Threaded Comment Replies Attempt

- **Date/Time**: 2025-09-12
- **Scope**: Chat comments system
- **Impact**: Temporary 500 on chat view for some users until rollback completed

### Summary
We attempted to introduce 1‑level threaded replies to comments by adding a `parent_comment_id` to `Comment`. The application began failing to load the chat view in production (generic error page). The likely cause was a schema mismatch where the application code referenced the new column before the migration had applied to the production database and all workers. We rolled back template/route/model usage to restore stability while leaving a migration file in the repo for a later, controlled rollout.

### What changed (before rollback)
- Model (`src/models/chat.py`)
  - Added `parent_comment_id` (nullable, FK to `comment.id`) and a `replies` relationship.
- Backend route (`src/app/chat.py`)
  - `POST /chat/<id>/comment` accepted optional `parent_comment_id`.
- Template (`templates/chat/view.html`)
  - Rendered top‑level comments and nested replies; switched “Add Comment” inline handlers to delegated JS.

### Observed failure
- Chat page returned the “An error occurred while loading the chat” fallback.
- No obvious deploy/console error surfaced to the user.
- Most likely a schema mismatch while the app expected `parent_comment_id`.

### Root cause candidates
1) Migration timing/race
   - Workers started with new code while the DB still had the old `comment` schema (no `parent_comment_id`).
   - Gunicorn multi‑worker startup could have interleaved migration and request handling.
2) Template access
   - Template logic referenced `comment.parent_comment_id` prior to guards; if the ORM mapping/column wasn’t present, it could throw.
3) Alembic environment
   - Migration may not have run (or not completed) before traffic hit updated workers.

### Mitigations attempted
- Added Alembic migration `9f1a2b3c4d5e_add_parent_comment_id_to_comment.py` (column + index + FK).
- Defensive code:
  - Wrapped comments query in try/except; if loading failed, render the chat without comments (avoids 500).
  - Guarded template loops to handle undefined `parent_comment_id`.
- Despite these, persistent failures were reported, so we performed a quick rollback to protect users.

### Rollback
- Model: removed reply relationships and `parent_comment_id` usage.
- Route: ignored `parent_comment_id`; reverted to flat comments.
- Template: reverted to rendering flat comment list; removed reply UI.
- Migration file remains in repo but is not required by current code.

Result: Chat loads normally; users unblocked.

### Lessons / Recommendations
- Ship schema changes behind a feature flag:
  1. Deploy the migration first (no code path requires it).
  2. Deploy code that can read/write the new data only when a flag is on; keep templates using backend‑computed view models.
  3. Enable the flag gradually after confirming migrations completed.
- Control migration timing:
  - Run migrations in a prestart job or CI/CD step before app instances receive traffic.
  - Use readiness checks to ensure the app is healthy post‑migration before switching traffic.
- Template safety:
  - Avoid direct template access of newly introduced nullable/optional fields on the first deploy. Prefer computed view models returned by the server.
- Observability:
  - Add targeted logging around comments render path to quickly pinpoint schema vs logic failures in production.

### Next steps (if we retry threaded replies)
1. Re‑introduce `parent_comment_id` under a feature flag.
2. Deploy migration separately; confirm apply.
3. Update backend to assemble a safe view model (`top_level_comments`, `replies_by_parent`) so templates don’t touch raw optional attrs.
4. Canary enable in a room, monitor logs, then ramp.

### Current state
- Chat is stable with flat comments.
- The migration file exists but is not required; if applied, it’s harmless since current code ignores the column.


