## Feature Roadmap and Integration Notes

This document outlines upcoming enhancements and how to integrate them cleanly with the existing application.

### OpenAI Fallback for Mode Generation

Goal: When Anthropic returns transient errors (e.g., 529), automatically fail over to OpenAI before using template-based fallbacks.

- Suggested flow (augment current `generate_room_modes` / `get_modes_for_room` in `src/utils/openai_utils.py`):
  1. Attempt Anthropic (existing `call_anthropic_api` with retries/backoff).
  2. On failure, attempt OpenAI (new `call_openai_api`).
  3. On failure, run `infer_template_type_from_goals` (already in `src/app/room/utils/room_utils.py`).
  4. If no confident inference, use `BASE_TEMPLATES["academic_essay"]` as last resort.

- Config (add to `.env` / Railway variables):
  ```
  OPENAI_API_KEY=sk-...
  OPENAI_MODEL=gpt-4o-mini  # or gpt-4o, gpt-4.1, etc.
  AI_FAILOVER_ORDER=anthropic,openai,templates
  ```

- Implementation notes:
  - Add `call_openai_api(prompt: str) -> str` in `src/utils/openai_utils.py` (or a sibling helper file) to standardize responses like Anthropic handlers.
  - Keep existing backoff logic; reuse for OpenAI to avoid code duplication.
  - Preserve current mode JSON schema and normalization so downstream code remains unchanged.

### External Invites (Non-Registered Emails)

Goal: Allow inviting people who are not yet registered by sending a secure, expiring link that onboards them and adds them to the room.

- Flow overview:
  - Creation: In `src/app/room/routes/invitations.py`, if email does not map to a user, create a signed token (itsdangerous) containing `room_id`, `email`, `inviter_id`, `exp`.
  - Email: Use `src/utils/email.py` to send an invite email with `accept` link.
  - Accept: New route `GET /room/accept-invite?token=...` (in room blueprint) decodes token, then:
    - If user is logged in: add membership, set `accepted_at`.
    - If not: redirect to `register` with token preserved; after successful signup/login, finalize membership and redirect to room.

- Security & persistence:
  - Use `itsdangerous.URLSafeTimedSerializer` with `INVITE_TOKEN_SECRET` and `INVITE_TOKEN_TTL_MINUTES`.
  - Optional one-time use: store token `jti` in DB to mark as consumed (can be added later if needed).

- Config:
  ```
  INVITE_TOKEN_SECRET=change-me
  INVITE_TOKEN_TTL_MINUTES=10080  # 7 days
  ```

- UI updates:
  - `templates/room/invite.html`: Clarify that non-registered emails will receive a signup link; keep username invite path unchanged.
  - Show distinct success messages for existing users vs external invites.

### Daily Email Reports (Admin)

Goal: Send a daily activity report to admins via email.

- Generator:
  - Create a utility `src/utils/reports.py` to compute aggregates (users, rooms, chats, new signups, active rooms, etc.).
  - Reuse queries currently backing `/admin/users` (see `src/app/admin.py`).

- Route:
  - `POST /admin/reports/send-daily?token=...` (protected by `@require_admin` and a shared secret for scheduler calls).
  - Use `send_email` from `src/utils/email.py` to email `ADMIN_REPORT_RECIPIENTS`.

- Scheduling (Railway):
  - Add a Cron task to `railway.toml` or Service → Schedules that hits the route daily with the secret token.

- Config:
  ```
  ADMIN_REPORT_RECIPIENTS=admin@example.com,ops@example.org
  REPORTS_CRON_TOKEN=change-me
  ```

### Template Improvements

Goal: Improve quality and coverage of deterministic templates and their inference.

- Expand base templates and rubrics:
  - Update `BASE_TEMPLATES` in `src/utils/openai_utils.py` to include more modes and richer rubric criteria.
  - Ensure each template has consistent step keys (`step_1`..`step_n`) and labels.

- Improve inference:
  - Enhance `infer_template_type_from_goals` in `src/app/room/utils/room_utils.py`:
    - Add richer keyword/phrase lists per template.
    - Support multi-word phrases and simple regex matching.
    - Consider scoring by frequency and proximity; pick top-scoring template above a threshold.

- UI affordance:
  - In `templates/room/learning_steps.html`, display the inferred template name (if any) and a small dropdown to override template before generation.
  - Persist the chosen template through the request so the first AI call (or fallback) aligns with user intent.

- Tests:
  - Add tests under `tests/` to validate inference decisions and fallback order (Anthropic → OpenAI → templates).

### Environment Summary

Add (or verify) the following variables in `.env` / Railway variables:

```
# AI providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
AI_FAILOVER_ORDER=anthropic,openai,templates

# Invites
INVITE_TOKEN_SECRET=change-me
INVITE_TOKEN_TTL_MINUTES=10080

# Reports
ADMIN_REPORT_RECIPIENTS=admin@example.com
REPORTS_CRON_TOKEN=change-me
```

### Files to Touch (at a glance)

- `src/utils/openai_utils.py`: OpenAI client call + failover orchestration, expand `BASE_TEMPLATES`.
- `src/app/room/utils/room_utils.py`: Improve `infer_template_type_from_goals`.
- `src/app/room/routes/invitations.py`: External invite branch and email.
- `src/app/room/__init__.py`: Add `accept-invite` route wiring if placed here.
- `src/utils/email.py`: Invite email content for external users; daily report email.
- `src/utils/reports.py` (new): Aggregate data for daily report.
- `src/app/admin.py`: Add route to trigger daily report send.
- `templates/room/invite.html`: Clarify external invites UX.
- `templates/room/learning_steps.html`: Show inferred template and allow override.


