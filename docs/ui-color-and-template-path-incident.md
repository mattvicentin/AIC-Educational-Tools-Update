# UI Color/Menu Breakpoint Issue and Template Path Confusion

This note captures what’s happening in production, what we changed in the repo, why you keep seeing the same UI, and how to validate that the live service is actually serving the updated code instead of older “ghost” assets.

---

## 1) Symptoms observed in production

- At wide widths (≥769px): page background is solid white/gray; cards look gray; desktop menu visible.
- At narrow widths (<768px): cards flip to white; hamburger/menu disappear; overall colors look unchanged.
- There is a noticeable style shift exactly at the 768↔769px breakpoint: menu button placement changes at 769px, and when narrower than 768px the menu disappears entirely. This indicates breakpoint‑specific rules and/or JS affecting visibility around the `md` threshold.
- Colors appear the same regardless of repo changes; multiple pushes don’t visibly affect the live site.

## 2) Diagnostics we ran (and what they prove)

- Template folder reported by the live app: `/app/templates` (lowercase is used at runtime).
  - Endpoint: `/__tpl` returns `{ "template_folder": "/app/templates", ... }`.
- Live `base.html` still links old CSS versions:
  - Endpoint: `/__tpl_base` returns (example):
    ```json
    {
      "template_folder": "/app/templates",
      "base_path": "/app/templates/base.html",
      "hrefs": [
        "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/globals.css') }}?v=2.0\">",
        "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/components.css') }}?v=5.9\">"
      ]
    }
    ```
  - This proves production is still serving older versions, not the newly linked `v=2.2 / v=6.1 / v=2.3` we pushed.
- Browser console (DevTools) confirms old assets are loaded at runtime:
  ```js
  [...document.querySelectorAll('link[rel=stylesheet]')]
    .map(l => l.href)
    .filter(h => h.includes('/static/css/'))
  // => [
  //   '.../globals.css?v=2.0',
  //   '.../components.css?v=5.9',
  //   '.../style.css?v=2.1'
  // ]
  ```
- Computed styles at runtime match the stale assets (e.g., `display: none` for the hamburger, `rgb(255,255,255)` background, same neutral for description and meta text).

## 3) Root cause (current)

The live container has not picked up the updated `base.html` and CSS assets. Until Railway deploys the latest commit from the correct branch, the browser will keep pulling the older versions (2.0/5.9/2.1). This is a deployment drift/caching issue, not a code-edit issue now.

## 4) Template path problem (historical)

- The repo historically contained both `Templates/` (capitalized) and `src/templates/` (lowercase). macOS dev is often case-insensitive, but Linux (Railway) is case-sensitive.
- Early edits sometimes landed in `Templates/` while the running app used `src/templates` (or vice versa), creating “ghost code” changes that never appeared.
- We corrected runtime to use lowercase `templates` and confirmed via `/__tpl`. Current issue is not path mismatch; it is stale HTML/CSS versions being served.

## 5) Changes already made in the repo (but not yet live in prod)

- Tokenized neutrals and fixed HSL usage:
  - `--muted-fg-50: #6b7280`, `--muted-fg-40: #9ca3af`.
  - `.text-muted-foreground` and `.text-muted-40` map to these (with `!important`).
  - `--background: 210 20% 98%` (HSL triple), `--card: 0 0% 100%` (HSL triple) and all usages changed to `hsl(var(--...))`.
- Removed hardcoded grays in `style.css` and replaced with tokens (`var(--muted-fg-50/40)` or `var(--foreground)`).
- Made `.bg-card` consistently `hsl(var(--card))` at all widths.
- Removed JS that forcibly hid the hamburger on desktop; now rely on Tailwind `md:hidden`/`md:flex`.
- Bumped cache-busters in `Templates/base.html` to force fresh loads:
  - `globals.css?v=2.2`
  - `components.css?v=6.1`
  - `style.css?v=2.3`

## 6) Why the UI still looks unchanged

Production is still linking older CSS versions. The browser is fetching `globals 2.0`, `components 5.9`, `style 2.1`, so it renders the old rules (white page, breakpoint-only white cards, hidden hamburger on mobile, legacy grays).

## 7) One-pass remediation (deployment)

1. Ensure Railway deploys from the `feature/railway-deployment` branch.
2. Start command should be the lower-case template app:
   ```
   gunicorn src.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   ```
3. Click “Deploy latest”.
4. Verify with `/__tpl_base` that `hrefs` now show:
   - `globals.css?v=2.2`, `components.css?v=6.1`, `style.css?v=2.3`.
5. Hard refresh the browser (or open a fresh incognito window).

## 8) Post-deploy validation checklist

- In the browser console:
  ```js
  [...document.querySelectorAll('link[rel=stylesheet]')]
    .map(l => l.href)
    .filter(h => h.includes('/static/css/'))
  // Expect v=2.2, v=6.1, v=2.3

  getComputedStyle(document.body).backgroundColor
  // Expect a soft gray (not pure white)

  getComputedStyle(document.querySelector('.bg-card')).backgroundColor
  // Expect white card background

  getComputedStyle(document.querySelector('.bg-card p.text-sm.text-muted-foreground')).color
  // Expect secondary neutral (≈ rgb(107,114,128))

  getComputedStyle(document.querySelector('.bg-card .text-xs.text-muted-foreground')).color
  // Expect lighter tertiary (≈ rgb(156,163,175))

  // On narrow (<768px): hamburger should exist and be visible
  !!document.getElementById('mobile-menu-button')
  getComputedStyle(document.getElementById('mobile-menu-button')).display
  // Expect 'block' (or not 'none') and visible
  ```

## 9) If it still doesn’t update

- Add a one-line sentinel comment at the end of `templates/base.html` (e.g., `<!-- base v=YYYY-MM-DDTHH:MMZ -->`) and redeploy. If you don’t see it in View Source, the service isn’t deploying the latest.
- Confirm the Railway service environment/branch selection.
- Confirm no CDN or proxy is pinning older `/static/css/*` responses with long cache headers (the `?v=` query-strings are designed to bust caches).

## 10) TL;DR

- Current blocker is not a code change; it’s that production is still serving older assets linked from `base.html`. Redeploy so the live `hrefs` read `globals v2.2 / components v6.1 / style v2.3`. The color hierarchy, card backgrounds, and hamburger visibility will then match the tokenized, responsive design.


