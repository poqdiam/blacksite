# Data Retention and Disposal Policy

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09

---

## 1. Purpose and Scope

This policy defines how long BLACKSITE retains different categories of data, when and how data is disposed of, and the procedures for implementing retention enforcement. It applies to all data stored in the BLACKSITE SQLite database, application logs, backup copies, and any derived exports.

Retention periods are set to satisfy the longest applicable legal or regulatory requirement while avoiding indefinite accumulation of unnecessary personal or operational data.

---

## 2. Data Categories and Retention Periods

### 2.1 Retention Schedule

| Data Category | Retention Period | Basis | Disposal Method |
|--------------|-----------------|-------|----------------|
| **Immutable audit logs** | 3 years from event date | FISMA / NIST SP 800-53 AU-11 | SQLite DELETE + VACUUM; secure DB file deletion if DB retired |
| **User profiles (active accounts)** | Duration of account | Operational necessity | Soft-delete on offboarding; hard DELETE after +1 year |
| **User profiles (offboarded)** | 1 year post-offboarding | Dispute resolution, compliance trail | Hard DELETE + VACUUM at end of retention window |
| **Assessment data and SSP content** | 6 years from creation or last significant modification | Federal records guidance (36 CFR 1236); NIST SP 800-53 SI-12 | SQLite DELETE + VACUUM; secure disposal for DB files |
| **AI chat logs (server-side)** | 90 days | Operational need; privacy minimization | Automated purge via scheduled cleanup script |
| **Session data** | 30 days or logout (whichever is sooner) | Security hygiene | Automated expiry on read; scheduled purge of expired rows |
| **Demo visitor logs** | 90 days | Analytics utility period | Automated purge via scheduled cleanup script |
| **Exported documents (PDF/DOCX)** | Not stored server-side | N/A — generated on demand | Streamed to client; not retained |
| **Backup copies** | Same as source data; backups older than 1 year purged | Proportionality | Delete from NAS backup path; overwrite if media reuse |
| **Incident records** | 3 years from incident closure | Security operations records | Manual deletion after retention window |

### 2.2 Notes on Specific Categories

**Audit logs:** Audit log records in the `audit_log` table are treated as immutable for the 3-year retention window. During this window, records may not be deleted, altered, or overwritten except as part of a court-ordered legal hold modification. After the retention window, records are purged in bulk.

**SSP / assessment content:** Federal records retention guidance (36 CFR 1236) recommends retaining security assessment records for the life of the system plus additional years to support ATO renewal cycles. The 6-year target covers a typical 3-year ATO authorization cycle with a one-cycle lookback.

**User profiles:** When a user account is deactivated (offboarding), the record is soft-deleted (marked inactive, login disabled). The profile and associated metadata are retained for 1 year to support audit trail integrity and any post-offboarding investigations. After 1 year, the record is hard-deleted.

**AI chat logs:** AI queries and responses are logged locally for debugging and audit purposes. Given the privacy sensitivity of query content and the 90-day utility window, these are purged on a rolling basis.

**Session data:** Expired session rows accumulate in the session store. These are purged automatically on access (lazy expiry) and cleaned up in bulk by the scheduled maintenance script.

---

## 3. Automated Purge Procedures

### 3.1 Current State

The BLACKSITE platform does not yet have a fully automated retention enforcement script. The following guidance defines the required behavior for implementation.

### 3.2 Recommended Implementation

Create a script at `/home/graycat/scripts/blacksite-retention-purge.sh` (or as a Python script callable from cron/systemd) that performs the following operations:

```bash
#!/bin/bash
# blacksite-retention-purge.sh
# Run weekly via systemd timer or cron
# Requires: sqlite3, access to DB path, DB encryption key in env

DB_PATH="/home/graycat/projects/blacksite/data/blacksite.db"
LOG_FILE="/var/log/blacksite-retention-purge.log"

echo "[$(date -Iseconds)] Starting retention purge" >> "$LOG_FILE"

# Purge expired sessions (> 30 days old)
sqlite3 "$DB_PATH" "DELETE FROM sessions WHERE created_at < datetime('now', '-30 days');"

# Purge AI chat logs older than 90 days
# (Table name: adjust to match actual schema)
sqlite3 "$DB_PATH" "DELETE FROM ai_chat_logs WHERE created_at < datetime('now', '-90 days');"

# Purge demo visitor logs older than 90 days
sqlite3 "$DB_PATH" "DELETE FROM visitor_logs WHERE visited_at < datetime('now', '-90 days');"

# Purge audit logs older than 3 years (1095 days)
# IMPORTANT: Confirm no active legal hold before enabling this block
# sqlite3 "$DB_PATH" "DELETE FROM audit_log WHERE created_at < datetime('now', '-1095 days');"

# Reclaim space
sqlite3 "$DB_PATH" "VACUUM;"

echo "[$(date -Iseconds)] Retention purge complete" >> "$LOG_FILE"
```

> **Note:** The audit log purge block is commented out intentionally. Enable it only after confirming no legal hold is active and that the records have passed the 3-year window. Run manually or under separate scheduled job with an additional confirmation step.

### 3.3 Scheduling

Register as a weekly systemd timer:

```ini
# /etc/systemd/system/blacksite-retention.timer
[Unit]
Description=BLACKSITE data retention purge (weekly)

[Timer]
OnCalendar=Sun 02:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/blacksite-retention.service
[Unit]
Description=BLACKSITE data retention purge

[Service]
Type=oneshot
User=graycat
ExecStart=/home/graycat/scripts/blacksite-retention-purge.sh
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now blacksite-retention.timer
```

### 3.4 User Offboarding Hard-Delete

Run manually as part of the offboarding checklist (see Personnel Security Procedures), 1 year after the offboarding date:

```sql
-- Confirm the user's offboarding date first
SELECT id, username, email, deactivated_at FROM users WHERE username = '[username]';

-- Hard delete (run only if 1+ year has elapsed since deactivated_at)
DELETE FROM users WHERE username = '[username]' AND deactivated_at < datetime('now', '-1 year');
VACUUM;
```

---

## 4. Disposal Method

### 4.1 In-Database Deletion

Standard disposal for all non-emergency situations:

1. Execute `DELETE` statements targeting rows past their retention window
2. Execute `VACUUM` to reclaim freed pages and prevent forensic recovery of deleted rows within the DB file
3. Log the purge event (timestamp, table, row count deleted) to the application audit log or purge log

### 4.2 Database File Disposal

When retiring the entire database (e.g., decommissioning the platform or migrating to a new DB):

```bash
# Overwrite with random data before deletion to prevent forensic recovery
# (DB is encrypted, but belt-and-suspenders approach)
shred -vzn 3 /path/to/blacksite.db

# Alternatively, if shred is not available:
dd if=/dev/urandom of=/path/to/blacksite.db bs=1M count=$(du -m /path/to/blacksite.db | cut -f1)
rm /path/to/blacksite.db
```

### 4.3 Backup Copy Disposal

Backups on the iapetus NAS should be reviewed annually. Backup files older than 1 year from the backup date are eligible for deletion. SMB deletion via rclone or direct SSH:

```bash
# List old backups
ssh -p 20234 iapetus 'ls -lah clawd/backups/borisov/blacksite/'

# Delete backups older than 365 days
find /home/graycat/shares/clawd/backups/borisov/blacksite/ -mtime +365 -delete
```

---

## 5. Legal Hold Override Procedure

A legal hold suspends normal retention and disposal procedures for data that is or may be relevant to litigation, regulatory investigation, or a formal legal request.

### Activating a Legal Hold

1. Receipt of a legal hold notice, subpoena, litigation hold letter, or court order triggers immediate hold activation
2. The Platform Administrator identifies all data categories covered by the hold
3. Automated purge scripts are disabled or modified to exclude held data:
   - Comment out the relevant DELETE statements in the purge script
   - Add a `legal_hold` flag or maintain a separate list of held record IDs
4. A hold record is created at `/home/graycat/docs/legal-holds/YYYY-MM-DD-hold.md` documenting:
   - The legal basis for the hold
   - What data is covered
   - The hold activation date
   - The responsible party who issued the hold
5. Notify legal counsel

### Releasing a Legal Hold

1. Obtain written confirmation that the hold is lifted (from legal counsel or the issuing authority)
2. Re-enable normal retention procedures for the previously held data
3. If the held data has passed its normal retention window, schedule disposal within 30 days of hold release
4. Document hold release in the hold record

---

## 6. Annual Review

This policy is reviewed annually (next review: 2027-03-09) or when:

- A new data category is introduced to the platform
- Regulatory requirements change (e.g., new NIST SP guidance, state law changes)
- A retention-related audit finding is received
- The backup or storage infrastructure changes significantly

The annual review should confirm:
- All retention periods remain appropriate and legally supported
- Automated purge scripts are functioning and logging correctly
- No data categories are being retained beyond their defined window
- Legal hold register is current (no stale holds)

---

## 7. References

- NIST SP 800-53 Rev 5: AU-11 (Audit Record Retention), SI-12 (Information Management and Retention)
- 36 CFR Part 1236 (Electronic Records Management)
- FISMA 2014 (44 U.S.C. § 3554)
- HIPAA 45 CFR § 164.530(j) — medical records retention (6 years) for BAA customers
- This platform's Privacy Notice (privacy-notice.md)
- This platform's Personnel Security Procedures (personnel-security-procedures.md)

---

## 8. Automated Purge — Installation

Scripts are ready at `/home/graycat/scripts/`. To activate the daily purge timer:

    sudo cp /home/graycat/scripts/blacksite-purge.service /etc/systemd/system/
    sudo cp /home/graycat/scripts/blacksite-purge.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now blacksite-purge.timer
    sudo systemctl status blacksite-purge.timer

The purge script (`blacksite-data-purge.sh`) targets the demo DB (`stock.db`) directly
and is schema-aware: it checks `PRAGMA table_info` for each table before issuing any
DELETE, and logs a summary of rows removed to `/var/log/blacksite-purge.log`.

**Main DB (encrypted) purge** is pending application-level implementation. The script
logs a NOTICE each run as a reminder. Until implemented, run manual purges via the
application API or an authenticated maintenance endpoint (see §3.2).
