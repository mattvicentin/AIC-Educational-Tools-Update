# Pins Feature Roadmap

**Status**: Planning  
**Date**: December 2025  
**Prerequisite**: Personal pins feature (complete ✅)

---

## Vision

Transform pins from passive bookmarks into **active conversation starters**:

1. **Phase A**: Personal pins (✅ complete)
2. **Phase B**: Shared pins (collaborative bookmarking)
3. **Phase C**: Pin-seeded chats (use pins to start new conversations)

---

## Ultimate Goal: Pin-Seeded Chats

Select pins → Create new chat with those pins as context → AI generates opening message based on pinned content.

**Use cases**:
- "Continue this discussion" — pin key insights, start a follow-up chat
- "Synthesize these ideas" — pin from multiple chats, create a summary chat
- "Explore this question" — pin a question, start a deep-dive chat

---

# Phase B: Shared Pins

## Overview

Extend the pinned items feature to support collaborative "shared pins" visible to all room/chat members, alongside existing personal pins.

---

## Data Model Changes

### Schema Addition

```sql
-- Add to pinned_items table
ALTER TABLE pinned_items ADD COLUMN is_shared BOOLEAN NOT NULL DEFAULT FALSE;

-- New indexes for shared pin queries
CREATE INDEX ix_pinned_items_chat_shared ON pinned_items(chat_id, is_shared);
CREATE INDEX ix_pinned_items_room_shared ON pinned_items(room_id, is_shared);
```

### Migration Files Required

1. **Alembic migration**: `add_is_shared_to_pinned_items.py`
2. **Manual fallback in `src/main.py`**: Both PostgreSQL and SQLite variants

### Manual Fallback SQL (src/main.py)

```python
# In run_production_migrations(), after pinned_items table creation:

try:
    # Check if is_shared column exists
    db.engine.execute("SELECT is_shared FROM pinned_items LIMIT 1")
except Exception:
    print("⚠️ is_shared column missing, adding...")
    is_postgres = 'postgresql' in str(db.engine.url)
    if is_postgres:
        db.engine.execute("""
            ALTER TABLE pinned_items 
            ADD COLUMN is_shared BOOLEAN NOT NULL DEFAULT FALSE;
            
            CREATE INDEX IF NOT EXISTS ix_pinned_items_chat_shared 
                ON pinned_items(chat_id, is_shared);
            CREATE INDEX IF NOT EXISTS ix_pinned_items_room_shared 
                ON pinned_items(room_id, is_shared);
        """)
    else:  # SQLite
        db.engine.execute("""
            ALTER TABLE pinned_items 
            ADD COLUMN is_shared INTEGER NOT NULL DEFAULT 0;
        """)
        # SQLite doesn't support CREATE INDEX IF NOT EXISTS in same transaction
        try:
            db.engine.execute(
                "CREATE INDEX ix_pinned_items_chat_shared ON pinned_items(chat_id, is_shared)"
            )
            db.engine.execute(
                "CREATE INDEX ix_pinned_items_room_shared ON pinned_items(room_id, is_shared)"
            )
        except Exception:
            pass  # Indexes may already exist
    print("✓ is_shared column added")
```

---

## API Changes

### Simplified Endpoints (reduced surface area)

| Endpoint | Purpose |
|----------|---------|
| `POST /chat/<id>/pin` | Create pin; accepts `{message_id, shared: bool}` (default `false`) |
| `POST /chat/<id>/unpin` | Remove pin; accepts `{message_id}` or `{comment_id}` |
| `PATCH /chat/<id>/pin/<pin_id>` | Update visibility; accepts `{shared: bool}` |
| `GET /chat/<id>/pins` | List pins; accepts `?scope=personal\|shared\|all` |
| `GET /room/<id>/pins` | List room-wide pins; accepts `?scope=shared` |

**Note**: Single PATCH endpoint for visibility changes avoids separate `/share` and `/unshare` routes.

### Access Rules

| Action | Who Can Do It |
|--------|---------------|
| View personal pins | Owner only |
| View shared pins | Any room/chat member |
| Create pin (personal) | Any room/chat member |
| Create pin (shared) | Any room/chat member |
| Change own pin visibility | Pin owner only |
| Remove own pin | Pin owner only |
| Remove others' shared pin | Room owner only (moderation) |
| Remove orphaned pin (owner left) | Room owner only |

### Moderation Policy: Orphaned Pins

When a pin owner leaves the room:
- **Shared pins stay visible** (content is room context)
- **Attribution shows "Former member"**
- **Room owner can remove** orphaned shared pins
- **Personal pins are deleted** (or hidden) when owner loses room access

---

## Helper Functions

### New Functions in `src/utils/pin_helpers.py`

```python
def get_personal_pins_for_chat(user_id, chat_id):
    """Returns only the current user's personal pins."""
    
def get_shared_pins_for_chat(chat_id):
    """Returns all shared pins for a chat (with author attribution)."""
    
def share_pin(user, pin_id):
    """Promote a personal pin to shared. Owner only."""
    
def unshare_pin(user, pin_id, is_room_owner=False):
    """Demote shared → personal. Owner or room owner."""
```

### AI Context Functions

```python
def get_pins_for_ai_context(user_id, chat_id):
    """
    Returns pins for AI prompt building.
    - Shared pins: included for all users
    - Personal pins: included only for the owner
    
    CRITICAL: Keep these queries separate to prevent leakage.
    """
```

---

## UI Changes

### Sidebar Enhancement

Extract `templates/chat/_pins_sidebar.html` with:

- **Tabs**: "My Pins" | "Shared Pins"
- **Personal pins**: Jump link, Unpin button, "Share" action
- **Shared pins**: Jump link, author badge ("Shared by Alice"), timestamp
- **Owner actions**: "Unshare" (own pins), "Remove" (room owner moderation)

### Empty & Loading States

```html
<!-- My Pins - Empty -->
<div class="pins-empty">
  <span class="text-muted">No personal pins yet</span>
  <p class="text-xs">Click "Pin" on any message to save it here</p>
</div>

<!-- Shared Pins - Empty -->
<div class="pins-empty">
  <span class="text-muted">No shared pins in this chat</span>
  <p class="text-xs">Share a pin to make it visible to all members</p>
</div>

<!-- Loading State -->
<div class="pins-loading">
  <span class="spinner"></span> Loading pins...
</div>

<!-- Error State -->
<div class="pins-error">
  <span class="text-warning">Could not load pins</span>
  <button onclick="retryLoadPins()">Retry</button>
</div>
```

### Pin Toggle Enhancement

```html
<!-- Current -->
<button class="pin-toggle">📌 Unpin</button>

<!-- Enhanced -->
<button class="pin-toggle">📌 Unpin</button>
<button class="share-toggle" title="Make visible to room members">
  Share
</button>
```

### Labels for Clarity

- Personal pins: No badge (default)
- Shared pins: Badge "Visible to room members" or "Shared by {user}"

---

## Critical Risks & Mitigations

### 1. AI Context Leakage (HIGH)

**Risk**: Personal pins accidentally included in other users' AI responses.

**Mitigation**:
- Separate helper functions (not just a flag parameter)
- Unit tests that create User A's personal pin, verify User B's context excludes it
- Code review checkpoint before merge

### 2. Access Control Gaps (MEDIUM)

**Risk**: Non-members seeing shared pins, or users unsharing others' pins.

**Mitigation**:
- Reuse `@require_chat_access` for all shared pin endpoints
- Add `is_room_owner` check for moderation actions
- Return 403, not 404, for permission denials (clear feedback)

### 3. Cascade on User Removal (MEDIUM)

**Risk**: Shared pins orphaned when user leaves room.

**Policy Decision**:
- Shared pins **stay visible** (content is room context)
- Attribution shows "Former member" if user no longer in room
- Room owner can remove orphaned pins

### 4. Session Poisoning (LOW)

**Risk**: Failed shared-pin query breaks chat view.

**Mitigation**:
- Replicate the `try/except/rollback` pattern from personal pins
- Return empty list on failure, not crash

---

## Implementation Phases

| Phase | Scope | Risk | Effort |
|-------|-------|------|--------|
| **1** | Add `is_shared` column + migration | Low | 1 hr |
| **2** | Add share/unshare API endpoints | Medium | 2 hr |
| **3** | Extract `_pins_sidebar.html` partial | Low | 1 hr |
| **4** | Add "Share" toggle to pin UI | Medium | 2 hr |
| **5** | Add "Shared Pins" tab in sidebar | Medium | 2 hr |
| **6** | Wire AI context to include shared pins | **High** | 3 hr |
| **7** | Room owner moderation UI | Medium | 2 hr |
| **8** | Tests: isolation, access control, cascades | High | 3 hr |

**Total estimate**: ~16 hours

---

## Files to Modify

### Backend
- `src/models/pin.py` — Add `is_shared` column
- `src/utils/pin_helpers.py` — New query functions
- `src/app/chat.py` — Extended endpoints
- `src/main.py` — Manual fallback SQL
- `src/utils/learning/context_manager.py` — AI context changes
- `migrations/versions/` — New Alembic migration

### Frontend
- `templates/chat/view.html` — Extract sidebar partial
- `templates/chat/_pins_sidebar.html` — New partial with tabs
- `src/app/static/js/pin-toggle.js` — Share/unshare handlers
- `src/app/static/css/chat-improvements.css` — Shared pin badges
- `templates/base.html` — Bump asset versions

---

## Testing Checklist

### Access Control
- [ ] Personal pin not visible to other users via API
- [ ] Personal pin not visible in other users' sidebar
- [ ] Shared pin visible to all chat members
- [ ] Non-member cannot see shared pins
- [ ] Only pin owner can change own pin visibility
- [ ] Room owner can remove any shared pin
- [ ] Room owner can remove orphaned pins (owner left room)

### AI Context Isolation (CRITICAL)
- [ ] **User B never sees User A's personal pins in AI context**
- [ ] User A's personal pins included in User A's AI context
- [ ] Shared pins included in AI context for all room members
- [ ] Mixed query (personal + shared) correctly scoped per user
- [ ] No personal pin content leaks into shared AI responses

### Data Integrity
- [ ] Deleted message cascades to remove pin
- [ ] User removal from room: shared pins remain with "Former member"
- [ ] User removal from room: personal pins deleted/hidden
- [ ] Session rollback on query failure (no session poisoning)

### Edge Cases
- [ ] Double-click on share toggle doesn't create duplicates
- [ ] Sharing already-shared pin is idempotent
- [ ] Unsharing already-personal pin is idempotent

---

## Cache Busting Reminder

**IMPORTANT**: Bump asset versions when deploying each phase to avoid stale UI.

### Phase B (Shared Pins)
```html
<!-- templates/base.html -->
<link href="...chat-improvements.css?v=2.2" ...>  <!-- +0.1 for share toggle styles -->
<link href="...chat-overrides.css?v=1.2" ...>     <!-- +0.1 for shared badge colors -->
<script src="...pin-toggle.js?v=1.2" ...>         <!-- +0.1 for share/unshare handlers -->
```

### Phase C (Pin-Seeded Chats)
```html
<script src="...pin-selection.js?v=1.0" ...>      <!-- New file -->
<link href="...pin-selection.css?v=1.0" ...>      <!-- New file -->
```

### Verification
After deploy, check browser DevTools Network tab to confirm new versions are loaded.
Add sentinel comments in templates if needed (e.g., `<!-- SHARED_PINS_V2 -->`).

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Default visibility | Personal | Opt-in sharing reduces accidental exposure |
| API structure | Single PATCH for visibility | Reduces surface area vs separate /share /unshare |
| Who can unshare others' pins | Room owner only | Clear moderation authority |
| Orphaned shared pins | Keep visible | Content is room context; show "Former member" |
| Orphaned personal pins | Delete/hide | No one should see them if owner can't |
| AI context approach | Separate functions | Prevents leakage via code structure |
| Migration strategy | Alembic + manual fallback | Proven pattern in this codebase |

---

## Open Questions

1. Should sharing a pin trigger a notification to room members?
2. Should there be a limit on shared pins per chat/room?
3. Should shared pins show in a room-wide "All Shared Pins" view?

---

# Phase C: Pin-Seeded Chats

## Overview

Allow users to select pins and use them to create a new chat, where the AI generates an opening message based on the pinned content.

---

## Data Model Additions

### Pin Metadata (extend `pinned_items`)

```sql
-- Add to pinned_items table
ALTER TABLE pinned_items ADD COLUMN pin_type VARCHAR(20) DEFAULT 'general';
-- Types: 'question', 'insight', 'issue', 'reference', 'general'

-- Track source integrity
ALTER TABLE pinned_items ADD COLUMN source_deleted BOOLEAN DEFAULT FALSE;
```

### New Table: `pin_chat_sources`

Track which pins were used to create a chat (audit trail):

```sql
CREATE TABLE pin_chat_sources (
    id SERIAL PRIMARY KEY,  -- INTEGER PRIMARY KEY AUTOINCREMENT for SQLite
    chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
    pin_id INTEGER NOT NULL REFERENCES pinned_items(id) ON DELETE SET NULL,
    pin_content_snapshot TEXT NOT NULL,  -- Frozen content at creation time
    pin_type VARCHAR(20),
    pin_owner_id INTEGER REFERENCES "user"(id),
    is_shared_pin BOOLEAN NOT NULL,
    included_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_id, pin_id)
);

CREATE INDEX ix_pin_chat_sources_chat ON pin_chat_sources(chat_id);
```

---

## API Endpoints

### Pin Selection

| Endpoint | Purpose |
|----------|---------|
| `GET /room/<id>/pins/selectable` | List pins available for chat creation |
| `POST /room/<id>/chat/create-from-pins` | Create chat seeded with selected pins |

### Request: Create from Pins

```json
{
  "title": "Follow-up Discussion",
  "pin_ids": [12, 45, 78],
  "scope": "personal",  // or "shared" or "both"
  "mode": "explore"     // optional: learning mode
}
```

### Response

```json
{
  "success": true,
  "chat_id": 156,
  "pins_used": 3,
  "redirect_url": "/chat/156"
}
```

---

## Selection UX

### Multi-Select Interface

```
┌─────────────────────────────────────────────────┐
│ Start Chat from Pins                            │
├─────────────────────────────────────────────────┤
│ ○ My Pins  ● Shared Pins  ○ Both               │
├─────────────────────────────────────────────────┤
│ ☑ "How does authentication work?" (question)   │
│   From: API Security Chat • Pinned 2 days ago  │
│                                                 │
│ ☑ "Key insight about JWT tokens" (insight)     │
│   From: Auth Deep Dive • Shared by Alice       │
│                                                 │
│ ☐ "Bug: session timeout issue" (issue)         │
│   From: Bug Triage • Pinned yesterday          │
│                                                 │
│ ⚠️ "Old reference" (deleted source)            │
│   Source message was deleted                    │
├─────────────────────────────────────────────────┤
│ Using 2 of 10 pins (max)           [Create →]  │
└─────────────────────────────────────────────────┘
```

### Constraints

- **Max pins per chat**: 10 (configurable)
- **Deleted sources**: Show warning, allow inclusion (snapshot preserved)
- **Mixed visibility**: If "Both" selected, clearly label each pin's source

---

## AI Prompt Construction

### Token Budget Management

```python
def build_pin_seeded_prompt(pins, token_budget=2000):
    """
    Build prompt from selected pins, respecting token limits.
    
    Strategy:
    1. Sort pins by relevance/recency
    2. Include full content for first N pins
    3. Summarize remaining pins if over budget
    4. Always include pin types for context
    """
    
    prompt_parts = []
    tokens_used = 0
    
    for pin in sorted(pins, key=lambda p: p.created_at, reverse=True):
        pin_text = f"[{pin.pin_type}] {pin.content}"
        pin_tokens = estimate_tokens(pin_text)
        
        if tokens_used + pin_tokens < token_budget * 0.8:
            prompt_parts.append(pin_text)
            tokens_used += pin_tokens
        else:
            # Summarize remaining pins
            remaining = pins[pins.index(pin):]
            summary = f"Plus {len(remaining)} more pins about: {summarize_topics(remaining)}"
            prompt_parts.append(summary)
            break
    
    return "\n\n".join(prompt_parts)
```

### System Prompt Template

```
You are starting a new conversation based on pinned items from previous chats.

The user has selected these pins as context:

{pin_content}

Based on these pins, generate a thoughtful opening that:
1. Acknowledges the key themes/questions from the pins
2. Proposes a direction for this conversation
3. Asks a clarifying question if the pins suggest multiple paths

Keep your opening concise (2-3 paragraphs).
```

---

## Attribution & Audit

### In-Chat Display

At the top of a pin-seeded chat, show:

```
┌─────────────────────────────────────────────────┐
│ 📌 This chat was started from 3 pins:          │
│                                                 │
│ • "How does auth work?" — from API Security    │
│ • "JWT insight" — shared by Alice              │
│ • "Session bug" — from Bug Triage (deleted)    │
│                                                 │
│ [Show pins ▼]                    [Hide header] │
└─────────────────────────────────────────────────┘
```

### Privacy Rules

- **Personal pins**: Only visible to the owner in the audit trail
- **Shared pins**: Visible to all chat participants
- **Mixed chats**: Each user sees only pins they have access to

---

## Access Control

### Selection API Rules

```python
def get_selectable_pins(user, room_id, scope):
    """
    Returns pins available for chat creation.
    
    scope='personal': Only user's own pins
    scope='shared': Only shared pins in room
    scope='both': Personal + shared (labeled)
    """
    
    if scope == 'personal':
        return PinnedItem.query.filter_by(
            user_id=user.id, 
            room_id=room_id,
            is_shared=False
        ).all()
    
    elif scope == 'shared':
        return PinnedItem.query.filter_by(
            room_id=room_id,
            is_shared=True
        ).all()
    
    else:  # both
        personal = get_selectable_pins(user, room_id, 'personal')
        shared = get_selectable_pins(user, room_id, 'shared')
        return {'personal': personal, 'shared': shared}
```

### Creation API Rules

- Validate each `pin_id` belongs to allowed scope
- Reject if any personal pin doesn't belong to user
- Reject if any shared pin isn't actually shared
- Log which pins were used (audit trail)

---

## Source Integrity

### Handling Deleted Sources

```python
def mark_orphaned_pins():
    """
    Periodic task to mark pins whose source was deleted.
    Pins remain usable but show warning in UI.
    """
    
    orphaned_messages = db.session.execute("""
        UPDATE pinned_items 
        SET source_deleted = TRUE
        WHERE message_id IS NOT NULL 
        AND message_id NOT IN (SELECT id FROM message)
        AND source_deleted = FALSE
    """)
    
    orphaned_comments = db.session.execute("""
        UPDATE pinned_items 
        SET source_deleted = TRUE
        WHERE comment_id IS NOT NULL 
        AND comment_id NOT IN (SELECT id FROM comment)
        AND source_deleted = FALSE
    """)
```

### UI Treatment

- **Active source**: Normal display, jump link works
- **Deleted source**: Yellow warning icon, no jump link, tooltip "Source was deleted"
- **Still selectable**: Content snapshot preserved, can still use for new chats

---

## Implementation Phases (Phase C)

| Step | Scope | Risk | Effort |
|------|-------|------|--------|
| **C1** | Add `pin_type` column | Low | 30 min |
| **C2** | Add `source_deleted` column | Low | 30 min |
| **C3** | Create `pin_chat_sources` table | Low | 1 hr |
| **C4** | Build pin selection API | Medium | 2 hr |
| **C5** | Build prompt construction logic | **High** | 3 hr |
| **C6** | Build chat creation endpoint | Medium | 2 hr |
| **C7** | Build selection UI modal | Medium | 3 hr |
| **C8** | Build in-chat attribution header | Low | 1 hr |
| **C9** | Add orphaned pin detection | Low | 1 hr |
| **C10** | Tests: access control, prompt building | High | 3 hr |

**Phase C estimate**: ~17 hours  
**Total roadmap**: ~33 hours (Phase B + Phase C)

---

## Testing Checklist (Phase C)

### Access Control
- [ ] Personal pins only selectable by owner
- [ ] Shared pins selectable by any room member
- [ ] Non-member cannot access selection API
- [ ] Creation rejects unauthorized pin_ids

### Prompt Building
- [ ] Pins included in correct order (recency)
- [ ] Token budget respected
- [ ] Summarization kicks in when over budget
- [ ] Pin types included in prompt

### Attribution
- [ ] Audit trail created on chat creation
- [ ] Personal pins hidden from non-owners in audit
- [ ] Shared pins visible to all in audit
- [ ] Deleted source warning displayed

### Integrity
- [ ] Orphaned pins marked correctly
- [ ] Orphaned pins still selectable
- [ ] Jump links disabled for deleted sources
- [ ] Content snapshot preserved

---

## Files to Modify (Phase C)

### Backend
- `src/models/pin.py` — Add `pin_type`, `source_deleted`
- `src/models/pin_chat_source.py` — New model (audit trail)
- `src/utils/pin_helpers.py` — Selection and prompt building
- `src/app/room/routes/crud.py` — Create-from-pins endpoint
- `migrations/versions/` — New migrations

### Frontend
- `templates/room/` — Pin selection modal
- `templates/chat/view.html` — Attribution header
- `src/app/static/js/pin-selection.js` — New JS for modal
- `src/app/static/css/` — Selection UI styles

---

## Decision Log (Phase C)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Max pins per chat | 10 | Keeps prompt manageable, forces curation |
| Deleted source handling | Keep pin, show warning | Content snapshot is still valuable |
| Pin types | Optional enum | Helps filtering, not required |
| Audit trail | Separate table | Preserves history even if pin deleted |
| Token budget | 2000 tokens for pins | Leaves room for system prompt + response |

---

## Open Questions (Phase C)

1. Should pin-seeded chats have a special mode/label?
2. Should users be able to add more pins to an existing chat?
3. Should the AI opening message be editable before sending?
4. Should there be room-wide "Start from all shared pins" option?

