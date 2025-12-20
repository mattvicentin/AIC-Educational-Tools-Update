# Chat Message Footer Styles (Status: December 2025)

This doc explains how the footer text/buttons ("time", "Add Comment", "Pin/Unpin") are styled in chat messages and comments, and how to adjust them safely.

## Where the styles live
- `templates/chat/view.html` — markup and per-page pin basics (inline `.pin-toggle` reset).
- `src/app/static/css/components.css` — base `.message-timestamp` styles (font size, opacity).
- `src/app/static/css/chat-improvements.css` — chip styling for comment/pin buttons.
- `src/app/static/css/chat-overrides.css` — bubble-specific overrides (different colors for user vs assistant bubbles).

## Current behavior (messages)
- Parent: `.message-timestamp` in `components.css` sets `font-size: 0.75rem` and `opacity: 0.7` for the whole footer line.
- "Add Comment" chip:
  - Styled in `chat-improvements.css` (`.message-timestamp button[data-toggle-comment]`) with a pill background/border, `font-weight: 600 !important`, and primary-colored text.
  - Additional hover/focus states defined there.
- "Pin/Unpin" chip:
  - Base chip styling in `chat-improvements.css` (`.message-timestamp button.pin-toggle`): pill background/border, `font-weight: 600 !important`, `font-size: 0.75rem !important`, `opacity: 1 !important` to cancel parent opacity.
  - Bubble-specific colors in `chat-overrides.css`:
    - User bubbles (purple): white text, light translucent background/border.
    - Assistant bubbles (light): primary-colored text, subtle gray/primary background/border.
  - Hover/focus states and outline for accessibility live in the same files.
- HTML classes for pin buttons in `chat/view.html`:
  - Messages: `class="text-xs ml-2 pin-toggle"` (no muted color utilities; color comes from CSS chips).
  - Comments: same `text-xs ml-2 pin-toggle` within the comment footer.

## Current behavior (comments)
- Comment footer uses the same `pin-toggle` class.
- Timestamp in comments inherits `text-muted-foreground`, but the pin color is overridden by the chip styles.
- Delete button uses its own styles; unaffected by pin changes.

## Cache/versioning
- JS is cache-busted via query strings (e.g., `pin-toggle.js?v=...`).
- If you change CSS, bump the query in `base.html` (or your CSS includes) to avoid stale assets.

## How to change colors/weight/shape
- For all bubbles at once: edit `chat-improvements.css` rules for `.message-timestamp button.pin-toggle` (color/background/border/font).
- For bubble-specific tweaks: edit `chat-overrides.css` rules for:
  - `.message-bubble.user .message-timestamp > button.pin-toggle`
  - `.message-bubble.assistant .message-timestamp > button.pin-toggle`
- To change size/weight globally: adjust `font-size` / `font-weight` in `chat-improvements.css` pin rule.
- To reintroduce muted link-style pins (not recommended): remove the chip styles and add `text-muted-foreground` back to the pin buttons in `chat/view.html`.
- To adjust parent opacity: `.message-timestamp` in `components.css` has `opacity: 0.7`; pin/comment chips currently override this with `opacity: 1 !important`.

## Gotchas
- Tailwind utility classes applied directly on the button (e.g., `text-muted-foreground`) will override colors unless your CSS uses `!important` or higher specificity. We removed those utilities from pin buttons to let the chip CSS control color.
- CSS load order matters: make sure `chat-improvements.css` and `chat-overrides.css` are loaded after the base styles/utilities so their `!important` rules take effect.
- Cache: if you don’t see changes, bump the CSS version query or hard-refresh.
