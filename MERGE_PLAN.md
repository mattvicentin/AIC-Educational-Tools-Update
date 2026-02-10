# Update Plan: Chat Layout + Educational Tools (Live Railway Repo)

## Summary
- Treat this as a normal update, not a repo transplant.
- Use a shared remote branch workflow across both laptops.
- Enforce strict file-delta discipline so identical files remain untouched.
- Reconcile Alembic heads safely without deleting revision files.
- Deploy with manual migrations and verify with targeted smoke tests.

## Two-Remote Model (Two Laptops)
1. Laptop A (source machine with latest feature work):
   ```bash
   git checkout update/chat-layout-edu-tools
   git push -u tools update/chat-layout-edu-tools
   ```
2. Laptop B (live/implementation machine used by Cursor):
   ```bash
   git remote add live <LIVE_REPO_URL>
   git remote add tools <TOOLS_REPO_URL>
   git fetch live
   git fetch tools
   ```
3. Branch roles:
- `live/*` is the production merge target and deployment source.
- `tools/*` contains feature updates prepared for merge.

This removes local-path remotes and ensures cross-machine consistency.

## Cursor Safety Rails (Must Follow)
- Only modify files required for the feature delta.
- Do not run repo-wide formatters.
- No whitespace-only edits.
- No renames unless explicitly required.
- Do not edit files that are functionally unchanged.
- Every change must map to a checklist item, failing behavior, or failing test.
- After each Cursor iteration, run:
  ```bash
  git diff --stat
  git diff --name-only
  git diff
  ```

## Public API/Schema Changes
- New API routes:
  - `POST /api/quiz/generate`
  - `POST /api/quiz/<id>/grade`
  - `GET /api/quiz/<id>`
  - `POST /api/flashcards/generate`
  - `POST /api/mindmap/generate`
  - `POST /api/narrative/generate`
  - `POST /api/narrative/feedback`
- New DB tables:
  - `quiz`, `quiz_answer`, `flashcard_set`, `flashcard_session`, `mindmap`
- Schema change:
  - `quiz.difficulty` column (default `average`)
- Frontend asset dependency:
  - ELK.js for mind map layout

## Plan
1. Prepare the live repo and create rollback safety.

   Commands:
   ```bash
   git checkout -b integration/edu-tools-update live/main
   git config rerere.enabled true
   git status -sb
   git tag -a pre-edu-tools-update-YYYY-MM-DD -m "Pre chat-layout + edu tools update"
   ```

2. Pull the shared feature branch and verify expected update scope.

   Commands:
   ```bash
   git fetch live
   git fetch tools
   git merge-base live/main tools/update/chat-layout-edu-tools
   git diff --stat live/main...tools/update/chat-layout-edu-tools
   git diff --name-only live/main...tools/update/chat-layout-edu-tools
   ```
   If merge-base is missing, do not use a normal merge. Use a controlled cherry-pick/replay flow instead.
   If changed files are unexpectedly broad, stop and resolve branch mismatch before merging.

3. Merge feature work into the integration branch.

   Commands:
   ```bash
   git merge --no-ff tools/update/chat-layout-edu-tools
   ```
   Expected conflict hotspots:
   - `templates/chat/view.html`
   - `templates/base.html`
   - `src/app/__init__.py`
   - `src/app/static/css/components.css`
   - `src/app/static/js/chat-view.js`

4. Enforce delta-only conflict resolution.

   Commands:
   ```bash
   git status
   git diff --name-status
   git diff --check
   ```
   Keep the online version when files are functionally identical.

5. Reconcile Alembic heads safely (no revision deletion).

   Commands:
   ```bash
   alembic heads
   alembic history --verbose
   alembic current
   ```
   Required actions:
   - Do not delete existing migration files as a first option.
   - For duplicate flashcard revisions (`bc1234567890` and `cd2345678901`), convert migration logic to idempotent table-existence checks so both paths are safe.
   - If multiple heads remain, create a merge revision:
     ```bash
     alembic merge -m "merge flashcard heads" <head_a> <head_b>
     ```
   - Re-run `alembic heads` and confirm a single head in code.

6. Make `quiz` migration path safe for all environments.

   Required actions:
   - Ensure `quiz` and `quiz_answer` creation exists before `afbd40f1e68c_add_difficulty_to_quiz.py`, or make `afbd40f1e68c` safely no-op if `quiz` is absent.
   - Validate both fresh DB migration and upgrade-from-live behavior.

7. Standardize CSRF handling with shared JS helper.

   Required actions:
   - Add one shared helper module (for example `src/app/static/js/tool-api.js`) with:
     - `getCsrfToken()`
     - `jsonFetch(url, payload, options)` that always adds `X-CSRFToken`
   - Refactor:
     - `src/app/static/js/quiz-tool.js`
     - `src/app/static/js/flashcards-tool.js`
     - `src/app/static/js/mindmap-tool.js`
     - `src/app/static/js/narrative-tool.js`
   - Remove duplicated per-file CSRF logic.

8. Make ELK.js production-safe.

   Preferred action:
   - Vendor `elk.bundled.js` into static assets (for example `src/app/static/vendor/elk.bundled.js`) and load locally from template.
   Fallback:
   - Keep pinned CDN URL only if vendoring is blocked, and keep CSP narrowly scoped.

9. Validate backend/frontend wiring after merge.

   Backend checks:
   - `src/app/__init__.py` blueprint registration for quiz/flashcards/mindmap/narrative
   - `src/models/__init__.py` model imports
   - Runtime env includes `ANTHROPIC_API_KEY`

   Frontend checks:
   - `templates/chat/view.html` tool menu + panel includes
   - `templates/components/quiz/quiz_panel.html`
   - `templates/components/flashcards/flashcards_panel.html`
   - `templates/components/mindmap/mindmap_panel.html`
   - `templates/components/narrative/narrative_panel.html`
   - Cache-busting query strings are updated for changed assets

10. Use PR gate even for solo merge.

   Commands:
   ```bash
   git push -u live integration/edu-tools-update
   ```
   Required action:
   - Open PR `integration/edu-tools-update -> main` in the `live` repository.
   - Review file list and diff size before merge.
   - Merge only after smoke tests pass.

11. Deploy with manual migrations.

   Actions:
   - Set `RUN_DB_MIGRATIONS_ON_STARTUP=false` in Railway.
   - Deploy merged code.
   - Run:
     ```bash
     railway run alembic upgrade head
     ```
   - Verify `/ready` reports ready status and no migration errors.

12. Execute smoke tests in production (or staging first if available).

   Checks:
   - Chat page renders new layout and sidebar behavior.
   - Tools menu opens and each tool completes end-to-end flow.
   - Quiz can generate, grade, and send results to chat.
   - Flashcards can generate and "Generate More" works.
   - Mind map renders and exports.
   - Narrative linear and interactive flows complete and send to chat.
   - Library document selection works in all tools.
   - No CSP, CSRF, or static-asset console/network errors.

## Rollback
- If deployment regresses:
  - Redeploy `pre-edu-tools-update-YYYY-MM-DD` tag or last known good commit.
  - Keep `RUN_DB_MIGRATIONS_ON_STARTUP=false`.
  - Re-run migration plan only after root cause is identified.

## Test Cases and Scenarios
- `GET /health` returns `200`.
- `GET /ready` returns `"status": "ready"` after deploy + migrations.
- `POST /api/quiz/generate` succeeds with `chat_id` + `context_mode=chat`.
- `POST /api/flashcards/generate` returns cards and session/cursor data.
- `POST /api/mindmap/generate` returns valid `mind_map_data`.
- `POST /api/narrative/generate` returns valid linear and interactive payloads.
- Tool panels open/close correctly (escape, backdrop, toolbar trigger).
- No missing static assets (`404`) for new JS/CSS/vendor files.

## Assumptions and Defaults
- `live` remote points to the production/online repository.
- `tools` remote points to `AIC-Educational-Tools-Update`.
- Feature branch name is `update/chat-layout-edu-tools`.
- Integration branch name is `integration/edu-tools-update`.
- Manual migrations are required on Railway for this rollout.
- ELK.js will be served locally unless blocked by deployment constraints.
