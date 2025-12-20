# Health Check Endpoints

## Overview
The application provides two health check endpoints following Kubernetes best practices:
- `/health` - Liveness probe (is the process alive?)
- `/ready` - Readiness probe (is the app ready to serve traffic?)

---

## `/health` - Liveness Probe

**Purpose:** Determine if the process is running and should be restarted.

**Returns:**
- **Always 200** if the process is alive
- Does NOT check database connectivity
- Use for process health monitoring

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2025-11-27T13:45:00.123456"
}
```

**Railway Config:**
```toml
healthcheckPath = "/health"
healthcheckTimeout = 60
```

**Use Case:** Railway uses this to determine if the container should be restarted. If it returns non-200 or times out, Railway restarts the service.

---

## `/ready` - Readiness Probe

**Purpose:** Determine if the app can serve traffic (database connected, migrations applied).

**Returns:**
- **200** when fully ready (DB connected, migrations applied)
- **503** when not ready (DB down, migration errors, init failures)

**Response (Healthy):**
```json
{
  "status": "ready",
  "checks": {
    "database": {
      "status": "connected",
      "latency_ms": 45
    },
    "migrations": {
      "status": "applied"
    }
  },
  "timestamp": "2025-11-27T13:45:00.123456",
  "version": "3.1.0"
}
```

**Response (Unhealthy - DB Password Wrong):**
```json
{
  "status": "not_ready",
  "checks": {
    "database": {
      "status": "error",
      "message": "password authentication failed for user \"postgres\""
    },
    "db_init": {
      "status": "error",
      "message": "connection to server failed"
    }
  },
  "timestamp": "2025-11-27T13:45:00.123456",
  "version": "3.1.0"
}
```
**HTTP Status:** `503 Service Unavailable`

**Use Case:** 
- Load balancers can check `/ready` to determine routing
- Monitoring systems can check this for service health
- Debugging: See exactly what's wrong (DB password, migrations, etc.)

---

## Benefits of This Pattern

### **Before (Old /health):**
```
Password wrong → App crashes on startup
                → Railway restarts
                → Crash loop
                → No diagnostics
```

### **After (New /health + /ready):**
```
Password wrong → App starts anyway ✅
                → /health returns 200 (process alive) ✅
                → /ready returns 503 with error details ✅
                → Clear diagnostics in logs ✅
                → No crash loop ✅
```

---

## Implementation Details

### **Graceful Startup:**
1. `db.create_all()` wrapped in try/except
2. Migrations wrapped in try/except
3. Errors stored in `app.config` for reporting
4. App continues to start even with DB errors

### **Health Checks:**
1. `/health` - Simple, always 200 (liveness)
2. `/ready` - Checks DB, reports errors (readiness)
3. 2-second timeout on DB check (fail fast)
4. Error messages truncated to 200 chars

### **Error Reporting:**
- Startup errors stored in `app.config["DB_INIT_ERROR"]`
- Migration errors in `app.config["MIGRATION_ERROR"]`
- `/ready` endpoint reports all errors with clear messages
- Logs show detailed errors for debugging

---

## Testing

### **Simulate DB Password Failure:**
1. Set wrong password in Railway `DATABASE_URL`
2. Deploy the app
3. **Expected:** App starts successfully
4. **Check `/health`:** Returns 200 (process is alive)
5. **Check `/ready`:** Returns 503 with "password authentication failed"
6. **Fix password** in Railway variables
7. **Next request to `/ready`:** Returns 200 (healthy)

### **Normal Operation:**
- `/health` → 200 (always, if process is up)
- `/ready` → 200 (only when DB is connected and migrations applied)

---

## Monitoring Setup

**For Railway:**
- Keep `healthcheckPath = "/health"` (liveness)
- Optionally monitor `/ready` for service health alerts

**For Load Balancers:**
- Use `/ready` for routing decisions
- Only send traffic when `/ready` returns 200

**For Monitoring Systems:**
- Poll `/ready` for service health
- Alert when returns 503
- Error message tells you exactly what's wrong

---

**Date:** November 27, 2025  
**Version:** 3.1.0  
**Pattern:** Kubernetes liveness/readiness best practice

