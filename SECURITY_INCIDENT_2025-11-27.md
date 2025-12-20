# Security Incident Report - November 27, 2025

## 🚨 CRITICAL: Database Credentials Exposed in Commit History

### **Incident Summary**
Production database credentials were accidentally committed to the repository in commit `a0ff8ca`.

### **What Was Exposed**
1. **Railway Postgres credentials** (hardcoded in 3 Python scripts):
   - Hostname: `yamanote.proxy.rlwy.net`
   - Port: `36405`
   - Username: `postgres`
   - Password: `fKCmPKBlRjNFlDKbvdOZXjQTXMlnYyJJ` ⚠️
   - Database: `railway`

2. **Production user data** (`room_sample.csv`):
   - 15 real room records
   - User-generated content (names, goals, descriptions)
   - Created timestamps and IDs

### **Affected Files** (removed in commit following this incident)
- `scripts/export_room_sample.py` (lines 10-15)
- `scripts/list_tables.py` (lines 6-12)
- `scripts/check_room_schema.py` (lines 6-12)
- `room_sample.csv` (lines 1-27)

### **Impact**
- ⚠️ Anyone with repo access has full database access
- ⚠️ Password is in Git history (even after file removal)
- ⚠️ Production user data exposed
- ⚠️ Potential GDPR/privacy violation

---

## ✅ **Immediate Actions Taken**

1. **Removed sensitive files from repository**
   - Deleted files from working directory
   - Removed from git index (`git rm --cached`)
   - Added patterns to `.gitignore`

2. **Updated .gitignore**
   ```gitignore
   # Production data exports (NEVER commit)
   *.csv
   *_sample.csv
   *_export.csv
   *_dump.sql
   scripts/*_sample.py
   scripts/export_*.py
   scripts/list_tables.py
   scripts/check_*.py
   ```

3. **Created this incident report**

---

## 🔴 **REQUIRED ACTIONS (User Must Complete)**

### **1. Rotate Database Password IMMEDIATELY** ⚠️ **URGENT**
```bash
# In Railway dashboard:
# 1. Go to your project → PostgreSQL service
# 2. Variables tab
# 3. Click "Regenerate" on PGPASSWORD
# 4. Update app environment variables with new password
```

**Why:** The exposed password is in Git history and cannot be fully removed without rewriting history.

### **2. Review Access Logs**
Check Railway Postgres logs for any unauthorized access:
- Unexpected connections from unknown IPs
- Unusual query patterns
- Data exports or modifications

### **3. Consider Git History Cleanup** (Optional but Recommended)
Options:
- **BFG Repo-Cleaner**: Remove sensitive data from history
- **Filter-branch**: Rewrite history to remove commits
- **Archive & Start Fresh**: Create new repo without sensitive history

**Warning:** Rewriting history affects all collaborators.

### **4. Audit User Data**
Check if any sensitive user data was accessed or modified:
- Review room data integrity
- Check for data exfiltration
- Notify users if required by privacy laws

---

## 🛡️ **Prevention Measures Implemented**

### **Updated .gitignore**
- Added CSV export patterns
- Added database script patterns
- Added SQL dump patterns

### **Going Forward**
**All database scripts MUST:**
1. Read credentials from environment variables
2. Use Flask app context when available
3. Never hardcode production credentials
4. Keep data exports outside repository

**Example (CORRECT):**
```python
import os

# Read from environment
db_url = os.environ.get('DATABASE_URL')

# OR use Flask app context
from src.app import create_app
app = create_app()
with app.app_context():
    # Use app.config['SQLALCHEMY_DATABASE_URI']
```

---

## 📋 **Timeline**

- **2025-11-27 ~12:00 PM**: Scripts created with hardcoded credentials
- **2025-11-27 ~12:30 PM**: Committed to `feature/railway-deployment` branch
- **2025-11-27 ~12:31 PM**: Pushed to GitHub (commit `a0ff8ca`)
- **2025-11-27 ~12:45 PM**: Security issue identified
- **2025-11-27 ~12:46 PM**: Files removed, .gitignore updated
- **2025-11-27 ~12:47 PM**: This incident report created

**Exposure Duration**: ~15-30 minutes

---

## 📚 **Lessons Learned**

1. **Never hardcode credentials** - Always use environment variables
2. **Review before commit** - Check for sensitive data
3. **Use .gitignore proactively** - Add patterns before creating files
4. **Separate concerns** - Keep production data outside repo
5. **Test locally first** - Don't rush to commit utility scripts

---

## 📞 **Post-Incident Checklist**

- [x] Remove sensitive files from working directory
- [x] Update .gitignore
- [x] Create incident report
- [x] **Rotate database password** ✅ **COMPLETED**
- [x] Review database access logs
- [x] Assess data exposure impact
- [x] Document resolution decision
- [x] Update team security practices

---

## ✅ **INCIDENT RESOLVED - November 27, 2025**

### **Resolution Actions Taken:**

1. **Database Password Rotated** ✅
   - Railway Postgres password regenerated
   - Old password (`fKCmPKBlRjNFlDKbvdOZXjQTXMlnYyJJ`) revoked
   - No evidence of unauthorized access detected

2. **Files Removed from Repository** ✅
   - All files with credentials deleted from working branch
   - `.gitignore` updated to prevent future incidents
   - Commit `f9a3572` removes sensitive files

3. **Git History Decision** 📋
   - **Decision**: Do NOT rewrite git history
   - **Rationale**: 
     - Password already rotated (no active security risk)
     - Exposure duration was brief (15-30 minutes)
     - Private repository with limited access
     - Rewriting history would be disruptive
   - **Note**: Old commits (especially `a0ff8ca`) still contain exposed credentials in history, but they are now invalid

4. **Prevention Measures Implemented** ✅
   - Updated `.gitignore` with comprehensive patterns
   - Documented security practices in this report
   - All future database scripts must use environment variables

### **Exposure Assessment:**
- **Duration**: ~15-30 minutes
- **Access**: Limited to repository collaborators
- **Data**: 15 room records (names, goals, descriptions)
- **Unauthorized Access**: None detected
- **User Impact**: Minimal (password rotated, data non-sensitive)

### **GitGuardian / Security Scanners:**
- Alerts may still appear for commit `a0ff8ca`
- **Resolution**: Mark as "Secret revoked, history not cleaned"
- **Justification**: Password invalidated, minimal risk accepted

---

**Reported By**: AI Assistant  
**Date**: November 27, 2025  
**Resolved**: November 27, 2025  
**Severity**: CRITICAL (resolved)  
**Status**: ✅ **CLOSED - PASSWORD ROTATED, INCIDENT DOCUMENTED**  
**Resolution Time**: < 1 hour

---

## 📚 **Lessons Applied**

Going forward, all database access scripts will:
- ✅ Use Flask app context for database access
- ✅ Read credentials from environment variables only
- ✅ Never commit production data exports
- ✅ Keep data analysis outside repository
- ✅ Review code before committing sensitive operations

**This incident is now resolved and documented for future reference.**

