# Change Management Process

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09

---

## 1. Purpose and Scope

This document defines the process for managing changes to the BLACKSITE production environment. Controlled change management reduces the risk of unintended outages, data loss, and security regressions.

**In scope — all changes to:**
- Application source code (Python, HTML/CSS/JS, templates)
- Application configuration (environment variables, systemd service unit, Caddy proxy configuration)
- Database schema (migrations, new tables, column changes)
- Infrastructure (host OS packages, Python dependencies, Docker if applicable)
- Security controls (authentication logic, RBAC rules, audit logging)
- Third-party integrations (new API endpoints, changed API keys, updated libraries)

**Out of scope:**
- Content changes made by end users within the platform (SSP edits, assessment records) — these are normal platform operations
- Read-only configuration inspection or log review with no system changes

---

## 2. Change Categories

### Standard Change
**Definition:** Low-risk, routine change with a well-understood procedure and pre-approved implementation path.

**Examples:**
- Python dependency patch update (non-breaking, security fix)
- Log level or log rotation configuration adjustment
- Static asset update (CSS, images, front-end only)
- Cosmetic UI text change

**Process:** No formal review required. Implement and document in CHANGELOG.md. If the change touches anything touching authentication or the DB schema, escalate to Normal.

---

### Normal Change
**Definition:** Any change that modifies core application logic, database schema, security controls, authentication flows, or external integrations.

**Examples:**
- New feature or API endpoint
- Database schema migration
- Changes to authentication or session handling
- New or updated third-party library (minor or major version)
- Environment variable changes
- Firewall or proxy rule changes

**Process:** Follow the full change request process (Section 4). Test before deploying. Document in CHANGELOG.md.

---

### Emergency Change
**Definition:** A change that must be deployed immediately to restore service, remediate a security vulnerability, or address an active incident. Normal review timelines are compressed.

**Examples:**
- Active security incident requiring an immediate patch or credential rotation
- Catastrophic bug causing data loss or platform unavailability
- Critical CVE in a dependency being actively exploited

**Process:** Implement immediately with minimum viable testing. Document retroactively within 48 hours. Conduct post-implementation review within 48 hours. Reference the incident record (from Incident Response Runbook).

---

## 3. Roles

| Role | Responsibility |
|------|---------------|
| **Change Initiator** | Identifies and proposes the change; responsible for testing and documentation |
| **Change Approver** | Reviews and approves Normal changes before production deployment (same person as Initiator in solo-operator context — use the checklist as a forcing function) |
| **Change Implementer** | Executes the deployment to production |

> **Solo operator note:** All three roles are typically the same person. The value of this process is the checklist discipline — not the formal sign-off. Use the pre-deployment checklist (Section 5) as a mandatory self-review gate.

---

## 4. Change Request Process (Normal Changes)

### Step 1: Document the Change

Before touching production, create a brief change record. For small teams, a dated entry in `/home/graycat/docs/changes/YYYY-MM-DD-change-name.md` is sufficient:

```markdown
## Change: [Brief Name]
Date: YYYY-MM-DD
Type: Normal
Initiator: [Name]

### Description
What is changing and why.

### Risk Assessment
- Risk level: Low / Medium / High
- What could go wrong?
- How would you know if it went wrong?
- What is the blast radius if it fails?

### Rollback Plan
How to undo this change if it causes problems.

### Testing Plan
What tests will be run before and after deployment.
```

### Step 2: Assess Risk

Consider:
- Does this change touch authentication, session management, or RBAC? → **High risk**
- Does this change alter the DB schema? → **Medium-High risk** (schema changes are hard to roll back)
- Does this change affect audit logging? → **High risk** (audit gaps are a compliance finding)
- Is this a third-party dependency with known CVEs in the new version? → Research first
- Could this change affect customer data directly? → Notify affected customers before deploying

### Step 3: Test in Dev/Staging

All Normal changes must be tested in a non-production environment before deploying to production.

Minimum dev testing:
- Application starts without errors
- Authentication flow works (login, logout, session expiry)
- The specific changed functionality works as designed
- No regression in adjacent functionality
- DB integrity check passes if schema was touched

**Dev instance:** Run a local instance of BLACKSITE against a copy of the production DB (or a sanitized subset):
```bash
# In the project directory, with a test DB copy:
DB_PATH=./data/test.db SECRET_KEY=test GROQ_API_KEY=test \
  .venv/bin/uvicorn server:app --host 127.0.0.1 --port 8101 --reload
```

### Step 4: Document Rollback Plan

Before deploying, confirm the rollback path:
- For code changes: `git revert` or `git checkout [previous commit]` + service restart
- For DB schema changes: migration rollback script or restore from backup (note: data entered after migration may be lost)
- For dependency changes: `pip install [package]==[previous version]` + service restart
- For config changes: revert the service unit edit + `systemctl daemon-reload` + restart

If there is no clean rollback path, escalate the risk assessment and consider whether to proceed.

### Step 5: Communicate Planned Downtime

If the deployment will cause service interruption > 5 minutes, notify affected users in advance:
- Minimum notice: 24 hours for planned maintenance
- Communication channel: email or in-platform notification
- Include: expected start time, expected duration, what is changing, contact for questions

---

## 5. Pre-Deployment Checklist

Run through this checklist before every production deployment of a Normal change:

- [ ] Change is documented (description, risk, rollback plan)
- [ ] Change tested in dev environment
- [ ] Health check passed in dev (`curl http://127.0.0.1:810x/health`)
- [ ] Authentication flow tested in dev (login, logout, session)
- [ ] DB integrity check passed (if schema changed)
- [ ] Rollback procedure identified and feasible
- [ ] Affected customers notified of downtime (if > 5 minutes)
- [ ] Current production DB backed up within past 24 hours (verify: `ls -lh ~/shares/clawd/backups/borisov/blacksite/`)
- [ ] Deployment time is during low-traffic window (avoid peak business hours)

---

## 6. Deployment Procedure

### Standard Deployment

```bash
# 1. Pull latest code to production host
cd /home/graycat/projects/blacksite
git pull origin main   # or copy files from dev

# 2. Install any new dependencies
.venv/bin/pip install -r requirements.txt

# 3. Apply DB migrations (if any)
# Run migration script or manual SQL — document what was run

# 4. Restart the service
sudo systemctl restart blacksite

# 5. Health check
curl -s http://127.0.0.1:8100/health

# 6. Smoke test (within 2 minutes of restart)
# - Login works
# - Key features load without errors
# - Audit log shows new activity
# - No error storm in logs
journalctl -u blacksite -f &   # watch logs for 2 minutes
```

### Post-Deployment Verification

Within 15 minutes of deployment:
- [ ] Health endpoint returns 200
- [ ] Login flow works
- [ ] Target changed functionality works as expected
- [ ] No unexpected errors in `journalctl -u blacksite`
- [ ] Audit log has a post-deployment entry

---

## 7. Rollback Procedure

If post-deployment verification fails:

### Code Rollback
```bash
cd /home/graycat/projects/blacksite
git log --oneline -5   # find the previous commit
git checkout [previous-commit-hash] -- .  # or git revert HEAD
.venv/bin/pip install -r requirements.txt   # in case deps changed
sudo systemctl restart blacksite
curl -s http://127.0.0.1:8100/health
```

### Database Rollback (if schema change caused failure)
```bash
sudo systemctl stop blacksite
cp /home/graycat/projects/blacksite/data/blacksite.db.pre-migration-* \
   /home/graycat/projects/blacksite/data/blacksite.db
sudo systemctl start blacksite
```

> Note: Data entered after the migration point will be lost. Document the data loss window and assess whether any customers need to be notified.

### Dependency Rollback
```bash
.venv/bin/pip install [package]==[previous-version]
sudo systemctl restart blacksite
```

---

## 8. Emergency Change Process

When a change must be deployed immediately without full pre-deployment review:

1. Implement the minimum change required to address the emergency
2. Run health check and minimal smoke test immediately after
3. Within **48 hours**, complete the following retrospective:
   - Document the change in the change log
   - Document what testing was skipped and why
   - Identify any risks introduced by skipping full testing
   - Schedule follow-up testing or remediation if needed
   - Cross-reference the incident record (if triggered by a security incident)

Emergency changes still require a rollback plan — even if that plan is "restore from last backup."

---

## 9. Change Log

All changes to production must be recorded in `CHANGELOG.md` in the project root. Maintain entries in reverse-chronological order.

**Format:**
```markdown
## [YYYY-MM-DD] — Brief change name

**Type:** Standard / Normal / Emergency
**Deployed by:** [Name]
**Related incident:** [Incident ID or N/A]

### Changes
- Brief description of what was changed

### Testing
- Tests run and results

### Rollback
- How to revert if needed
```

The CHANGELOG.md is a first-class compliance artifact. It provides evidence of controlled change management for audits and ATO reviews.

---

## 10. Database Schema Change Guidance

DB schema changes carry extra risk because migrations can be difficult to roll back cleanly.

**Before any schema change:**
1. Take a manual DB backup immediately before applying the migration
2. Test the migration on a copy of production data in dev
3. Verify that the application works against the migrated schema before pointing production at it
4. Write a corresponding rollback SQL script before executing the forward migration

**Migration naming convention:**
- Keep migration scripts in `/home/graycat/projects/blacksite/migrations/`
- Name format: `YYYYMMDD_description.sql`
- Each migration file should include the rollback SQL in a comment block at the bottom

---

## 11. References

- NIST SP 800-53 Rev 5: CM-3 (Configuration Change Control), CM-4 (Impact Analyses), CM-5 (Access Restrictions for Change)
- This platform's Contingency Plan (contingency-plan.md)
- This platform's Incident Response Runbook (incident-response-runbook.md)
- Project CHANGELOG.md
