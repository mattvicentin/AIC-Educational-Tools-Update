# Next Steps: Migration Fix

## Current Situation

- ✅ All migrations are now idempotent (won't fail if tables/columns exist)
- ✅ Advisory lock implementation added to prevent race conditions
- ⚠️ Still seeing race condition errors in `/ready` endpoint
- ⚠️ Multiple workers racing to create Alembic's internal tables

## Step-by-Step Action Plan

### Step 1: Commit and Deploy the Advisory Lock Implementation

**What to do:**
```bash
# Review the changes
git diff src/main.py

# Commit the advisory lock implementation
git add src/main.py MIGRATION_STRATEGY_COMPARISON.md
git commit -m "feat: add PostgreSQL advisory locks to prevent migration race conditions

- Use pg_try_advisory_lock() to ensure only one worker runs migrations
- Other workers wait and check if migrations completed
- Better error handling for race condition edge cases
- Falls back gracefully if advisory locks unavailable (SQLite)"

# Push to trigger Railway deployment
git push
```

**Why:** This gives us automated migrations with race condition protection. If it works, we're done. If not, we fall back to Step 2.

---

### Step 2: Monitor the Deployment

**What to watch:**

1. **Railway Deployment Logs:**
   - Look for: `🔒 Acquiring migration lock...`
   - Look for: `✅ Migration lock acquired`
   - Look for: `⏳ Another worker is running migrations`
   - Should see only ONE worker running migrations

2. **Check `/ready` endpoint:**
   ```bash
   curl https://collab.up.railway.app/ready
   ```
   - Should show: `"status": "ready"`
   - Migrations should show: `"status": "applied"` or no errors

3. **Watch for errors:**
   - If you see `duplicate key value violates unique constraint "pg_type_typname_nsp_index"` → Advisory locks didn't fully prevent the race
   - If you see clean migration logs → Success!

**Timeline:** Wait 2-3 minutes after deployment completes

---

### Step 3A: If Advisory Locks Work ✅

**What you'll see:**
- Only one worker runs migrations
- Other workers wait and skip
- `/ready` endpoint shows `"status": "ready"`
- No race condition errors

**Action:**
- ✅ **Nothing!** You're done.
- Keep `RUN_DB_MIGRATIONS_ON_STARTUP=true` (default)
- Migrations will run automatically on each deployment
- No manual steps needed

---

### Step 3B: If Advisory Locks Don't Work ❌

**What you'll see:**
- Still seeing `duplicate key value violates unique constraint` errors
- Multiple workers still racing
- `/ready` endpoint still failing

**Why this might happen:**
- Alembic creates its own database connections internally
- Advisory lock might not fully protect Alembic's initialization
- Edge case with Alembic's internal state management

**Action: Disable Auto-Migrations**

1. **In Railway Dashboard:**
   - Go to your service → **Variables**
   - Add/Update: `RUN_DB_MIGRATIONS_ON_STARTUP=false`
   - Save (triggers redeploy)

2. **Run migrations manually (one-time):**
   ```bash
   # Option A: Railway CLI
   railway run alembic upgrade head
   
   # Option B: Railway Dashboard
   # Go to Deployments → New → Run Command
   # Command: alembic upgrade head
   ```

3. **Verify:**
   ```bash
   curl https://collab.up.railway.app/ready
   ```
   Should show: `"status": "ready"`

4. **For future deployments:**
   - Keep `RUN_DB_MIGRATIONS_ON_STARTUP=false`
   - Run `railway run alembic upgrade head` after each code deployment
   - Or add migration step to your CI/CD pipeline

---

## Recommended Approach

**My recommendation:** Try Step 1-2 first (advisory locks). If it works, you get automated migrations. If not, fall back to Step 3B (disable auto-migrations).

**Why:** 
- Advisory locks are a good solution if they work
- But disabling auto-migrations is the most reliable fallback
- Both approaches are now supported in the code

---

## Quick Decision Tree

```
Deploy advisory lock implementation
         │
         ├─→ Works? → ✅ Done! Keep RUN_DB_MIGRATIONS_ON_STARTUP=true
         │
         └─→ Still races? → Set RUN_DB_MIGRATIONS_ON_STARTUP=false
                            → Run migrations manually
                            → ✅ Done!
```

---

## Commands Summary

**Deploy the fix:**
```bash
git add src/main.py MIGRATION_STRATEGY_COMPARISON.md NEXT_STEPS_MIGRATION_FIX.md
git commit -m "feat: add PostgreSQL advisory locks for migration race prevention"
git push
```

**If advisory locks don't work:**
```bash
# In Railway: Set RUN_DB_MIGRATIONS_ON_STARTUP=false
# Then run:
railway run alembic upgrade head
```

**Check status:**
```bash
curl https://collab.up.railway.app/ready
```

---

## Expected Timeline

- **Deployment:** ~2-3 minutes
- **Testing:** ~2 minutes
- **Total:** ~5 minutes to know if it works

If it works, you're done. If not, 5 more minutes to disable and run manually.

