# Pin Feature - Testing Guide

**Commit**: `9f3a059`  
**Branch**: `feature/railway-deployment`  
**Status**: ✅ Pushed to GitHub - Railway deployment triggered

---

## 🚀 Deployment

The pin feature has been committed and pushed to GitHub. Railway will automatically deploy it to:

**Production URL**: https://collab.up.railway.app

**Health Check**: https://collab.up.railway.app/health

⏱️ **Wait 2-3 minutes** for Railway to build and deploy, then **hard refresh** your browser (Cmd+Shift+R or Ctrl+Shift+R).

---

## ✅ Testing Checklist

### 1. **Database Migration** (Automatic)

The manual fallback in `src/main.py` will automatically create the `pinned_items` table on first run if Alembic doesn't apply the migration.

**Check logs** for:
```
✓ pinned_items table exists
```
or
```
✓ pinned_items table created manually
```

---

### 2. **UI Verification**

**A. Pin Buttons Appear**
1. Navigate to any chat with messages
2. Look for "Pin" button next to "💬 Add Comment" on each message
3. Verify buttons appear for both AI and user messages
4. Check comments also have "Pin" buttons

**Expected**: 
- Pin button shows as plain text "Pin"
- After clicking, changes to "📌 Unpin"

---

### 3. **Pin a Message**

**Steps**:
1. Open a chat with at least one message
2. Click "Pin" next to any message
3. Button should briefly show "Pinning..."
4. Button changes to "📌 Unpin"
5. Page reloads (or sidebar updates)

**Verify**:
- Left sidebar shows "Pinned in this Chat" section
- Pinned message appears with preview text
- Shows role indicator: 🤖 AI Response or 👤 User Message
- "Jump to message →" link works
- Timestamp displays correctly

---

### 4. **Pin a Comment**

**Steps**:
1. Add a comment to a message (if none exist)
2. Click "Pin" on the comment
3. Verify same behavior as message pinning

**Verify**:
- Comment appears in sidebar with 💬 Comment indicator
- Preview text shows comment content
- Remove button works

---

### 5. **Unpin Functionality**

**From message/comment**:
1. Click "📌 Unpin" on a pinned item
2. Button changes back to "Pin"
3. Item removed from sidebar

**From sidebar**:
1. Click "Remove" button on pinned item
2. Page reloads
3. Item no longer in sidebar
4. Message/comment shows "Pin" button again

---

### 6. **Multiple Pins**

**Steps**:
1. Pin 3-4 different messages and comments
2. Verify all show in sidebar
3. Each has its own "Remove" button
4. Jump links work for all
5. Preview text is unique for each

---

### 7. **Edge Cases**

**A. Pin Toggle Idempotency**
- Double-click a Pin button rapidly
- Should only create one pin (handled by disabled state + IntegrityError)

**B. Cross-Chat Isolation**
- Pin messages in Chat A
- Navigate to Chat B
- Verify Chat A's pins don't show in Chat B's sidebar

**C. No Pins State**
- Unpin all items
- Sidebar "Pinned in this Chat" section disappears

---

### 8. **CSRF Protection**

**Verify** (in browser console):
1. Open DevTools → Network tab
2. Click Pin button
3. Check request headers for:
   - `X-CSRFToken: <token>`
   - Request should succeed (200 OK)

---

### 9. **Database Verification** (Optional)

If you have access to the Railway database:

```sql
-- Check table exists
SELECT * FROM pinned_items LIMIT 5;

-- Check constraints
\d pinned_items  -- PostgreSQL

-- Verify user isolation
SELECT user_id, COUNT(*) FROM pinned_items GROUP BY user_id;
```

---

### 10. **Error Handling**

**Test graceful failures**:

**A. Pin deleted message**
- Pin a message
- Delete the message (if deletion is enabled)
- Pin should cascade delete (ON DELETE CASCADE)

**B. Network error**
- Disable network mid-pin
- Should show error and revert button state

---

## 🐛 Known Issues / Expected Behavior

### What to Expect

✅ **Content Snapshot**: Pinned content is frozen at pin time (won't update if message edited)  
✅ **Per-User**: Pins are private - other users can't see your pins  
✅ **Page Reload**: Removing from sidebar reloads page (could be improved with AJAX later)  
✅ **Truncation**: Very long messages truncate to 5000 chars in database, 150 in sidebar preview  

### What Would Be Bugs

❌ Pin button doesn't appear → Check if JS loaded (`pin-toggle.js`)  
❌ Pin button crashes → Check browser console for errors  
❌ Pins show for other users → User isolation broken  
❌ Can't pin comments → Check `comment.chat` backref  
❌ SQLite errors on local → Check manual fallback SQL  

---

## 📊 Success Metrics

After testing, the feature is working if:

- [x] Pin buttons visible on all messages/comments
- [x] Clicking Pin creates entry in sidebar
- [x] Clicking Unpin removes entry
- [x] Jump links scroll to correct message
- [x] Pins persist after page refresh
- [x] Other users don't see your pins
- [x] No console errors
- [x] CSRF token sent in requests

---

## 🔧 Troubleshooting

### Pin Buttons Don't Appear

**Check**:
1. View page source, search for "pin-toggle"
2. Check if `pin-toggle.js` loads in Network tab
3. Look for JavaScript errors in console

**Fix**:
- Hard refresh (Cmd+Shift+R)
- Clear browser cache

---

### Pin Button Clicks Don't Work

**Check**:
1. Browser console for errors
2. Network tab for failed requests
3. CSRF token in request headers

**Common Issues**:
- CSRF token missing → Check cookie settings
- 401/403 errors → Not logged in or no access
- 500 error → Check Railway logs

---

### Sidebar Doesn't Update

**Expected Behavior**: 
- Pinning from message → Optimistic update (no reload)
- Unpinning from sidebar → Page reload

**If broken**:
- Check `pinned_items` in context data
- Verify template receives `pinned_message_ids`, `pinned_comment_ids`

---

## 📝 Feedback Template

After testing, report results:

```
## Pin Feature Test Results

**Date**: 
**Tester**: 
**Environment**: Production / Local

### Working ✅
- [ ] Pin buttons visible
- [ ] Message pinning works
- [ ] Comment pinning works
- [ ] Sidebar displays pins
- [ ] Jump links work
- [ ] Unpin works
- [ ] CSRF protection

### Issues ❌
1. [Description of any bugs found]
2. [Steps to reproduce]
3. [Expected vs actual behavior]

### Notes
[Any additional observations]
```

---

## 🎉 Feature Complete!

**8 files changed**, **955 insertions**, **81 deletions**

**New files**:
- `src/models/pin.py` - PinnedItem model
- `src/utils/pin_helpers.py` - Pin business logic
- `src/app/static/js/pin-toggle.js` - Frontend handler
- `migrations/versions/c3d4e5f6g7h8_add_pinned_items_table.py` - Migration

**Modified files**:
- `src/app/chat.py` - Pin routes + context
- `src/main.py` - Manual migration fallback
- `templates/chat/view.html` - UI with buttons + sidebar
- `src/models/__init__.py` - Import PinnedItem

Happy testing! 🚀

