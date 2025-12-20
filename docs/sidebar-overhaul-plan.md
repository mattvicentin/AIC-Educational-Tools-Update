# Sidebar Redesign Plan

## 1. Current Sidebar Inventory (Baseline)
- **Generate Document dropdown**
  - Export chat history (`.txt`, `.docx`)
  - Create notes (`.txt`, `.docx`)
  - Create outline (`.txt`, `.docx`)
- **Chat summary**: title and writing mode label
- **AI Assistant Role** card (collapsible instructions)
- **Tone & Critique** slider (with Save button)
- **Learning Progress** row (`Assess Progress` CTA)
- **Room Members** list (unbounded)
- **Other Chats** list (mode badge, message count, timestamp)

## 2. Target Structure
### Always-visible header
- Room name + “Back to Rooms” link/icon
- Active chat title + writing mode badge
- Quick actions row (Generate Document dropdown, optional shortcuts)

### Collapsible sections (`<details class="sidebar-section">`)
1. **Tools**
   - Tone & Critique slider panel
   - AI Assistant Role instructions
   - Export / notes / outline actions
   - Placeholder slot for future tools
2. **Participants**
   - Summary shows total count
   - Body lists member cards; if >5, constrain height and allow scroll
   - Include “Invite” control
3. **Other Chats**
   - Summary shows count
   - Body lists recent chats with mode badge, message count, last activity

*Optional future section:* Learning Progress (detailed), Resources & Docs.

## 3. Tool Card Pattern
Reusable markup for each tool:
```html
<div class="tool-card" data-tool="tone">
  <div class="tool-card__icon">🎯</div>
  <div class="tool-card__body">
    <h4 class="tool-card__title">Tone & Critique</h4>
    <p class="tool-card__meta">Adjust AI feedback style</p>
  </div>
  <button class="tool-card__action" aria-label="Open Tone & Critique">
    <i data-lucide="chevron-right"></i>
  </button>
</div>
```
- Define `.tool-card`, `.tool-card__icon`, `.tool-card__body`, `.tool-card__action` in `components.css`.
- Optionally loop over a `tools` array to add new entries quickly.

## 4. Implementation Steps
1. Add shared accordion styles (`sidebar-section`, `sidebar-summary`, `sidebar-panel`).
2. **Phase 1 (low-risk rollout):** wrap the existing Tools block (Generate Document + AI role + Tone & Critique) in a `<details class="sidebar-section" open>` shell using the new styles. Keep all current IDs/classes so existing JS continues to work.
3. Smoke test the Tools block (desktop + mobile) to ensure the dropdown, tone slider, and AI instructions still behave.
4. Deploy Phase 1 and monitor.
5. **Next phases (one at a time):**
   - Migrate Participants into the accordion; add `max-height` + scroll.
   - Migrate Other Chats into the accordion.
   - Introduce optional sections (Learning Progress, Resources) as needed.
6. Apply the tool card pattern when the Tools hub needs additional utilities.
7. Constrain long lists (participants, other chats) with `max-height` + `overflow-y: auto`.
8. Run the full desktop/tablet/mobile/focus-mode test suite after each phase.

## 5. Testing Checklist
- Desktop: expand/collapse works, tone slider functional, lists scroll inside panels.
- Tablet/mobile: drawer opens, sections collapsed by default, summary tap area large enough.
- Focus mode: sidebar remains hidden as before.
- Accessibility: keyboard focus order, `aria-expanded` handled by `<details>`.
