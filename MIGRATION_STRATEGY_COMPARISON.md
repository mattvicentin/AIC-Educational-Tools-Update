# Migration Strategy Comparison

## The Problem

Multiple Gunicorn workers start simultaneously and all try to run Alembic migrations, causing:
- Race conditions when creating `alembic_version` table
- `duplicate key value violates unique constraint` errors
- `/ready` endpoint failures

## Solution Options

### Option 1: Disable Auto-Migrations (Current Recommendation)

**How it works:**
- Set `RUN_DB_MIGRATIONS_ON_STARTUP=false` in Railway
- Run migrations manually via `railway run alembic upgrade head`
- Workers skip migrations on startup

**Pros:**
- ✅ Simple and reliable
- ✅ No race conditions
- ✅ Explicit control over when migrations run
- ✅ Industry standard practice (migrations as separate step)

**Cons:**
- ❌ Requires manual step (easy to forget)
- ❌ Not fully automated
- ❌ Need to remember to run migrations after deploying

**Best for:** Production environments where you want explicit control

---

### Option 2: PostgreSQL Advisory Locks (Just Implemented)

**How it works:**
- Use `pg_try_advisory_lock()` to ensure only one worker runs migrations
- Other workers wait and check if migrations completed
- Lock is held for the entire migration process

**Pros:**
- ✅ Fully automated
- ✅ Prevents race conditions
- ✅ Works across containers/workers
- ✅ No manual intervention needed

**Cons:**
- ❌ More complex code
- ❌ Requires PostgreSQL (doesn't work with SQLite)
- ❌ Still has edge cases (Alembic uses its own connections)
- ❌ Lock might not protect Alembic's internal connection creation

**Best for:** Environments where you want fully automated migrations

**Note:** There's a limitation - Alembic creates its own database connections internally, so the advisory lock on our connection might not fully protect Alembic's initialization. This could still have race conditions.

---

### Option 3: Single Worker Migration (Railway-Specific)

**How it works:**
- Scale workers to 1 temporarily
- Run migrations
- Scale back to 2+ workers

**Pros:**
- ✅ Simple
- ✅ No code changes needed
- ✅ Guaranteed no race conditions

**Cons:**
- ❌ Requires manual scaling
- ❌ Not automated
- ❌ Service downtime during migration

**Best for:** One-time fixes or manual deployments

---

### Option 4: Better Error Handling (Current Partial Implementation)

**How it works:**
- Catch race condition errors
- Check if migrations actually completed despite error
- Mark as success if another worker completed them

**Pros:**
- ✅ Handles races gracefully
- ✅ No manual steps
- ✅ Works with existing code

**Cons:**
- ❌ Still has races (just handles them)
- ❌ Less clean than preventing races
- ❌ Error messages in logs

**Best for:** Quick fixes, but not ideal long-term

---

## Recommendation

**For Production (Railway):**

**Best Approach:** **Option 1 (Disable Auto-Migrations)**

**Why:**
1. **Industry Standard**: Most production deployments run migrations as a separate step
2. **Explicit Control**: You know exactly when migrations run
3. **No Race Conditions**: Guaranteed single execution
4. **Reliability**: No complex locking logic that could fail
5. **CI/CD Friendly**: Easy to add migration step to deployment pipeline

**Implementation:**
```bash
# In Railway:
# 1. Set RUN_DB_MIGRATIONS_ON_STARTUP=false
# 2. Add migration step to deployment:
railway run alembic upgrade head
```

**For Development:**

**Best Approach:** **Option 1 or Option 2**

- Single worker = no races, so auto-migrations are fine
- Or disable and run manually: `alembic upgrade head`

---

## Hybrid Approach (Best of Both Worlds)

**What I Just Implemented:**

1. **Advisory locks** to prevent races (Option 2)
2. **Better error handling** to catch any remaining races (Option 4)
3. **Environment flag** to disable if needed (Option 1)

**How it works:**
- If `RUN_DB_MIGRATIONS_ON_STARTUP=false`: Skip migrations (manual control)
- If `RUN_DB_MIGRATIONS_ON_STARTUP=true`: Use advisory locks + error handling

**Pros:**
- ✅ Automated by default
- ✅ Can be disabled for explicit control
- ✅ Handles edge cases gracefully

**Cons:**
- ❌ More complex code
- ❌ Still might have edge cases with Alembic's internal connections

---

## My Answer to Your Question

**"Is disabling auto-migrations the best way?"**

**Short answer:** Yes, for production. It's the most reliable and industry-standard approach.

**Long answer:** 

The **best practice** is to run migrations as a **separate deployment step**, not during application startup. This is what most production systems do:

1. **Deploy code** → Workers start
2. **Run migrations** → Separate step (via CLI, CI/CD, or init container)
3. **Verify** → Check `/ready` endpoint

However, I've also implemented **advisory locks** as a fallback for automated migrations. This gives you:

- **Option A**: Set `RUN_DB_MIGRATIONS_ON_STARTUP=false` and run migrations manually (most reliable)
- **Option B**: Keep `RUN_DB_MIGRATIONS_ON_STARTUP=true` and let the advisory lock system handle it (automated, but might have edge cases)

**My recommendation:** Use Option A (disable auto-migrations) for production, but keep the advisory lock code as a safety net.

---

## Next Steps

1. **Test the advisory lock implementation** - Deploy and see if it prevents races
2. **If it works**: Keep `RUN_DB_MIGRATIONS_ON_STARTUP=true` for convenience
3. **If races still occur**: Set `RUN_DB_MIGRATIONS_ON_STARTUP=false` and run migrations manually

The code now supports both approaches, so you can choose based on what works best for your deployment workflow.

