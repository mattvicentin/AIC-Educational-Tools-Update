# Merge Plan: Chat Layout + Educational Tools

## Summary
- Merge this repo into the live Railway repo via Git merge on an integration branch.
- Resolve Alembic multiple heads and ensure quiz/flashcards/mindmap schemas are safe for Postgres.
- Integrate chat layout + tool UI assets and backend blueprints/models.
- Add CSRF headers for tool API fetches to avoid production CSRF failures.
- Deploy with manual migrations, then run targeted smoke tests.

## Precaution: Preserve Matching Files
- Because the two repos are largely identical, **any file that is identical between repos should be left untouched** (no edits, no reformatting, no changes in whitespace).
- During merge conflict resolution, always prefer the **current online version** for files that are functionally the same, and only apply changes where this repo clearly introduces new behavior or fixes.
- Use `git diff`/`git status` and conflict tools to confirm that only intended files are modified.

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
- CSP dependency:
  - `https://unpkg.com` for ELK.js in `templates/chat/view.html` and `src/app/__init__.py`

## Plan
1. Create an integration branch in the live repo and confirm shared history.

   Commands:
   ```bash
   git checkout -b merge/chat-layout-edu-tools
   git remote add feature /path/to/this/repo
   git fetch feature
   git merge-base HEAD feature/main
   ```
   If no merge-base is found, stop and revisit; the Git-merge path assumes shared history.

2. Merge feature branch and resolve known conflict hot spots **without touching identical files**.

   Commands:
   ```bash
   git merge feature/main
   ```
   Likely conflicts:
   - `templates/chat/view.html`
   - `templates/base.html`
   - `src/app/__init__.py`
   - `src/app/static/css/components.css`
   - `src/app/static/js/chat-view.js`

3. Resolve Alembic multiple heads before running migrations.

   Required adjustment:
   - Keep one flashcard migration and remove the duplicate.
   - Recommended: keep `migrations/versions/cd2345678901_add_flashcard_tables.py`, remove `migrations/versions/bc1234567890_add_flashcard_tables.py`.
   - Confirm `migrations/versions/de3456789012_add_mindmap_table.py` points to the kept flashcard revision.

   Commands:
   ```bash
   alembic heads
   alembic history --verbose
   ```
   Goal: a single head.

4. Verify the quiz table exists before `afbd40f1e68c` runs in Postgres.

   Required adjustment (choose one):
   - Add a migration that creates `quiz` and `quiz_answer` tables if they don’t exist.
   - Or update `migrations/versions/afbd40f1e68c_add_difficulty_to_quiz.py` to no-op safely if `quiz` table is missing in Postgres.

   Rationale: current migration adds a column and will fail if `quiz` doesn’t exist.

5. Backend wiring checks.

   Confirm these are merged and consistent:
   - Blueprint registration in `src/app/__init__.py`
   - Model imports in `src/models/__init__.py`
   - New blueprints in `src/app/quiz`, `src/app/flashcards`, `src/app/mindmap`, `src/app/narrative`
   - CSP includes `https://unpkg.com` in `src/app/__init__.py`
   - Environment has `ANTHROPIC_API_KEY` set (already required by Library tool)

6. Frontend wiring checks.

   Confirm these are merged and referenced:
   - `templates/chat/view.html` includes tool menu and panel includes
   - `templates/components/quiz/quiz_panel.html`
   - `templates/components/flashcards/flashcards_panel.html`
   - `templates/components/mindmap/mindmap_panel.html`
   - `templates/components/narrative/narrative_panel.html`
   - New assets in `src/app/static/js` and `src/app/static/css`
   - Cache-bust query strings in `templates/base.html` and `templates/chat/view.html` match updated assets

7. Add CSRF headers to tool API fetches.

   Required adjustment:
   - Include `X-CSRFToken` (or `X-CSRF-Token`) header on JSON fetches in:
     - `src/app/static/js/quiz-tool.js`
     - `src/app/static/js/flashcards-tool.js`
     - `src/app/static/js/mindmap-tool.js`
     - `src/app/static/js/narrative-tool.js`
   - Use the existing meta tag `csrf-token` from `templates/base.html` as the source.

   This avoids 400 CSRF failures in production.

8. Deploy with manual migrations (per selected strategy).

   Actions:
   - Set `RUN_DB_MIGRATIONS_ON_STARTUP=false` in Railway.
   - Deploy code.
   - Run:
     ```bash
     railway run alembic upgrade head
     ```
   - Verify `/ready` is green and no migration errors appear.

9. Smoke test on staging or production.

   Check:
   - Chat page renders new layout and sidebar accordions.
   - Tools menu opens and each tool works end-to-end.
   - Quiz grades and sends results to chat.
   - Flashcards generate and “Generate More” works.
   - Mind map renders with ELK and exports.
   - Narrative linear and interactive flows complete and send to chat.
   - Library document selection works inside tools.
   - No CSP or CSRF errors in console/network logs.

## Test Cases and Scenarios
- `GET /health` returns 200.
- `GET /ready` returns `"status": "ready"` after migration.
- `POST /api/quiz/generate` with `chat_id` and `context_mode=chat` succeeds.
- `POST /api/flashcards/generate` returns cards and session info.
- `POST /api/mindmap/generate` returns `mind_map_data`.
- `POST /api/narrative/generate` returns linear and interactive responses.
- Tool UI closes properly on escape and backdrop.
- No 404s for new static assets.

## Assumptions and Defaults
- Shared Git history exists between this repo and the live repo.
- Manual migrations are used on Railway for this deployment.
- Tools are fully enabled in UI (no feature flag).
- `ANTHROPIC_API_KEY` is available in production.
- CSP allows `https://unpkg.com` for ELK.js.
