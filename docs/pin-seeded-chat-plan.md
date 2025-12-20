# Pin-Seeded Chats Plan (Shared Pins Only)

**Status**: Proposed (Phase D)  
**Date**: December 2025  
**Scope**: Allow users to start a new chat from shared pins in a room. Personal pins are not used for room chats.

---

## UX Summary
- Scope: Pin-seeded chats use room-level shared pins (not per-chat pins). Add a “Room Pins” tab/view (count badge) and keep chat-level pins for inline reference. CTA copy: “Start chat from room shared pins (N).”
- Entry: Pins card (sidebar) → Shared tab only. Show “Start chat from pins” CTA only when there are ≥3 shared pins.
- Step 1 (initial rollout): Quick create. Pick one of the predefined options, then create the chat from all shared pins (or selected shared pins if selection is present). No review step yet.
- Step 2 (later): Add a confirmation/review page with pin selection (enforce ≥3), option choice, and toggles (e.g., critique).
- Chat placement: New chat appears in the room chat list, grouped at the bottom as “Pin-based chats” (visual divider or tag). Same UI as other chats, with a “Using N pins” badge in the header.
- Title: Auto-title including room and option, e.g., “Pinned Insights — Study & Master — Tuberculosis Room”.
- Context: Only shared pins + room goals/summary (as with other chats). No personal pins to avoid leakage.

### Prompts for Options (define statically)
Add a `PIN_SYNTHESIS_OPTIONS` dict in a dedicated module (`src/utils/pin_synthesis.py`) mapping option keys to labels/prompts/intro templates, e.g.:
```
PIN_SYNTHESIS_OPTIONS = {
  "explore": {
    "label": "Explore & brainstorm",
    "prompt": "You are a creative thinking facilitator. Using the pinned insights provided, help the user explore connections, generate new ideas, and brainstorm possibilities. Ask probing questions to deepen exploration.",
    "intro_template": "Let's explore these {n} pinned insights together..."
  },
  "study": {
    "label": "Study & master",
    "prompt": "You are an expert tutor. Using the pinned content as study material, help the user deeply understand concepts, test knowledge, and master the material through active recall and explanation.",
    "intro_template": "I'll help you study and master these {n} key concepts..."
  },
  # TODO: add entries for all 8 options + optional analyze/summarize catch-all:
  # - research_essay (draft a research essay)
  # - presentation (build a presentation)
  # - learning_exercise (debate/simulation/pedagogical game)
  # - startup (plan a startup)
  # - artistic (create something artistic)
  # - social_impact (create positive social impact)
  # - analyze (catch-all)
}
```

### Discoverability
- Consider a prominent entry when shared pins ≥3: chat list “New from Pins” button, room header CTA, or a Mountain view CTA. Keep the CTA in the shared tab too.

---

## Options (current set)
1) Explore & brainstorm  
2) Study & master (plan/prioritize; mock tests as sub-option)  
3) Draft a research essay (summarize/outline subpath)  
4) Build a presentation  
5) Create a learning exercise (debate/simulation/pedagogical game)  
6) Plan a startup  
7) Create something artistic  
8) Create positive social impact  
9) (Optional) Analyze/Summarize catch-all

Toggles (later): Critique & improve.

---

## Backend Plan
- New endpoint: `POST /room/<room_id>/chats/from-pins`
  - Body: `{ pin_ids: [..], option: "<option_key>", include_summary: bool }`
  - Enforce: all pin_ids must be `is_shared=True` in that room; reject personal pins. Require ≥3 pins (configurable, default 3).
  - Create Chat row: title auto-generated; mode should not collide with existing template step keys.
  - Pin prompts: do NOT write to `CustomPrompt`. Instead, map the chosen option to a static pin-synthesis prompt (e.g., `PIN_SYNTHESIS_MODES` in `openai_utils.py` for the 8 options), and/or store the option+prompt in `PinChatMetadata` tied to `chat_id`. Feed that prompt directly to the AI for this chat.
- Build intro: AI intro uses selected pins as primary context; include room goals/summary per normal behavior.
- Validation: If a pin is missing/deleted, reject or drop with a warning (for Step 1, reject with a friendly error).
- Tag pin chats for grouping: prefer a PinChatMetadata table keyed by chat_id to avoid Chat schema changes; if you add a Chat flag, include manual DDL fallback like pinned_items.
- Ongoing AI responses: For pin chats, include pin context (or a summarized briefing) in the system prompt for every response, similar to learning_context. Store selected pins/summaries in PinChatMetadata and branch in get_ai_response for `is_pin_chat`.
- Title generation: Add a dedicated helper for pin chats (don’t reuse `generate_short_title` which expects room goals). Example:
  ```
  def generate_pin_chat_title(room_name: str, option_label: str, pins: List[PinnedItem]) -> str:
      return f"Pinned Insights — {option_label} — {room_name}"
      # Optionally, add an AI-generated variant later based on pin themes.
  ```

---

## Frontend Plan (Step 1)
- Pins card (shared tab):
  - Show “Start chat from pins” CTA only when shared pins ≥3.
  - Option picker (simple dialog/dropdown) to choose one of the options above.
  - On submit, call the new endpoint; on success, redirect to the new chat.
- Chat list:
  - Group pin chats at the bottom (if `is_pin_chat` true) with a small divider/header (e.g., “Pin-based chats”).
- Chat header:
  - Show badge “Using N pins” with a dropdown listing the pins and jump links.

Step 2 (later):
- Confirmation/review page: show selected shared pins (allow deselect but enforce min=3), allow adding newly created shared pins (default unchecked), and apply option/toggles.
- Prevent deselection below 3; disable “Create” if fewer than 3 remain.
- Slice the frontend work to reduce risk:
  1) Discoverability + CTA: add “Start chat from pins” in the shared tab and a prominent button in chat list/header when shared pins ≥3.
  2) Basic flow: wire CTA → option picker → call endpoint → redirect. Use all shared pins (no selection yet).
  3) UI grouping: render pin chats as a distinct group in chat list; add “Using N pins” badge in pin chat header.
  4) Selection (later): add multi-select in shared tab with min-3 guard.
  5) Polish: mobile layout, loading/empty states, error toasts, cache-bust assets.

---

## Risks / Problems to Avoid
- Privacy/leakage: Never include personal pins. Enforce `is_shared=True` on pin_ids server-side.
- ACL: Only room members can start pin chats; pin selection must be restricted to the room’s shared pins.
- Mode mapping: Avoid overloading existing learning-step modes; use dedicated `pins_<option>` keys or a neutral `analyze`, or a dedicated `pin_synthesis` template.
- Grouping: If grouping pin chats, ensure sorting/grouping logic is explicit to avoid UX confusion.
- Pin drift: Pins used are snapshotted; if a pin is deleted later, the chat should still render (use stored content). In Step 2, revalidation can allow deselection.
- Token budget: Cap by count and chars (e.g., max 8 pins or 20k chars total). If over, pre-summarize newest shared pins into a briefing before prompting.
- UI state: CTA should be hidden/disabled when <3 shared pins; shared tab only. Avoid showing the CTA in the personal tab.
- Entry: Make the CTA discoverable (chat list/room header/Mountain view) in addition to the shared tab.
- Caching: Bump asset versions when adding new UI to avoid stale CSS/JS.
- Title generation: Use `title_generator.py` with pin content as input; fallback to “Pinned Insights — <option> — <room>”. Keep server-side for consistency.
- Snapshot schema: Define `PinChatMetadata.pin_snapshot` as JSON list of pin snippets, e.g., `[{"id":123,"content":"...","role":"assistant","author":"username"}, ...]` so pin-based chats can render even if originals are deleted.
- Detection in AI flow: In `get_ai_response`, detect pin chats via `PinChatMetadata` on `chat_id`; if present, build a pin-specific system prompt from stored snapshot/option; otherwise use the normal mode flow.
- Discoverability: Don’t bury the CTA in a collapsed tab; surface it prominently when shared pins ≥3.
- Validation gaps: Enforce shared-only and min-3 on the server; don’t rely solely on client checks.
- Mode/prompt collisions: Keep pin prompts separate from room `CustomPrompt`.
- Token overload: Enforce caps; summarize when over budget.
- Error handling: Handle missing/deleted pins gracefully with friendly errors.

---

## Minimal Rollout Checklist (Step 1)
- [ ] New endpoint to create chat from shared pins (≥3, option required).
- [ ] Pins card CTA visible only in shared tab when count ≥3.
- [ ] Option picker wired; mode/title set appropriately.
- [ ] Pin chat tagged and rendered in chat list (bottom grouping).
- [ ] Chat header shows “Using N pins” with links.
- [ ] Tests: reject personal pins; reject <3 pins; ACL check; intro uses pins.

---

## Implementation Order (recommended)
- **Phase 1: Data**
  - Add `PinChatMetadata` model (chat_id FK, option key, pin snapshot JSON, created_at) with migration and manual fallback DDL.
- **Phase 2: Backend endpoint**
  - `POST /room/<room_id>/chats/from-pins`: validate room access, ≥3 shared pins, snapshot pins, create Chat + PinChatMetadata, generate intro, return chat_id.
- **Phase 3: AI integration**
  - Add `PIN_SYNTHESIS_OPTIONS` prompts and `generate_pin_chat_introduction(pins, option, room_goals)` to build the system prompt/intro with pin context (truncate/summarize as needed).
- **Phase 4: Frontend**
  - Add Room Pins tab with count, CTA in shared tab when ≥3 shared pins, option picker modal, and chat list grouping for pin chats.
