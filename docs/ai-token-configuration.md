# AI Token & Context Configuration

## Overview
Control AI response length and conversation context via environment variables.

---

## Environment Variables

**Note:** These settings currently apply to the **Anthropic (Claude) path**. The OpenAI path still defaults to 300 tokens and would need the same environment handling if you switch to it in the future.

### `AI_MAX_TOKENS`
**Default:** `400`  
**Range:** `200-2000`  
**Purpose:** Maximum tokens for AI responses

**Impact:**
- **300 tokens** (old): ~225 words, frequent truncation
- **400 tokens** (new): ~300 words, 60% fewer truncations
- **500 tokens**: ~375 words, minimal truncation (higher cost)

**Example:**
```bash
AI_MAX_TOKENS=400  # Balanced (recommended)
AI_MAX_TOKENS=300  # More concise, more truncation
AI_MAX_TOKENS=500  # Longer responses, higher cost
```

**Cost Impact:**
- 300 → 400 tokens = 33% more API cost
- Worth it for better UX (fewer continue clicks)

---

### `AI_MAX_HISTORY`
**Default:** `8`  
**Range:** `4-20`  
**Purpose:** Number of conversation turns to include as context

**What is a "turn"?**
- 1 turn = 1 user message + 1 assistant response (a pair)
- 8 turns = 16 messages (last 8 user+assistant exchanges)

**Note:** History trimming currently applies to the **Anthropic path only** in `get_ai_response()`. The OpenAI helper doesn't trim context yet.

**Impact:**
- **4 turns**: Minimal context, faster responses, might lose continuity
- **8 turns**: Good balance (recommended)
- **12 turns**: More context, slower responses, better for complex topics
- **20 turns**: Maximum context, expensive, rarely needed

**Example:**
```bash
AI_MAX_HISTORY=8   # Balanced (recommended)
AI_MAX_HISTORY=6   # More concise, less context
AI_MAX_HISTORY=12  # More context for complex discussions
```

**Context Calculation:**
```
Conversation has 20 messages
AI_MAX_HISTORY=8
Last 8 turns = last 16 messages sent to AI
Messages 1-4 are not included (saves tokens)
```

---

## How It Works

### **get_ai_response() Function:**

```python
def get_ai_response(chat, max_tokens=None, ...):
    # Read config
    DEFAULT_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "400"))
    MAX_HISTORY_TURNS = int(os.getenv("AI_MAX_HISTORY", "8"))
    
    # Use provided or default
    if max_tokens is None:
        max_tokens = DEFAULT_MAX_TOKENS
    
    # Fetch all messages
    all_messages = Message.query.filter_by(chat_id=chat.id).all()
    
    # Cap to recent history
    if len(all_messages) > MAX_HISTORY_TURNS * 2:
        messages_payload = all_messages[-(MAX_HISTORY_TURNS * 2):]
        # Saves tokens by not sending full 20+ message history
    else:
        messages_payload = all_messages
    
    # Call API with configured max_tokens
    return call_anthropic_api(messages_payload, system, max_tokens)
```

---

## Tuning Guide

### **If Responses Truncate Too Often:**

**Option 1: Increase max_tokens**
```bash
AI_MAX_TOKENS=450  # or 500
```

**Option 2: Reduce context**
```bash
AI_MAX_HISTORY=6  # Saves tokens for response
```

**Option 3: Both**
```bash
AI_MAX_TOKENS=450
AI_MAX_HISTORY=6
```

---

### **If Responses Lose Context:**

**Option 1: Increase history**
```bash
AI_MAX_HISTORY=12  # More conversation context
```

**Option 2: Implement summarization** (future)
- Summarize messages 1-N
- Keep recent messages N+1 to end
- Best of both worlds

---

### **If API Costs Too High:**

**Option 1: Reduce max_tokens**
```bash
AI_MAX_TOKENS=350
```

**Option 2: Reduce history**
```bash
AI_MAX_HISTORY=6
```

**Option 3: Both**
```bash
AI_MAX_TOKENS=350
AI_MAX_HISTORY=6
```

---

## Monitoring

### **Watch For:**

**Truncation Rate:**
- Check logs for: "⚠️ Response truncated at X tokens"
- Target: <10% truncation rate
- If >20%: Increase `AI_MAX_TOKENS`

**Context Trimming:**
- Check logs for: "📊 Context trimmed: 20 messages → 16"
- If frequent: Consider increasing `AI_MAX_HISTORY`
- Or implement summarization

**API Costs:**
- Monitor Anthropic/OpenAI usage
- Compare before/after changing limits
- Adjust based on budget

---

## Examples

### **Scenario 1: Long Academic Discussion**
```bash
# Need more context for thesis development
AI_MAX_TOKENS=500
AI_MAX_HISTORY=12
```

### **Scenario 2: Quick Q&A Chatbot**
```bash
# Keep responses concise and fresh
AI_MAX_TOKENS=300
AI_MAX_HISTORY=4
```

### **Scenario 3: Balanced Learning (Recommended)**
```bash
# Good for most educational use cases
AI_MAX_TOKENS=400
AI_MAX_HISTORY=8
```

---

## Technical Details

### **Token Estimation:**
- 1 token ≈ 0.75 words (English)
- 400 tokens ≈ 300 words ≈ 1-2 paragraphs

### **Context Window:**
- Claude Sonnet: 200K tokens total
- Our limits are well within capacity
- Focus is on cost and response quality

### **Message History:**
- User message: ~50-200 tokens
- Assistant response: ~200-400 tokens
- 8 turns: ~2000-4000 tokens context
- System prompt: ~200-500 tokens
- **Total sent:** ~2500-5000 tokens per request

---

---

## Phase 2: Mode-Specific Response Tailoring

### Overview
Different learning modes need different response styles. Phase 2 adds mode-aware brevity hints.

### Mode-Specific Concise Instructions

**Built-in guidance per mode:**

| Mode | Concise Hint | Rationale |
|------|--------------|-----------|
| `explore` | Ask 2-3 probing questions, 2-3 short paragraphs | Early exploration needs questions, not essays |
| `focus` | Guide with 2-3 focused questions and brief examples | Help narrow without overwhelming |
| `context` | Suggest 2-3 key sources or search strategies | Concise source guidance |
| `proposal` | 2-3 paragraphs of guidance, use bullets for multiple points | Balance depth with clarity |
| `evidence` | Comment on 2-3 key pieces of evidence | Specific, focused feedback |
| `argument` | Highlight 2-3 main points to strengthen | Direct, actionable |
| `draft` | Focused feedback on structure and clarity (2-3 paragraphs) | Needs more depth than polish |
| `organize` | Suggest 2-3 concrete organizational improvements | Specific structural guidance |
| `polish` | 2-3 specific edits or refinements, be concise | Final stage, brief tweaks |
| `present` | 2-3 presentation tips, direct and actionable | Brief, practical |

**Implementation:**
These hints are appended to the system prompt:
```
{base_prompt}

STYLE GUIDANCE: {mode_concise_hint}
```

**No code changes needed** - works automatically based on chat.mode.

---

### Per-Mode Token Limits (Optional)

For modes that need more depth, you can override the default:

```bash
# Global default
AI_MAX_TOKENS=400

# Mode-specific overrides
AI_MAX_TOKENS_DRAFT=500      # Draft needs more room
AI_MAX_TOKENS_ARGUMENT=450   # Argument needs depth
AI_MAX_TOKENS_POLISH=350     # Polish is brief
```

**Pattern:** `AI_MAX_TOKENS_{MODE_KEY_UPPERCASE}`

**Examples:**
- `AI_MAX_TOKENS_EXPLORE=350` - Keep exploration brief
- `AI_MAX_TOKENS_DRAFT=500` - Give drafting more room
- `AI_MAX_TOKENS_POLISH=300` - Polish is concise

---

### How It Works Together

**Example - Explore Mode:**
```
User in "explore" mode chat asks question
  ↓
System builds prompt:
  Base: "You are an expert instructor..."
  +
  Concise hint: "Ask 2-3 probing questions. Keep explanations 
                 to 2-3 short paragraphs."
  +
  Token limit: AI_MAX_TOKENS_EXPLORE (if set) or 400 (default)
  ↓
AI responds with:
  - 2-3 thoughtful questions
  - Brief explanation
  - Stays within token limit
  - Less likely to truncate
```

**Example - Draft Mode:**
```
User in "draft" mode gets feedback
  ↓
System builds prompt:
  Base: "You are an expert writing coach..."
  +
  Concise hint: "Provide focused feedback on structure and 
                 clarity (2-3 paragraphs)."
  +
  Token limit: AI_MAX_TOKENS_DRAFT=500 (more room for depth)
  ↓
AI responds with:
  - Detailed structural feedback
  - Uses extra tokens (500 vs 400)
  - Appropriate depth for drafting stage
```

---

### Benefits

**Mode-Aware Responses:**
- ✅ Exploration modes: Brief, question-focused
- ✅ Development modes: Balanced guidance
- ✅ Refinement modes: Specific, concise feedback
- ✅ Natural fit to learning stage

**Reduced Truncation:**
- Early modes use fewer tokens (more concise)
- Later modes can use more tokens (if configured)
- Better token budget management

**Improved Learning:**
- Right level of detail for each stage
- No overwhelming bullet lists in early exploration
- Sufficient depth when needed for drafting
- Concise, actionable polish feedback

---

**Date:** November 27, 2025  
**Version:** 3.2.0 (Phase 2)  
**Status:** Implemented and configurable

