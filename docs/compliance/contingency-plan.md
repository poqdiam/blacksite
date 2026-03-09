# System Contingency Plan

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09
**Reference:** NIST SP 800-34r1 (Contingency Planning Guide for Federal Information Systems)

---

## 1. System Description

**System Name:** BLACKSITE GRC Platform
**System Type:** Web application (FastAPI/SQLite, Python venv, systemd-managed)
**Production Host:** borisov (192.168.86.102), Ubuntu 20.04 LTS FIPS
**Service:** `blacksite.service` (systemd unit), port 8100, proxied via Caddy
**Data Store:** SQLite database at `/home/graycat/projects/blacksite/data/blacksite.db` (encrypted via pysqlcipher3)
**Code Path:** `/home/graycat/projects/blacksite/`
**Operator:** Solo developer / small team

**System Purpose:** BLACKSITE provides RMF/NIST compliance management capabilities to federal, state, local, tribal, and commercial customers. It hosts System Security Plans (SSPs), assessment records, POA&M data, and compliance workflow tooling.

**Criticality:** High — customers rely on BLACKSITE for active ATO package management. Extended outages may delay compliance decisions or prevent access to security documentation.

---

## 2. Business Impact Analysis (BIA)

### Recovery Objectives

| Objective | Target | Rationale |
|-----------|--------|-----------|
| **Recovery Time Objective (RTO)** | 4 hours | Customers access the platform for time-sensitive compliance work; a 4-hour window is acceptable for unplanned outages |
| **Recovery Point Objective (RPO)** | 24 hours | Nightly backups cover a 24-hour data loss window; most compliance data changes infrequently |

### Impact by Outage Duration

| Duration | Impact |
|----------|--------|
| < 1 hour | Minimal; users may retry or work offline |
| 1–4 hours | Moderate; may delay active assessment or SSP editing sessions |
| 4–24 hours | Significant; customers may escalate; RTO threshold breached |
| > 24 hours | Severe; potential data loss exceeds RPO; customer notification required |
| > 72 hours | Critical; may trigger contractual SLA breach for enterprise customers |

### Maximum Tolerable Downtime (MTD)

**72 hours.** Beyond this point, customers are expected to seek alternative tooling or escalate formally. This is a soft MTD given the solo-operator context.

---

## 3. Backup Procedures

### Current Backup Configuration

**Script:** `/home/graycat/scripts/backup-all.sh`
**Schedule:** Daily at 03:00 (systemd timer: `backup-all.timer`)
**Destination:** `iapetus` NAS (192.168.86.213) via rclone SMB at `clawd/backups/borisov/`
**Sync tool:** rclone / rsync over SSH
**Test frequency:** Monthly restore verification (see Section 8)

### What Is Backed Up

| Data | Path | Included |
|------|------|----------|
| BLACKSITE database | `/home/graycat/projects/blacksite/data/blacksite.db` | Yes |
| Application code | `/home/graycat/projects/blacksite/` | Yes (via sync-projects.sh) |
| Service unit file | `/etc/systemd/system/blacksite.service` | Manually document changes |
| Python venv | `/home/graycat/projects/blacksite/.venv/` | No — rebuild from requirements.txt |
| Logs | `/tmp/blacksite.log` | No — ephemeral |

### Backup Integrity Verification

After each backup, confirm the destination file size is non-zero and the DB file can be opened:

```bash
# On iapetus (via SSH) or after restore:
sqlite3 /path/to/restored/blacksite.db "PRAGMA integrity_check;"
# Expected output: ok
```

---

## 4. Recovery Team Roles

| Role | Responsibility | Default Person |
|------|---------------|----------------|
| **Recovery Coordinator** | Activates this plan; makes go/no-go decisions | Platform Administrator |
| **Technical Recovery Lead** | Executes restore and restart procedures | Platform Administrator |
| **Customer Liaison** | Notifies customers of outage and estimated recovery time | Platform Administrator |

---

## 5. Activation Criteria

This plan is activated when any of the following conditions are met:

1. The BLACKSITE service is unavailable for > 15 minutes and cannot be restored by a simple `systemctl restart`
2. The production database is corrupt, missing, or encrypted by ransomware
3. The production host (`borisov`) is unavailable, inaccessible, or compromised
4. A security incident (per the Incident Response Runbook) requires a full system restore
5. Hardware failure on `borisov` prevents normal service operation

### Activation Decision Tree

```
Is blacksite.service running?
  NO → systemctl start blacksite → health check passes?
         YES → Done (minor outage, no activation needed)
         NO → Is it a DB error?
               YES → Go to Section 6.2 (DB Restore)
               NO → Go to Section 6.3 (Full Recovery)
  YES → Is the app returning errors?
         YES → Check logs → Is data corrupt?
               YES → Go to Section 6.2 (DB Restore)
               NO → Go to Section 6.1 (Service Restart)
         NO → False alarm — no activation needed
```

---

## 6. Recovery Procedures

### 6.1 Service Restart (No Data Loss)

Use when: the process crashed, OOM kill, or failed after a config change.

```bash
# Check service status
sudo systemctl status blacksite

# Review recent logs
journalctl -u blacksite -n 50

# Restart
sudo systemctl restart blacksite

# Verify
curl -s http://127.0.0.1:8100/health
```

Expected response: `{"status": "ok"}` or equivalent JSON indicating healthy state.

---

### 6.2 Database Restore

Use when: DB is corrupt, missing, accidentally deleted, or suspected tampered.

**Step 1: Stop the service**
```bash
sudo systemctl stop blacksite
```

**Step 2: Preserve the current (corrupt) DB for forensics**
```bash
mv /home/graycat/projects/blacksite/data/blacksite.db \
   /home/graycat/projects/blacksite/data/blacksite.db.corrupt.$(date +%Y%m%d%H%M%S)
```

**Step 3: Retrieve latest backup from iapetus**
```bash
# Mount or copy from iapetus NAS
scp -P 20234 iapetus:'clawd/backups/borisov/blacksite/data/blacksite.db' \
    /home/graycat/projects/blacksite/data/blacksite.db

# OR if rclone FUSE is mounted:
cp /home/graycat/shares/clawd/backups/borisov/blacksite/data/blacksite.db \
   /home/graycat/projects/blacksite/data/blacksite.db
```

**Step 4: Verify integrity**
```bash
# Must pass integrity check before starting service
# (DB is encrypted; use the encryption key from the service unit)
# If using plain sqlite3 for check, run integrity_check via the app's own DB access
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/graycat/projects/blacksite/data/blacksite.db')
result = conn.execute('PRAGMA integrity_check').fetchone()
print(result)
conn.close()
"
# Expected: ('ok',)
```

**Step 5: Restart and validate**
```bash
sudo systemctl start blacksite
curl -s http://127.0.0.1:8100/health
```

**Step 6: Check audit log continuity**

Log into the platform and confirm the most recent audit log entries match expectations. Note the data loss window (time of last backup → time of incident) in the incident record.

---

### 6.3 Full Recovery to Alternate Host

Use when: `borisov` is unavailable, destroyed, or under active compromise.

**Alternate site:** Any Linux host (physical or VM) with:
- Python 3.10+ available
- Docker (optional) or direct Python venv support
- 10 GB+ free disk space
- Network access to iapetus NAS or backup storage

**Step 1: Provision the alternate host**

The alternate host needs:
- User account with sudo access
- Python 3.11 (`apt install python3.11 python3.11-venv python3-pip`)
- SQLCipher library (`apt install sqlcipher libsqlcipher-dev`)
- Caddy or nginx for reverse proxy (optional for immediate recovery; direct port access acceptable during recovery)

**Step 2: Retrieve code and data from backup**

```bash
# SSH to iapetus and copy project files
rsync -av -e "ssh -p 20234" \
  graycat@iapetus.local:'clawd/projects/blacksite/' \
  /opt/blacksite/

# Copy database
scp -P 20234 graycat@iapetus.local:'clawd/backups/borisov/blacksite/data/blacksite.db' \
    /opt/blacksite/data/blacksite.db
```

**Step 3: Rebuild Python venv**

```bash
cd /opt/blacksite
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Step 4: Configure service environment**

Create a local run script or systemd unit with the required environment variables (DB encryption key, SECRET_KEY, GROQ_API_KEY). Retrieve these from the secure credential store (SOPS-encrypted `.secrets.env` on borisov, or a printed emergency credential sheet stored offline).

**Step 5: Start the service**

```bash
# Direct start for immediate recovery:
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8100 &

# Or install and start systemd unit from the backed-up unit file
```

**Step 6: Verify and communicate**

Run health check, complete smoke test (login, view systems, AI assistant). Notify customers of the alternate access URL if the primary hostname is unavailable. Update DNS if needed.

---

## 7. Health Check Verification Checklist

After any recovery action, confirm all of the following before declaring recovery complete:

- [ ] `curl http://127.0.0.1:8100/health` returns 200 OK
- [ ] Application login succeeds with a test account
- [ ] At least one system record is accessible
- [ ] Audit log records new login event post-recovery
- [ ] AI assistant endpoint responds (or note if Groq API is unavailable separately)
- [ ] Caddy proxies traffic correctly (check via public hostname)
- [ ] No error storm in `journalctl -u blacksite -f`
- [ ] Backup job still scheduled (`systemctl status backup-all.timer`)

---

## 8. Test Schedule

| Test Type | Frequency | Scope | Owner |
|-----------|-----------|-------|-------|
| **Tabletop exercise** | Annually (each March) | Walk through a simulated P1 incident using this plan | Platform Administrator |
| **Full restore test** | Semi-annually (March and September) | Restore DB from backup to a test environment; verify integrity and service startup | Platform Administrator |
| **Backup verification** | Monthly | Confirm backup files are present, non-zero, and pass integrity check | Platform Administrator (automated or manual spot check) |

**Test results** should be documented in `/home/graycat/docs/contingency-tests/YYYY-MM-DD-test.md` and any gaps fed back into this plan.

**Next scheduled tests:**
- Tabletop: 2026-03-09 (due this month)
- Full restore: 2026-03-15 (target)
- Backup spot check: 2026-04-01

---

## 9. Plan Maintenance

This document is reviewed annually or following any of these trigger events:

- A real activation of the contingency plan
- A major change to the platform architecture, hosting, or backup strategy
- Change in recovery objectives driven by customer contracts
- Findings from a test exercise

---

## 10. References

- NIST SP 800-34r1: Contingency Planning Guide for Federal Information Systems
- NIST SP 800-53 CP controls (CP-1 through CP-13)
- This platform's Incident Response Runbook (incident-response-runbook.md)
- Backup script: `/home/graycat/scripts/backup-all.sh`
- Systemd timer: `backup-all.timer`
