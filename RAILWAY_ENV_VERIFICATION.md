# Railway Environment Variables & Setup Verification

## 🔍 Environment Variables Checklist

### Required Variables (Set in Railway Dashboard → Service → Variables)

| Variable | Required Value | Purpose | Status |
|----------|---------------|---------|--------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection | ✅ Auto-provided by Railway |
| `SECRET_KEY` | `your-secret-key-here` | Flask session encryption | ⚠️ **MUST SET MANUALLY** |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude AI API key | ⚠️ **MUST SET MANUALLY** |
| `OPENAI_API_KEY` | `sk-...` (optional) | OpenAI API key (if using) | ⚠️ Optional |
| `USE_RAILWAY_DOCUMENTS` | `true` | Enable Library Tool | ⚠️ **MUST SET** |
| `ENABLE_RAILWAY_FALLBACK` | `false` | Railway-only mode (no Supabase) | ⚠️ **RECOMMENDED** |
| `FLASK_ENV` | `production` | Production mode | ✅ Set in railway.toml |
| `PORT` | (auto-set) | Server port | ✅ Auto-set by Railway |
| `RAILWAY_ENVIRONMENT` | `true` (optional) | Railway detection | ⚠️ Optional |

### How to Set Variables in Railway

1. Go to **Railway Dashboard** → Your Project → Your Service
2. Click **"Variables"** tab
3. Click **"New Variable"** for each required variable
4. Enter variable name and value
5. Click **"Add"**

### Verification Commands (Railway CLI)

If you have Railway CLI installed:

```bash
# List all variables
railway variables

# Check specific variables
railway variables | grep -E "DATABASE_URL|SECRET_KEY|USE_RAILWAY_DOCUMENTS|ANTHROPIC_API_KEY"

# Set a variable (if needed)
railway variables set USE_RAILWAY_DOCUMENTS=true
railway variables set ENABLE_RAILWAY_FALLBACK=false
railway variables set SECRET_KEY=your-secret-key-here
railway variables set ANTHROPIC_API_KEY=sk-ant-...
```

---

## 🗄️ PostgreSQL Setup Verification

### 1. Verify pg_trgm Extension

**Option A: Railway CLI**
```bash
# Connect to PostgreSQL
railway connect postgres

# Then in psql:
\dx pg_trgm

# If not enabled, enable it:
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**Option B: Railway Dashboard**
1. Go to **PostgreSQL** service
2. Click **"Connect"** → **"Query"**
3. Run:
```sql
-- Check if pg_trgm exists
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';

-- If not found, enable it:
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify it's enabled:
\dx pg_trgm
```

**Expected Output**:
```
extname | extversion | nspname
--------+------------+---------
pg_trgm | 1.6        | public
```

### 2. Verify Migration Status

**Check Current Migration**:
```bash
railway run alembic current
```

**Expected Output** (after Library Tool migration):
```
add_document_tables_railway (head)
```

**If Migration Not Applied**:
```bash
# Check migration history
railway run alembic history

# Apply migrations
railway run alembic upgrade head
```

**Verify Tables Exist**:
```sql
-- Connect to PostgreSQL and run:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('document', 'document_chunk', 'room');

-- Should return:
-- document
-- document_chunk
-- room
```

---

## 🚀 Post-Deployment Verification

### 1. Check Deployment Logs

Go to Railway Dashboard → Deployments → Latest Deployment → **"Logs"**

**Look for**:
- ✅ `✅ Alembic migrations complete.`
- ✅ `🚀 FLASK APP CREATED`
- ✅ `✅ Database tables initialized successfully`
- ⚠️ Any migration errors or warnings

### 2. Test Health Endpoint

**Note**: `/health` endpoint is wrapped in try/except and may mask errors. Use `/ready` for real status.

```bash
# Health check (may mask errors)
curl https://collab.up.railway.app/health

# Expected: {"status": "alive", "timestamp": "..."}

# Ready check (shows real status)
curl https://collab.up.railway.app/ready

# Expected: {"status": "ready", "checks": {...}}
```

### 3. Verify Auto-Migration

The app runs migrations automatically on startup via `src/main.py` → `run_production_migrations()`.

**Check logs for**:
```
Running Alembic migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Running upgrade ...
✅ Alembic migrations complete.
```

**If Migration Fails**:
- Check logs for specific error
- Manually run: `railway run alembic upgrade head`
- Verify `pg_trgm` extension is enabled

### 4. Test Library Tool

Once app is running:

1. **Navigate to a chat room**: `https://collab.up.railway.app/chat/[chat_id]`
2. **Check sidebar**: Library Tool card should be visible
3. **Upload test document**: Try uploading a small PDF/DOCX/TXT
4. **Verify upload works**: Document should appear in list

---

## 🐛 Troubleshooting

### Issue: `/ready` Shows Database Error

**Symptom**: 
```json
{
  "checks": {
    "database": {
      "message": "The current Flask app is not registered with this 'SQLAlchemy' instance...",
      "status": "error"
    }
  }
}
```

**Solution**: This is a check issue, not a startup blocker. The app should still work. If app doesn't start, check:
- Environment variables are set correctly
- Database connection works
- Migrations are applied

### Issue: Migration Fails with "pg_trgm does not exist"

**Symptom**: 
```
ERROR: extension "pg_trgm" does not exist
```

**Solution**:
```sql
-- Connect to PostgreSQL and run:
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Issue: Migration Fails with "column already exists"

**Symptom**:
```
column "group_size" of relation "room" already exists
```

**Solution**: Fixed in latest commit - migration is now idempotent. Redeploy should fix it.

### Issue: ModuleNotFoundError: No module named 'anthropic'

**Symptom**: App crashes on startup

**Solution**: Fixed in latest commit - `anthropic` added to `requirements.txt`. Redeploy should fix it.

### Issue: Library Tool Not Working

**Check**:
1. `USE_RAILWAY_DOCUMENTS=true` is set
2. Migrations are applied (`document` and `document_chunk` tables exist)
3. `pg_trgm` extension is enabled
4. Check logs for Library Tool errors

---

## ✅ Success Criteria

Deployment is successful when:

1. ✅ **Environment variables set**: All required vars are configured
2. ✅ **pg_trgm enabled**: Extension exists in PostgreSQL
3. ✅ **Migrations applied**: `alembic current` shows `add_document_tables_railway`
4. ✅ **Tables exist**: `document` and `document_chunk` tables present
5. ✅ **App starts**: No import errors in logs
6. ✅ **Health endpoint**: `/health` returns 200
7. ✅ **Ready endpoint**: `/ready` shows database connected (may show warnings, but should work)
8. ✅ **Library Tool works**: Can upload documents and search

---

## 📋 Quick Verification Script

Run this after deployment:

```bash
# 1. Check environment variables
railway variables | grep -E "DATABASE_URL|SECRET_KEY|USE_RAILWAY_DOCUMENTS|ANTHROPIC_API_KEY"

# 2. Check migration status
railway run alembic current

# 3. Check pg_trgm extension
railway connect postgres -c "SELECT * FROM pg_extension WHERE extname = 'pg_trgm';"

# 4. Check tables exist
railway connect postgres -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('document', 'document_chunk', 'document');"

# 5. Test endpoints
curl https://collab.up.railway.app/health
curl https://collab.up.railway.app/ready
```

---

## 🎯 Next Steps After Verification

1. **Set all environment variables** in Railway dashboard
2. **Enable pg_trgm** extension if not already enabled
3. **Monitor deployment logs** for migration completion
4. **Test Library Tool** functionality
5. **Monitor `/ready` endpoint** for real status (not `/health`)

---

**Remember**: Use `/ready` endpoint to see real app status. `/health` endpoint is wrapped and may mask errors.

