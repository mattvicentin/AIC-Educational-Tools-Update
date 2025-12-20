# Enhanced Remote Rollout Plan - Library Tool

## Overview

This plan deploys the Library Tool with synthesis guardrails to production (Railway/DigitalOcean).

## Pre-Deploy Checklist (Local)

### 1. Code Preparation
- [ ] **Branch/Commit**: Ensure you're on `feature/railway-deployment` branch with all changes committed
- [ ] **Baseline**: Baseline hash was `2b9d51f7e8781be6b0192a16823cb08ecdf0daca`; verify you're beyond this
- [ ] **Commit Message**: Use clear message: `feat: add Library Tool with synthesis guardrails`

### 2. Dependencies Verification
- [ ] **Requirements Files**: Confirm both `requirements.txt` and `requirements_railway.txt` include:
  - `pypdf>=4.0.0`
  - `python-docx==1.1.2`
- [ ] **Local Install**: Verify dependencies install cleanly: `pip install -r requirements_railway.txt`

### 3. Migration Verification (CRITICAL)
- [ ] **Check Migration Chain**: Verify both migrations exist:
  - `f6g7h8i9j0k1_add_card_comment_table.py` (parent)
  - `20241106120000_add_document_tables_railway.py` (Library Tool)
- [ ] **Local Migration Test**: Run against local PostgreSQL:
  ```bash
  alembic current  # Check current state
  alembic upgrade head  # Apply both migrations
  ```
- [ ] **Verify Tables**: Confirm `document` and `document_chunk` tables exist
- [ ] **Verify pg_trgm**: Confirm extension is available (should be default on PostgreSQL)

### 4. Feature Flags (Local Testing)
- [ ] **Set Flags**: In `.env`:
  - `USE_RAILWAY_DOCUMENTS=true`
  - `ENABLE_RAILWAY_FALLBACK=false` (Railway-only)
- [ ] **API Keys**: Ensure `ANTHROPIC_API_KEY` is set for AI calls

### 5. Smoke Tests (Local)
- [ ] **Upload Test**: Upload a small PDF/DOCX/TXT document
- [ ] **Chunk Verification**: Confirm chunks are created in database
- [ ] **Normal Search**: Ask a question, verify top-3 ranked chunks are used
- [ ] **Synthesis Test**: Upload 6+ documents, ask "summarize all sources"
  - Verify: Max 5 docs processed, max 10 chunks returned
  - Verify: Chunks truncated to 400 chars
  - Verify: Token budget fallback works if exceeded
- [ ] **Feature Flag Test**: Set `USE_RAILWAY_DOCUMENTS=false`, verify graceful degradation

### 6. Server Migration State Check (CRITICAL - NEW)
- [ ] **Check Server Migration State**: Before deploying code, verify server's current migration:
  ```bash
  # Via Railway CLI or SSH
  railway run alembic current
  # OR
  railway connect postgres
  # Then: SELECT * FROM alembic_version;
  ```
- [ ] **Expected States**:
  - ✅ `f6g7h8i9j0k1` or later: Safe to deploy
  - ⚠️ `e5f6g7h8i9j0` or earlier: Must run `f6g7h8i9j0k1` migration first
- [ ] **If Migration Gap Exists**: Run parent migration first:
  ```bash
  railway run alembic upgrade f6g7h8i9j0k1
  ```

## Server-Side Deployment Plan

### 1. Database Backup (CRITICAL - NEW)
- [ ] **Backup Database**: Before any migrations, backup production database:
  ```bash
  # Via Railway CLI or pg_dump
  railway connect postgres
  pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- [ ] **Verify Backup**: Confirm backup file exists and is valid

### 2. Code Deployment
- [ ] **Push Branch**: Push `feature/railway-deployment` branch to GitHub
- [ ] **Deploy**: Trigger deployment on Railway/DigitalOcean
- [ ] **Monitor Build**: Watch build logs for:
  - ✅ Dependencies installing (`pypdf`, `python-docx`)
  - ✅ Build completing successfully
  - ⚠️ Any errors or warnings

### 3. Environment Variables (Server)
- [ ] **Set Flags**: In Railway/DigitalOcean dashboard:
  - `USE_RAILWAY_DOCUMENTS=true` (REQUIRED for Library Tool)
  - `ENABLE_RAILWAY_FALLBACK=false` (Railway-only mode)
- [ ] **Verify Database**: Confirm `DATABASE_URL` points to PostgreSQL with `pg_trgm` available
- [ ] **API Keys**: Verify `ANTHROPIC_API_KEY` is set (unchanged)

### 4. Migration Execution (CRITICAL)
**Note**: Railway runs migrations automatically via `src/main.py` on startup, but verify manually:

- [ ] **Option A - Automatic (Recommended)**:
  - Deploy code (migrations run automatically on startup)
  - Check logs for: `✅ Alembic migrations complete.`
  - Verify migration status: `railway run alembic current`
  - Expected: `add_document_tables_railway` or later

- [ ] **Option B - Manual (If Automatic Fails)**:
  ```bash
  railway run alembic upgrade head
  ```
  - Verify success: `railway run alembic current`
  - Check for errors in logs

- [ ] **Verify Tables**: Confirm tables exist:
  ```bash
  railway connect postgres
  # Then:
  \dt document
  \dt document_chunk
  \dx pg_trgm  # Verify extension
  ```

### 5. Application Restart
- [ ] **Restart App**: Railway restarts automatically on deploy
- [ ] **Verify Health**: Check `/health` endpoint returns 200 OK
- [ ] **Check Logs**: Verify no migration errors in startup logs

## Post-Deploy Verification (Server)

### 1. Health Checks
- [ ] **Health Endpoint**: `GET /health` returns 200 OK
- [ ] **Ready Endpoint**: `GET /ready` returns 200 OK (if exists)
- [ ] **Logs**: Check for startup errors or warnings

### 2. Library Tool Functionality
- [ ] **Upload Test**: Upload a small document (PDF/DOCX/TXT)
- [ ] **Storage Display**: Verify storage indicator shows correct percentage
- [ ] **Document List**: Verify uploaded document appears in list
- [ ] **Normal Query**: Ask a question about the document
  - Verify: AI uses top-3 ranked chunks
  - Verify: Document context is included in response

### 3. Synthesis Mode Testing
- [ ] **Multiple Documents**: Upload 6+ documents
- [ ] **Synthesis Query**: Ask "summarize all sources"
- [ ] **Verify Caps**:
  - Max 5 documents processed (most recent)
  - Max 10 chunks returned
  - Chunks truncated to 400 chars
- [ ] **Check Logs**: Verify synthesis mode detected and caps applied
- [ ] **Token Budget**: If many large chunks, verify fallback to summaries

### 4. Feature Flag Testing
- [ ] **Disable Flag**: Set `USE_RAILWAY_DOCUMENTS=false`
- [ ] **Restart**: Restart application
- [ ] **Synthesis Request**: Ask "summarize all sources"
- [ ] **Verify**: AI informs user that Library Tool is disabled
- [ ] **Re-enable**: Set `USE_RAILWAY_DOCUMENTS=true` and restart

### 5. Error Monitoring
- [ ] **Check Logs**: Look for:
  - Migration warnings/errors
  - Library Tool warnings (feature flag, token budget)
  - API errors (Anthropic)
- [ ] **Error Rate**: Monitor error rate for 24 hours post-deploy

## Rollback Plan (If Deployment Fails)

### Immediate Rollback
1. **Revert Code**: Revert to previous commit or branch
2. **Disable Feature**: Set `USE_RAILWAY_DOCUMENTS=false` in environment
3. **Restart**: Restart application
4. **Verify**: Confirm app works without Library Tool

### Database Rollback (If Migration Fails)
1. **Stop App**: Stop application to prevent further issues
2. **Restore Backup**: Restore database from backup created in Step 1
3. **Verify**: Confirm database is restored correctly
4. **Revert Code**: Revert to previous commit
5. **Restart**: Restart application

### Partial Rollback (Feature Flag)
- **Keep Code**: Leave new code deployed
- **Disable Feature**: Set `USE_RAILWAY_DOCUMENTS=false`
- **Restart**: Restart application
- **Investigate**: Fix issues, then re-enable feature flag

## Monitoring & Alerts

### First 24 Hours
- [ ] **Error Rate**: Monitor error rate (should be < 1%)
- [ ] **API Costs**: Monitor Anthropic API usage (synthesis mode uses more tokens)
- [ ] **Database Performance**: Monitor query performance (FTS searches)
- [ ] **Storage Usage**: Monitor document storage growth

### First Week
- [ ] **User Feedback**: Collect user feedback on Library Tool
- [ ] **Performance**: Monitor synthesis mode performance
- [ ] **Token Budget**: Adjust `SYNTHESIS_TOKEN_BUDGET` if needed
- [ ] **Caps**: Adjust `SYNTHESIS_MAX_DOCUMENTS` or `SYNTHESIS_MAX_TOTAL_CHUNKS` if needed

## Success Criteria

✅ **Deployment Successful If**:
- Health checks pass
- Migrations applied successfully
- Library Tool upload/search works
- Synthesis mode works with caps
- Feature flag graceful degradation works
- No increase in error rate
- User feedback is positive

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration dependency missing | High | Verify server migration state before deploy |
| Migration fails silently | Medium | Check logs explicitly, verify tables exist |
| Token budget exceeded | Low | Fallback to summaries implemented |
| Feature flag disabled | Low | Graceful degradation with user message |
| Database backup missing | High | Always backup before migrations |
| pg_trgm unavailable | Medium | Railway PostgreSQL should have it by default |

## Additional Notes

- **Automatic Migrations**: Railway runs migrations automatically via `src/main.py` on startup
- **Zero-Downtime**: Railway handles zero-downtime deployments automatically
- **Monitoring**: Use Railway dashboard for logs and metrics
- **Support**: Have database backup ready for quick rollback if needed

