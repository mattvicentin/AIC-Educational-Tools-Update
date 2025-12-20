# Phase 2 – Sidebar Accordion Rollout (Participants & Other Chats)

Date: 2025-10-30

This guide captures the exact steps for adding collapsible panels for the Room Members and Other Chats blocks in the chat sidebar. The goal is to keep the change surgical, preserve all existing functionality, and avoid the tag‑matching issues we hit during Phase 1.

---

## 1. Prerequisites
- Current branch: `feature/railway-deployment` (or a feature branch branched from it)
- Phase 1 – Tools accordion already merged and verified
- Local dev server available for manual testing (desktop + mobile/iOS)
- Confidence that the current chat layout is stable

---

## 2. Implementation Steps

### 2.1 Wrap “Room Members” in an accordion
1. Open `templates/chat/view.html`.
2. Locate the `<!-- Room Members -->` section.
3. Replace the existing wrapper with:
   ```jinja
        <!-- Participants Section (Collapsible) -->
        <details class="sidebar-section" data-section="members" open>
            <summary class="sidebar-summary">
                <i data-lucide="users" class="w-5 h-5"></i>
                <span>Participants</span>
                <span class="badge">{{ (room_members|length) if room_members else 0 }}</span>
                <i data-lucide="chevron-down" class="w-4 h-4 chevron"></i>
            </summary>
            <div class="sidebar-panel">
                <!-- Room Members -->
                <div class="overflow-y-auto">
                    {# existing member markup, unchanged #}
                </div>
            </div>
        </details>
   ```
4. Keep all member markup (avatars, buttons, classes) untouched.
5. Save and visually inspect indentation/tag balance.

### 2.2 Wrap “Other Chats” in an accordion
1. Still in `templates/chat/view.html`, locate the “Other Chats” block.
2. Wrap it with:
   ```jinja
        <!-- Other Chats Section (Collapsible) -->
        <details class="sidebar-section" data-section="other-chats" open>
            <summary class="sidebar-summary">
                <i data-lucide="messages-square" class="w-5 h-5"></i>
                <span>Other Chats</span>
                <span class="badge">{{ (other_chats|length) if other_chats else 0 }}</span>
                <i data-lucide="chevron-down" class="w-4 h-4 chevron"></i>
            </summary>
            <div class="sidebar-panel">
                {# existing chat list markup, unchanged #}
            </div>
        </details>
   ```
3. Preserve the existing `<a>` links, timestamp formatting, and message counts.

### 2.3 Add badge styling
1. Open `src/app/static/css/components.css`.
2. Append:
   ```css
   .sidebar-summary .badge {
       margin-left: auto;
       margin-right: 0.5rem;
       padding: 0.125rem 0.5rem;
       background: hsl(var(--muted));
       color: hsl(var(--muted-foreground));
       font-size: 0.75rem;
       font-weight: 600;
       border-radius: 9999px;
       min-width: 1.5rem;
       text-align: center;
   }
   ```

---

## 3. Testing Checklist

### Desktop
- [ ] Collapse/expand “Tools,” “Participants,” and “Other Chats” independently.
- [ ] Member avatar actions still work (profile button, disabled message button).
- [ ] “Other Chats” links navigate correctly.
- [ ] Counts update (0 when no members/chats).
- [ ] No console errors; Lucide icons render.

### Mobile / Drawer
- [ ] Sidebar drawer opens/closes normally.
- [ ] Accordions respond to touch; tap targets feel large enough.
- [ ] Scrolling is smooth (no nested scroll traps).

### Focus Mode
- [ ] Enter focus mode: sidebar hidden as before.
- [ ] Exit focus mode: accordion open states acceptable.

### Regression – Sticky Composer
- [ ] Confirm sticky composer still works while collapsing/expanding panels (especially on iPhone Safari).

---

## 4. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Broken tag structure | Verify each opening `<details>` has a matching `</details>` before moving to the next section. |
| Scroll conflicts on iOS | Keep only one scroll container per panel (remove extra `overflow-y-auto` if needed) and test on a physical device. |
| Null/empty data | Use `{{ (room_members|length) if room_members else 0 }}` guards to avoid Jinja errors. |
| JS regressions | Keep `data-section="tools"` unchanged so `restore-document-generation.js` and tone mount continue to work. |

---

## 5. Rollback Plan
1. `git restore templates/chat/view.html src/app/static/css/components.css`
2. Redeploy current stable version (Phase 1 only)
3. Re-test sidebar basics

---

## 6. Next Steps After Phase 2
- Capture UX feedback from desktop/mobile users.
- Decide whether to persist accordion state in `localStorage`.
- Plan Phase 3 (e.g., metadata in summary bars, new tool injection point).

---

Maintain the “one change at a time” discipline: wrap Participants, test, commit; wrap Other Chats, test, commit; add CSS, test, commit. This keeps diffs reviewable and makes rollback painless. Good luck! 🎯
