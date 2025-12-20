# Future Enhancement: Always-Visible Desktop Composer

**Status**: Planned (deploy after iPhone fixes are stable)  
**Priority**: Medium (UX enhancement, not bug fix)  
**Risk**: Low (desktop-only, isolated change)

---

## 🎯 Goal

Make input composer always visible on desktop (like focus mode) while keeping sidebar open.

---

## 📋 Implementation Plan

### **Phase 1: Deploy iPhone Fixes** ✅ **DO THIS NOW**
```
Current commits ready:
- c5237a3: Disable ChatTouchOptimizer on mobile
- 433e0c1: Stop auto-nudge + data-chat-id  
- 6088ed5: Remove preventDefault
- 0f5ce45: Sidebar icon guards
- 69c31f7: Polling URL fix

Deploy → Test → Confirm stable
```

### **Phase 2: Desktop Fixed Composer** 📅 **DO THIS LATER**

**CSS Change:**
```css
/* Desktop large screens: Always-visible composer */
@media (min-width: 1280px) {
    .chat-input-container {
        position: fixed !important;
        left: 0;
        right: 0;
        bottom: 0;
        margin: 0;
        z-index: 10000;
    }
    
    #chat-messages {
        /* Ensure padding always applied */
        padding-bottom: var(--chat-input-h, 120px);
    }
}

/* Tablets: Keep sticky (stable) */
@media (min-width: 768px) and (max-width: 1279px) {
    .chat-input-container {
        position: sticky;
    }
}

/* Mobile: Keep sticky (just fixed!) */
@media (max-width: 767px) {
    .chat-input-container {
        position: sticky;
    }
}
```

**JavaScript:** No changes needed (applyBottomPadding already works)

**Focus Mode Adjustment:**
```css
/* Focus mode on desktop: Edge-to-edge + hide sidebar */
body.focus-mode .chat-input-container {
    /* Already fixed, just ensure full-width */
    left: 0 !important;
    right: 0 !important;
    margin: 0 !important;
}
```

---

## 🧪 Testing Checklist (When Ready)

**Desktop (≥1280px):**
- [ ] Input always visible while scrolling
- [ ] Multi-line input updates padding
- [ ] Last message not hidden behind bar
- [ ] Scroll button above bar (z-index)
- [ ] Focus mode works (sidebar hides, edge-to-edge)
- [ ] Window resize updates padding
- [ ] No layout flicker

**Tablets (768-1279px):**
- [ ] Sticky behavior (unchanged from current)
- [ ] Sidebar works
- [ ] No conflicts

**Mobile (<768px):**
- [ ] Sticky behavior (unchanged - STABLE)
- [ ] iPhone scroll works naturally
- [ ] No regression

---

## 📊 Benefits vs Risks

**Benefits:**
- ✅ Better desktop UX (always-visible input)
- ✅ Like focus mode but keep sidebar
- ✅ Read & type simultaneously
- ✅ Professional feel

**Risks:**
- ⚠️ Padding must stay synced (but we have ResizeObserver)
- ⚠️ Z-index layering (easy to test)
- ⚠️ Breakpoint edge cases (iPad sizing)

**Mitigation:**
- 🛡️ Desktop-only (mobile unaffected)
- 🛡️ Media query isolated (easy rollback)
- 🛡️ Reuses existing infrastructure
- 🛡️ Test before promoting

---

## 🎯 Why Wait?

**Current State:**
- iPhone scroll fixes are critical
- Need testing and validation
- Mobile stability just restored

**Don't Risk:**
- Mixing stable fixes with new features
- Complex rollback if issues found
- Debugging multiple changes simultaneously

**Safe Approach:**
1. Deploy fixes → Test → Confirm stable
2. Add enhancement → Test → Deploy separately
3. Clean git history (easy bisect if needed)

---

## 📝 Implementation Notes (For Later)

**Files to Change:**
- `src/app/static/css/components.css` (media queries)
- `src/app/static/css/chat-improvements.css` (focus mode)
- Maybe: `chat-view.js` (ensure padding on desktop)

**Estimated Effort:** 30 minutes + testing

**Rollback:** Just revert one commit (media query changes)

---

**Status**: Documented, ready to implement after iPhone fixes stable  
**Date**: October 28, 2025
