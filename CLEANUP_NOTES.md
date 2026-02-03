# Cleanup Notes

Date: 2026-02-03

## Removed (unused/obsolete)
- `src/app/static/js/chat-input-fixes.js`: no longer referenced (explicitly removed from `templates/base.html`), conflicts with current ResizeObserver approach.
- `src/app/static/css/.gitkeep`, `src/app/static/images/.gitkeep`: directories are populated; placeholders are no longer needed.
- `docs/SESSION-SUMMARY-2025-10-06.md`, `docs/DEPLOYMENT-SUCCESS-2025-10-28.md`, `docs/CLEANUP_SUMMARY_2025-10-26.md`: historical status notes not referenced by code or README.

## Code cleanup (no functional change)
- Removed debug-only inline scripts and localhost ingest calls from `templates/chat/view.html`.
- Removed debug logging/telemetry blocks from:
  - `src/app/static/js/flashcards-tool.js`
  - `src/app/static/js/tools-menu.js`
- Removed stale comment about a deleted script in `templates/base.html`.

## TODO (ambiguous usage)
- `test_ai_integration.py`: retained, but likely a developer-only script. Added `# TODO: verify usage`.
- `test_models.py`: retained, but likely a developer-only script. Added `# TODO: verify usage`.

## Notes
- No imports or runtime entry points were altered.
- Static asset references remain unchanged.
