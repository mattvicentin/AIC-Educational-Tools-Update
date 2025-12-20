# Chat Module Slimming Plan

**Status**: Proposed  
**Date**: December 2025  
**Problem**: `src/app/chat.py` is ~960 lines and mixes multiple concerns (view, comments, pins, exports, progression). This makes changes risky and hard to reason about.

---

## Goals
- Reduce surface area per file for readability and safer edits.
- Group related routes/helpers (e.g., pins) so future changes don’t touch core chat view.
- Keep templates modular to avoid bloat in `chat/view.html`.

---

## Proposed Breakout

1) **Pins**  
   - New blueprint file: `src/app/chat_pins.py` (or `src/app/pins.py`)  
   - Routes: pin/unpin, update visibility (share/unshare), list pins (`/pin`, `/pin/<id>`, `/pins`).  
   - Helpers already in `src/utils/pin_helpers.py` stay there; import in the new blueprint instead of `chat.py`.  
   - Template: keep `_pins_sidebar.html` partial; continue to include it from `chat/view.html`.

2) **Comments**  
   - Option A: keep in `chat.py` but move to a bottom section with clear separation.  
   - Option B: new file `src/app/chat_comments.py` with routes: add/delete comment.  
   - Keep comment templates within `chat/view.html` but consider a `_comments.html` partial if it grows.

3) **Progression/Exports**  
   - `assess-progression` and `export` routes can remain in `chat.py` or move to `chat_tools.py` if they grow.  
   - Keep core chat view and message posting near the top; auxiliary routes near the bottom or another file.

4) **Template modularity**  
   - Already extracted `_pins_sidebar.html`.  
   - Consider a small `_message_footer.html` partial if footer actions grow (time, comment, pin).

---

## Suggested File Structure
```
src/app/chat.py            # core view_chat, post message
src/app/chat_comments.py   # add/delete comment routes (optional)
src/app/chat_pins.py       # pin/unpin/share/unshare/list routes
src/utils/pin_helpers.py   # pin logic (keep)
templates/chat/view.html   # include partials
templates/chat/_pins_sidebar.html
```

---

## Migration Steps (incremental)
1. Move pin routes from `chat.py` into `chat_pins.py`; register the blueprint in `src/app/__init__.py`.  
2. Update imports in `chat.py` to remove pin route dependencies.  
3. (Optional) Move comment routes into `chat_comments.py`.  
4. Keep route URLs unchanged to avoid breaking clients.  
5. Run lint/tests to ensure imports and blueprint registration are correct.

---

## Risks / Considerations
- Blueprint registration: ensure new blueprints are registered in `create_app` with the same URL prefixes.  
- Import cycles: keep helpers in `utils` to avoid circular imports between chat/pins.  
- Asset includes: no change needed; templates still include the same partials.  
- Tests: add/update tests to cover pin routes in the new module and ensure ACLs still apply.
