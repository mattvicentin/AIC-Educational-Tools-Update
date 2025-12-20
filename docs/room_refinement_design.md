# Room Refinement with AI (Design)

Goal: Make the “Revise with AI” action reliably reconfigure a room’s learning steps based on user preferences, while preserving the room’s original intent and maintaining a valid step schema.

---

## High‑Level Flow
1) Gather context
   - Room snapshot: title, description, goals
   - Current steps: ordered list of `{ key, label, prompt }`
   - Baseline (first‑composition) steps stored at first save for reference
   - User preference (free text): e.g., “reduce to six steps focused on evidence and sources”
2) Deterministic pre‑pass (fast path)
   - If preference matches simple patterns (reduce to N, remove step by number/substring), apply locally
   - Keep ordering; reindex keys as `step1..stepN`; normalize labels to `1. …`
3) AI rewrite (constrained)
   - Build a structured prompt with room snapshot + current steps + preference
   - Ask the model to return ONLY JSON of shape:
     ```json
     {
       "modes": [{ "key": "step1", "label": "1. …", "prompt": "…" }, ...],
       "summary": "what changed and why",
       "notes": ["optional notes"]
     }
     ```
   - Keep provider failover (Anthropic → OpenAI → templates)
4) Validation & normalization
   - Validate JSON, min/max steps, sequential keys, normalized labels
   - Cap lengths, strip HTML; if invalid, fall back to deterministic result or previous modes
5) Persistence (edit flow)
   - Transactionally replace `CustomPrompt` rows
   - Append a `RoomRefinementHistory` record with preference, old/new modes, summary
   - Provide a one‑click revert
6) Response & UX
   - Return `modes` + `summary` and show preview/diff before/after labels
   - Display banner “Applied your changes” or an error/fallback notice

---

## Aggregated Context (what we send to the model)
- Room:
  - `name`: string
  - `goals`: string (or description when goals missing)
- Current steps (at most 12; summarize prompts if overly long):
  ```
  1. Explore & evaluate significance — prompt: …
  2. Narrow to a researchable question — prompt: …
  …
  ```
- Preference (verbatim): user’s free text
- Constraints (in system prompt):
  - Output ONLY JSON matching the schema
  - Keys must be `step1..stepN` sequential; labels must start with an ordinal (`1.`, `2.`, …)
  - Be coherent with the preference while preserving the room’s goals

---

## Prompt Skeleton (system + user)
- System:
  - “You are revising a course/room learning sequence. Produce ONLY JSON with fields `modes`, `summary`, and optional `notes`. Follow schema strictly. Do not include prose.”
  - “Each mode: `{ key, label, prompt }`. Keys must be `step1..stepN`. Labels must start with `n.`. Prompts must be plain text.”
- User:
  ```
  Room title: "{{title}}"
  Room goals: "{{goals}}"

  Current steps:
  1. {{label1}} — prompt: {{prompt1}}
  2. {{label2}} — prompt: {{prompt2}}
  ...

  Preference: "{{preference}}"

  Return ONLY JSON as:
  {
    "modes": [{ "key": "step1", "label": "1. …", "prompt": "…" }, ...],
    "summary": "…",
    "notes": ["optional"]
  }
  ```

---

## Validation Rules
- `1 <= steps <= 12` (configurable)
- Keys strictly sequential; if not, renumber deterministically
- Labels must start with `n.`; if not, rewrite
- Prompts must be plain text (strip HTML/tags); cap length
- Reject empty labels/prompts; if any invalid after repair → fallback

---

## Data Model Additions
- `RoomRefinementHistory` (new)
  - `id PK`, `room_id`, `user_id`, `preference TEXT`,
    `old_modes_json JSON`, `new_modes_json JSON`, `summary TEXT`, `created_at`
  - Index on `room_id`, `created_at`
- `CustomPrompt` remains the write target

---

## Endpoint Behavior
- New room (no `room_id`): compute result but do not persist; return preview + `summary` and persist after user saves
- Edit flow: compute; persist immediately within a transaction; write history
- Keep existing deterministic `_apply_refinements` as a pre‑pass for fast reductions/merges

---

## Risks to Avoid & Mitigations
- Model returns invalid JSON → strict validator + repair + fallback to deterministic/current modes
- Hallucinated step counts or keys → enforce renumbering, min/max limits
- Drifting intent across multiple revisions → use baseline snapshot in context; include earlier goals in the prompt
- Over‑long prompts blow up token budget → summarize prompts before sending; cap lengths
- Cost spikes → rate‑limit revise endpoint; reuse provider failover; cache per preference signature briefly
- User confusion → always return a concise `summary` and render a diff; provide “Revert” via history

---

## How to Test (manual + automated)
1) Basic correctness
   - Create a room with 10 default steps; ask “reduce to six steps focused on evidence and sources”
   - Expect 6 steps; labels renumbered; prompts emphasize evidence; `summary` explains merges
2) Invalid JSON path
   - Simulate provider returning prose → validator triggers fallback to deterministic result; request succeeds with warning
3) Schema normalization
   - Ask to “remove step 9 and rename step 3 to ‘Outline Methods’”
   - Verify key renumbering and label normalization; no gaps in `stepN`
4) History and revert
   - After a revision, verify a `RoomRefinementHistory` row is written and “Revert” restores the previous set
5) Cost/limit
   - Hit the endpoint rapidly; verify rate‑limit and graceful error message
6) Trial mode
   - In trial, verify each revision counts toward message caps; limit prevents abuse

---

## Rollout Plan
- Behind a feature flag `REFINE_V2_ENABLED=false`
- Ship validators and history table first; wire AI call after validation passes
- Enable per cohort; monitor revert usage, error rate, and average steps before/after
