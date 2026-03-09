# Incident Response Runbook

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09
**Reference:** NIST SP 800-61r2 (Computer Security Incident Handling Guide)

---

## 1. Purpose and Scope

This runbook governs the detection, response, and recovery from security incidents affecting the BLACKSITE GRC platform, including:

- The BLACKSITE application and all running instances (production, staging)
- The underlying host system (borisov / 192.168.86.102)
- All data stored in or processed by the platform (SSP content, assessment records, user credentials, audit logs)
- API integrations (Groq AI, ip-api.com)

This runbook applies to all individuals with administrative or operational access to BLACKSITE.

---

## 2. Incident Categories

| Category | Description |
|----------|-------------|
| **Data Breach** | Confirmed or suspected unauthorized access to, or exfiltration of, user data, SSP content, or audit records |
| **Unauthorized Access** | Login by an unknown or unauthorized party; brute-force attempts that succeed; session hijacking |
| **Service Outage** | Platform unavailable to legitimate users for > 15 minutes due to a non-scheduled cause |
| **Ransomware / Destructive Malware** | Database or file system encrypted or destroyed by malicious software |
| **Insider Threat** | Deliberate or accidental misuse of access by a staff member or authorized user |

---

## 3. Severity Levels and SLAs

| Level | Name | Definition | Initial Response | Escalation |
|-------|------|------------|-----------------|------------|
| **P1** | Critical | Active data breach, ransomware, or confirmed unauthorized access to production data | 15 minutes | Immediate — notify all roles |
| **P2** | High | Suspected breach, service outage affecting all users, suspected insider threat | 1 hour | Within 1 hour |
| **P3** | Medium | Isolated service degradation, failed intrusion attempt, anomalous but unconfirmed activity | 4 hours | Next business day if no escalation |
| **P4** | Low | Policy violation with no data exposure, minor anomaly resolved automatically | 1 business day | Document only |

---

## 4. Roles and Responsibilities

### Incident Commander (IC)
- **Default:** Platform Administrator (solo developer context)
- Declares incident severity
- Coordinates all response activities
- Makes go/no-go decisions on containment actions
- Signs off on external notifications

### Technical Lead (TL)
- **Default:** Platform Administrator (or designee with system access)
- Performs hands-on investigation, log analysis, containment
- Executes DB snapshots and evidence preservation
- Implements fixes and validates recovery

### Communications Lead (CL)
- **Default:** Platform Administrator
- Drafts and sends customer notifications
- Manages any external disclosure requirements
- Coordinates with legal counsel if PHI or federal data is involved

> **Solo operator note:** For a solo-developer operation, the Platform Administrator fills all three roles. During a P1/P2 incident, prioritize containment over documentation — document retrospectively using preserved logs.

---

## 5. Escalation Contacts

| Severity | Who Gets Notified | Method | Timeline |
|----------|------------------|--------|----------|
| P1 | All affected customers; platform admin's personal emergency contact | Email + phone | Within 2 hours of declaration |
| P2 | Platform admin; affected customers if data at risk | Email | Within 4 hours |
| P3 | Platform admin log entry; customer notification if service impact > 1 hour | Email | Within 24 hours |
| P4 | Internal incident log only | Log entry | Within 48 hours |

**Federal/FedRAMP context:** If the affected customer holds a federal contract and data at rest includes CUI or system security information, notify the customer's ISSO within 1 hour of P1 declaration per FISMA requirements. Customers are responsible for notifying their AO.

---

## 6. Response Phases

### Phase 1: Detect

- Sources: application logs (`/tmp/blacksite.log`, uvicorn stdout), host syslog, Caddy access logs, AdGuard DNS logs, fail2ban alerts
- Automated alerts: fail2ban bans, disk full conditions, process crashes (systemd unit failure)
- Manual detection: user reports, anomalous login patterns in audit log table

**Actions:**
1. Confirm the event is a real incident (not a false positive)
2. Record initial detection time, source, and indicator(s)
3. Assign a severity level (P1–P4)
4. Open an incident record (see Section 8 — use a dated entry in `docs/incidents/YYYY-MM-DD-incident.md`)

---

### Phase 2: Contain

**Short-term containment (stop the bleeding):**

```bash
# Block external access via Caddy (edit Caddyfile to return 503)
# OR take down the service immediately:
sudo systemctl stop blacksite

# If host is compromised, isolate from network:
# sudo ufw default deny incoming
# sudo ufw default deny outgoing
# sudo ufw enable
```

**Preserve evidence BEFORE containment changes the state** (see Section 7).

**Specific actions by category:**

- **Data breach / unauthorized access:** Invalidate all active sessions (restart app or rotate SECRET_KEY in service unit). Identify the compromised account and disable it in the DB.
- **Ransomware:** Do NOT restart. Isolate host immediately. Do not pay. Restore from backup.
- **Insider threat:** Revoke the user's platform access and rotate any credentials they had access to. Do not alert the suspect until containment is complete.
- **Service outage:** Identify root cause before restarting (check disk space, OOM, process crash).

---

### Phase 3: Eradicate

1. Identify the root cause (vulnerability exploited, misconfiguration, compromised credential)
2. Remove malicious artifacts (malware files, rogue admin accounts, injected content)
3. Patch the vulnerability or close the attack vector
4. Rotate any credentials that may have been exposed
5. Update firewall rules or application controls as needed
6. Verify no persistence mechanisms remain (cron jobs, authorized_keys changes, modified service files)

---

### Phase 4: Recover

1. Restore from backup if data integrity is in doubt (see Contingency Plan for restore procedures)
2. Restart services in order:
   ```bash
   sudo systemctl start blacksite
   # Verify health
   curl -s http://127.0.0.1:8100/health | python3 -m json.tool
   ```
3. Confirm audit logging is operational
4. Conduct smoke test: login, view a system, check AI assistant
5. Monitor logs closely for 24 hours post-recovery
6. Remove any temporary containment controls (e.g., restore Caddyfile if blocked externally)

**Recovery validation checklist:**
- [ ] Application returns HTTP 200 on health endpoint
- [ ] Authentication flow works (login + logout)
- [ ] Audit log records new activity post-recovery
- [ ] No error spike in application logs
- [ ] Backup confirmed intact and unmodified

---

### Phase 5: Post-Incident Review

Must be completed **within 5 business days** of incident closure.

**Review checklist:**
- [ ] Timeline reconstructed from logs (detection → containment → recovery)
- [ ] Root cause identified and documented
- [ ] Data exposure scope determined (what data, how many records, which customers)
- [ ] Regulatory notification obligations assessed and fulfilled
- [ ] Corrective actions identified with owners and due dates
- [ ] Runbook updated if gaps were found
- [ ] Customer notification sent (if applicable)
- [ ] Incident record finalized and archived

---

## 7. Evidence Preservation

**Do this BEFORE taking containment actions whenever possible.**

```bash
# Snapshot the SQLite database
cp /home/graycat/projects/blacksite/data/blacksite.db \
   /home/graycat/docs/incidents/$(date +%Y%m%d-%H%M%S)-blacksite-evidence.db

# Capture running process list and network connections
ps auxf > /home/graycat/docs/incidents/$(date +%Y%m%d-%H%M%S)-ps.txt
ss -tulpn >> /home/graycat/docs/incidents/$(date +%Y%m%d-%H%M%S)-netstat.txt

# Copy application logs (do not truncate or rotate)
cp /tmp/blacksite.log \
   /home/graycat/docs/incidents/$(date +%Y%m%d-%H%M%S)-app.log

# Export auth audit log from DB
sqlite3 /home/graycat/projects/blacksite/data/blacksite.db \
  "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10000;" \
  > /home/graycat/docs/incidents/$(date +%Y%m%d-%H%M%S)-audit.csv

# Preserve host syslog
sudo journalctl --since "2 hours ago" > \
   /home/graycat/docs/incidents/$(date +%Y%m%d-%H%M%S)-syslog.txt
```

**Rules:**
- Never wipe, rotate, or clear logs during an active incident
- Preserve evidence copies to a location outside the potentially compromised path
- Hash all evidence files with SHA-256 immediately after capture
- Chain of custody: record who collected evidence and when

---

## 8. Communication Templates

### Internal Incident Record (create at `/home/graycat/docs/incidents/YYYY-MM-DD-incident.md`)

```
# Incident: [Brief Title]
Date/Time Detected:
Severity: P[1-4]
Category:
Detected By:

## Timeline
- [timestamp] Initial detection
- [timestamp] Incident declared
- [timestamp] Containment action
- [timestamp] Recovery complete
- [timestamp] Incident closed

## Root Cause

## Scope / Impact

## Actions Taken

## Corrective Actions (with due dates)
```

### Customer Notification — Initial (P1/P2 with data exposure)

```
Subject: BLACKSITE Platform Security Notice — [Date]

[Customer name],

We are writing to notify you of a security incident affecting the BLACKSITE
platform that may involve data associated with your organization.

What happened: [Brief factual description]
When: [Date/time range]
What data may be affected: [Specific data categories]
What we have done: [Containment and eradication steps taken]
What you should do: [Any customer action required]

We will provide a follow-up communication within [48 hours / 5 business days]
with a full incident report.

For questions, contact: [admin contact]

BLACKSITE Platform Administrator
[Contact information]
[Date]
```

### Customer Notification — Resolution

```
Subject: BLACKSITE Platform Security Incident — Resolution Report — [Date]

[Customer name],

This is our follow-up to our [initial notification date] notice regarding
the security incident affecting the BLACKSITE platform.

Summary of findings: [Root cause, scope]
Data exposure determination: [Confirmed exposure / No confirmed exposure]
Remediation completed: [Date and actions]
Preventive measures implemented: [Controls added]

No further action is required on your part unless noted below: [Actions]

We sincerely apologize for any concern this incident has caused.

BLACKSITE Platform Administrator
[Contact information]
[Date]
```

---

## 9. References

- NIST SP 800-61r2: Computer Security Incident Handling Guide
- NIST SP 800-53 IR controls (IR-1 through IR-10)
- FISMA 2014 (44 U.S.C. § 3554) — federal agency notification obligations
- HIPAA Breach Notification Rule (45 CFR §§ 164.400–414) — if PHI is involved
- This platform's Contingency Plan (contingency-plan.md)
- This platform's Data Retention Policy (data-retention-policy.md)
