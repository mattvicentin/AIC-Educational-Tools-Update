# Sticky Composer Fix - October 28, 2025

## 🎯 Goal: Restore Hovering Input UX

**User Feedback**: "We lost the hovering input bar - users need to read previous messages while typing"

**Root Cause**: Changed from `position: fixed` to `position: relative` caused composer to scroll away.

---

## ✅ Solution: position: sticky

### **What We Did:**

#### **1. Changed Composer to `position: sticky`**
**File**: `src/app/static/css/components.css:393`

```css
.chat-input-container {
  position: sticky;  /* Hovers at bottom while scrolling */
  bottom: env(safe-area-inset-bottom, 16px);
  margin: 0 16px;
}
```

**Result**: Composer stays visible while scrolling, but remains in flex flow.

---

#### **2. Cleaned Up Mobile Overrides**
**Files**: `components.css:714-718` and `components.css:1551-1555`

- Removed redundant `position: sticky` rules
- Kept padding adjustments for mobile
- Main rule now handles all viewports

---

#### **3. Renamed Function: `updateComposerPadding()`**
**File**: `templates/chat/view.html:749`

**Before**: `enforceFocusModeLayout()` - Only ran in focus mode  
**After**: `updateComposerPadding()` - Runs in BOTH modes

**New Logic**:
```javascript
function updateComposerPadding() {
    // Works in BOTH sticky and fixed modes
    const messagesEl = document.getElementById('chat-messages');
    const composerEl = document.querySelector('.chat-input-container');
    
    if (!messagesEl || !composerEl) return;
    
    // Measure actual heights
    const composerHeight = composerEl.offsetHeight || 0;
    const safeAreaBottom = parseInt(getComputedStyle(...)) || 16;
    const buffer = 8;
    const totalPadding = composerHeight + Math.max(safeAreaBottom, 16) + buffer;
    
    // Set CSS variable (works for sticky AND fixed)
    messagesEl.style.setProperty('--chat-input-h', totalPadding + 'px');
}
```

---

#### **4. Wired ResizeObserver for Both Modes**
**File**: `templates/chat/view.html:784-793`

**Before**: Only called in focus mode  
**After**: Calls `updateComposerPadding()` always

```javascript
const textareaObserver = new ResizeObserver(() => {
    updateComposerPadding();  // Works in both modes
});
textareaObserver.observe(messageInputEl);

// Initial calculation
setTimeout(() => updateComposerPadding(), 100);
```

---

#### **5. Updated Resize Listener**
**File**: `templates/chat/view.html:782`

**Before**: `if (focus-mode) updateComposerPadding()`  
**After**: `updateComposerPadding()` - Always runs

---

## 🏗️ Final Architecture

### **Normal Mode (Sticky):**
```
Position: sticky (hovers at bottom)
Padding: Dynamic via ResizeObserver
Behavior: Input stays visible while scrolling
Z-index: 100 (above content)
Layout: In flex flow (clean architecture)
```

### **Focus Mode (Fixed Overlay):**
```
Position: fixed !important (full-width)
Padding: Dynamic via same ResizeObserver
Behavior: Edge-to-edge overlay, hides all chrome
Z-index: 10000 (above everything)
Layout: Overlay, max contrast
```

### **Shared Padding System:**
```
Both modes use updateComposerPadding():
  - Measures actual composer height
  - Reads real safe-area-inset-bottom (iPhone X+)
  - Adds 8px buffer
  - Sets --chat-input-h CSS variable
  
ResizeObserver triggers on:
  - Textarea growth (multi-line typing)
  - Window resize
  - Focus mode toggle
```

---

## 📊 What This Achieves

### **UX Restored:**
- ✅ Hovering input in normal mode (can read while typing)
- ✅ Focus mode is now high-contrast (hides chrome, full-width)
- ✅ Clear visual difference between modes

### **Architecture Benefits:**
- ✅ position: sticky (browser-native, no JS positioning)
- ✅ Still in flex flow (proper architecture)
- ✅ One padding function (works in both modes)
- ✅ ResizeObserver prevents race conditions
- ✅ Reads actual safe-area (iPhone X+ support)

### **Performance:**
- ✅ No JS positioning calculations
- ✅ Browser-native sticky behavior
- ✅ ResizeObserver only fires on actual changes
- ✅ Minimal JavaScript overhead

---

## 🧪 Testing Checklist

### **Desktop - Normal Mode:**
- [ ] Composer hovers at bottom while scrolling ← **KEY TEST**
- [ ] Can scroll up and read messages while input visible
- [ ] Multi-line message → padding adjusts
- [ ] Glass effect looks good
- [ ] Side margins preserved (16px)

### **Desktop - Focus Mode:**
- [ ] Click "Focus" → clear visual change
- [ ] Sidebar disappears
- [ ] Header/footer disappear
- [ ] Composer becomes full-width (edge-to-edge)
- [ ] "Exit Focus" restores normal mode

### **iPhone Safari:**
- [ ] Composer sticky at bottom
- [ ] Safe-area respected (34px on X+)
- [ ] Multi-line typing → padding grows
- [ ] Keyboard appearance → no layout break
- [ ] Focus mode works

---

## 🔄 Fallback Plan (If Sticky Fails on Mobile)

If `position: sticky` is glitchy on iOS:

```css
/* Desktop: sticky works great */
@media (min-width: 769px) {
  .chat-input-container {
    position: sticky;
    bottom: env(safe-area-inset-bottom, 16px);
  }
}

/* Mobile: fall back to fixed if needed */
@media (max-width: 768px) {
  .chat-input-container {
    position: fixed;
    bottom: env(safe-area-inset-bottom, 16px);
    left: 16px;
    right: 16px;
  }
}
```

**Note**: Same `updateComposerPadding()` function works for both sticky and fixed!

---

## 📝 Changes Summary

**Files Modified**: 2
- `components.css`: Changed to `position: sticky`, cleaned overrides
- `chat/view.html`: Renamed function, wired ResizeObserver for both modes

**Net Change**: Minimal (+17 insertions, -18 deletions)

**Complexity**: Same or lower (one clean padding function)

---

## 🎓 Key Insight

**position: sticky is the sweet spot:**
- Gives hovering UX like `fixed`
- Keeps proper architecture like `relative`
- Browser-native, no JS positioning
- Works with same padding logic in both modes

**Focus mode becomes a true enhancement:**
- Not just "hide sidebar"
- Full-width edge-to-edge overlay
- Maximum contrast vs normal mode
- Clear before/after difference

---

**Status**: Ready for testing  
**Risk**: Low (minimal changes)  
**Confidence**: High (sticky is well-supported)

**Author**: AI Assistant  
**Date**: October 28, 2025
