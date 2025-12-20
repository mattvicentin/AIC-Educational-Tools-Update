# 🧭 AI System Improvement Plan

### **1. Truncation-Aware “Continue” Button**
**Problem:** Long messages are sometimes cut off (`finish_reason == "length"`) but every message currently shows a “Continue” button.  
**Why:** Restores flow, prevents user confusion, and signals completion status clearly.  
**How:**
- In `openai_utils.py` and `anthropic` call handlers, set:
  ```python
  is_truncated = (finish_reason == "length" or stop_reason == "max_tokens")
  ```
- Save this flag with each assistant message:
  ```python
  ai_msg = Message(..., is_truncated=is_truncated)
  ```
- In `templates/chat/view.html`, show the button only when true:
  ```jinja2
  {% if m.role == "assistant" and m.is_truncated %}
     <button class="continue-btn" data-msg-id="{{ m.id }}">Continue ↻</button>
  {% endif %}
  ```
- Add a `/continue` route in Flask that posts the prior chat and a user cue like “Please continue where you left off.”
- JS: on click, fetch the continuation and insert it below the truncated message.

---

### **2. Whitelist the Critique “Tone” Field**
**Problem:** `extra_system` can contain arbitrary user text → injection risk.  
**Why:** Keeps tone control safe and predictable.  
**How:**
- Define allowed tones:
  ```python
  ALLOWED_TONES = {
      "1": "Be warmly supportive...",
      "3": "Be neutral and concise...",
      "5": "Be rigorous and analytical..."
  }
  tone = request.form.get("critique_level")
  extra_system = ALLOWED_TONES.get(tone, "")
  ```
- Pass only this value to `get_ai_response()`.

---

### **3. Mode Guardrails (Soft Constraints)**
**Problem:** Models sometimes output essays in “explore” or under-question in “draft.”  
**Why:** Keeps each stage aligned to its learning intent.  
**How:**
- Before calling the API:
  ```python
  if mode == "explore":
      system_prompt += "\n\nCONSTRAINT: Ask 2–3 probing questions; do not produce full answers."
  elif mode == "draft":
      system_prompt += "\n\nCONSTRAINT: Focus on structure, not new ideas."
  ```
- Avoid hard validation; simply guide generation.

---

### **4. Deterministic Defaults per Mode**
**Problem:** Responses vary too widely; formative feedback should be consistent.  
**Why:** Makes comparisons and assessments fair.  
**How:**
- Adjust generation settings by mode:
  ```python
  TEMPERATURES = {"explore": 0.4, "focus": 0.5, "draft": 0.6}
  temp = TEMPERATURES.get(mode, 0.5)
  response = call_model(messages, temperature=temp)
  ```
- Lower temperature for analytical tasks; higher for creative brainstorming.

---

### **5. Minimal Provenance Line (Transparency)**
**Problem:** Students can’t tell which mode or tone shaped a response.  
**Why:** Builds metacognition and trust.  
**How:**
- Append to `system_prompt`:
  ```python
  system_prompt += "\n\nAt the start of each reply, state briefly: 'Mode: {mode}; Tone: {tone}; Context: {context_source}'."
  ```
- Or toggle display in UI (`show provenance` checkbox).

---

### **6. Token Budgeting + Safe Truncation**
**Problem:** Long chats overflow context limits; early messages vanish abruptly.  
**Why:** Keeps continuity and prevents API errors.  
**How:**
- Estimate token use:
  ```python
  def estimate_tokens(msgs): return sum(len(m['content'].split())/0.75 for m in msgs)
  if estimate_tokens(messages) > BUDGET:
      summary = summarize_early_turns(messages)
      messages = [system_msg, summary] + get_recent(messages, k=8)
  ```
- Summarize *earliest* turns into bullet notes (e.g., 50–80 words).

---

### **7. Lightweight Retries + Fallback**
**Problem:** Occasional timeouts or 502s disrupt conversation.  
**Why:** Improves reliability without new infrastructure.  
**How:**
```python
import time, random
for i in range(3):
    try:
        return call_model(...)
    except (TimeoutError, requests.exceptions.RequestException):
        time.sleep(0.8 * (2**i) + random.random())
# Fallback message
return "I had a short connection delay — here's a concise next step while I reconnect..."
```

---

### **8. Critique Tone Anchors**
**Problem:** Tone slider descriptions are vague → inconsistent behavior.  
**Why:** Improves clarity and calibration across sessions.  
**How:**
```python
TONE_ANCHORS = {
  1: "Encourage curiosity and effort; avoid criticism.",
  3: "Balanced and constructive; give specific guidance.",
  5: "Rigorous and analytical; challenge unsupported reasoning."
}
system_prompt += f"\n\nTone Guidance: {TONE_ANCHORS[tone_level]}"
```

---

### **9. Modular Prompt Structure**
**Problem:** Each mode prompt is written separately; inconsistent phrasing.  
**Why:** Simplifies maintenance and ensures pedagogical uniformity.  
**How:**
```python
HEADER = "You are an AI instructor guiding reflective academic dialogue."
FOOTER = "Encourage reflection; never write final essays; keep curiosity alive."

system_prompt = f"{HEADER}\n\n{BASE_MODES[mode].prompt}\n\n{FOOTER}"
```
- Store HEADER/FOOTER centrally in a config or YAML.

---

### **10. Self-Check Micro-Instruction**
**Problem:** Model occasionally forgets to ask reflective questions.  
**Why:** Improves adherence to teaching behavior.  
**How:**
Add this to system prompt end:
```text
Before finalizing your reply, verify that you have:
1. Asked at least one reflective question.
2. Avoided giving a full solution.
If not, revise your response briefly before sending.
```

---

## ✅ **Implementation Order (Recommended)**
| Priority | Improvement | Effort | Impact | Type |
|-----------|--------------|--------|---------|------|
| 1 | Truncation-aware Continue button | Low | ⭐⭐⭐⭐ | UX |
| 2 | Whitelist critique tone | Low | ⭐⭐⭐⭐ | Safety |
| 3 | Mode guardrails | Low | ⭐⭐⭐ | Pedagogy |
| 4 | Deterministic defaults | Low | ⭐⭐⭐ | Consistency |
| 5 | Provenance line | Low | ⭐⭐⭐ | Transparency |
| 6 | Token budgeting | Medium | ⭐⭐⭐ | Stability |
| 7 | Retries + fallback | Low | ⭐⭐ | Reliability |
| 8 | Tone anchors | Low | ⭐⭐ | Clarity |
| 9 | Modular prompt structure | Medium | ⭐⭐ | Maintainability |
| 10 | Self-check instruction | Low | ⭐⭐ | Pedagogical fidelity |

---

**Summary:**  
Start with fixes that make the AI **complete**, **safe**, and **predictable** (1–5).  
Add structural and robustness layers (6–10) once stability and tone reliability are solid.
