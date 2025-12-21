# UI Regression: Missing Tailwind CDN

## What happened
- The Tailwind CDN script was removed from `templates/base.html`.
- The app’s layout relies on Tailwind utility classes; without the CDN JIT, those classes never load.
- Result: most of the UI lost spacing, colors, and layout (chat and sidebar collapsed, footer unstyled) while custom CSS like the Quiz modal still worked.

## Fix
- Re-add the Tailwind CDN include in `templates/base.html`:
  ```html
  <script src="https://cdn.tailwindcss.com"></script>
  ```
- Ensure CSP allows Tailwind:
  - `script-src` includes `https://cdn.tailwindcss.com`
  - `style-src` includes `https://cdn.tailwindcss.com`
  - `connect-src` includes `https://cdn.tailwindcss.com` (the CDN fetches the generated stylesheet)
- Hard-refresh (Cmd/Ctrl+Shift+R) after deploying.

## Prevent it
- If you need to remove the CDN, build a local Tailwind bundle and update `base.html` to point to it; otherwise keep the CDN script in place.
- When changing titles or minor template text, avoid touching the CDN include lines.
