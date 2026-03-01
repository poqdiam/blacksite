# AUTOFAIL_SCHEDULER_SPEC.md — BLACKSITE Auto-Fail Engine Schedule Specification

Version: 1.0 | Owner: dan (AO) | Updated: 2026-03-01

---

## 1. Purpose

The auto-fail engine (`_run_auto_fail_checks()`) automatically creates POA&M items when
compliance failures are detected without human review. This document specifies the trigger
conditions, schedule, job wiring, and output format.

---

## 2. Auto-Fail Trigger Conditions

| Trigger Type | Condition | Target |
|-------------|-----------|--------|
| `evidence_stale` | SystemControl evidence older than freshness window (default: 365d) | SystemControl records with old `last_updated_at` |
| `review_overdue` | Required assessment not completed within cadence window | SystemControl where `review_frequency_days` exceeded |
| `document_expired` | ATO document with `valid_until` in the past | AtoDocument where `valid_until < today` |
| `parameter_drift` | ControlParameter with `drift_detected = True` | ControlParameter records |
| `patch_sla_breach` | NVD vulnerability on in-scope asset older than SLA | Future: requires asset→CVE mapping |
| `backup_missed` | ePHI system backup missed (future: requires backup job telemetry) | Future: requires backup API integration |

---

## 3. Auto-Generated POA&M Record Fields

Each auto-created POA&M contains:
- `created_by`: `"auto_fail:{trigger_type}:{resource_id}"`
- `system_id`: affected system
- `weakness_name`: auto-generated description of the failure
- `severity`: Critical (document_expired, review_overdue) | High (evidence_stale, parameter_drift)
- `status`: `"open"`
- `scheduled_completion`: today + 30 days (document_expired) or today + 90 days (others)
- `poam_id`: auto-generated in ABVR format
- Dedupe key: `auto_fail_event_id` links to `auto_fail_events` table — prevents duplicate POA&Ms

---

## 4. Schedule

| Job | Timer | Window |
|-----|-------|--------|
| Auto-fail engine | `bsv-auto-fail.timer` | Daily at 02:00 UTC |
| ATO + POAM alerts | `bsv-ato-alerts.timer` | Daily at 07:00 UTC |
| NVD feed ingest | `bsv-nvd-ingest.timer` | Daily at 03:00 UTC |
| NIST controls update | `blacksite-update-controls.timer` | Daily at 00:00 UTC |

---

## 5. Endpoint

```
POST /admin/auto-fail
```
- Admin-only
- Triggers `_run_auto_fail_checks()` across all active systems
- Returns JSON with `created`, `updated`, `skipped` counts
- Logged to AuditLog with `action="RUN"`, `resource_type="auto_fail_engine"`

---

## 6. Job Wiring

```
bsv-auto-fail.timer
  → bsv-auto-fail.service
    → /home/graycat/scripts/bsv-auto-fail.sh
      → POST http://127.0.0.1:8100/admin/auto-fail (Remote-User: dan)
      → Parses JSON response
      → If created > 0: sends Telegram alert
      → Writes result to /var/log/bsv-auto-fail.log
      → journalctl -u bsv-auto-fail
```

---

## 7. Log Output Format

```
[2026-03-01T02:00:05Z] === bsv-auto-fail START ===
[2026-03-01T02:00:07Z] Auto-fail complete. POA&M items created/updated: 3
[2026-03-01T02:00:08Z] === bsv-auto-fail DONE ===
```

---

## 8. Proof of Execution

After `sudo systemctl enable --now bsv-auto-fail.timer`:
```bash
# Check next run
systemctl list-timers bsv-auto-fail.timer

# Check last run
journalctl -u bsv-auto-fail --since "24h ago"

# Manual trigger (test)
sudo systemctl start bsv-auto-fail.service
journalctl -u bsv-auto-fail -n 20

# Verify via API
curl -s -H "Remote-User: dan" -X POST http://127.0.0.1:8100/admin/auto-fail
```

---

## 9. Installation

```bash
sudo cp /home/graycat/scripts/bsv-auto-fail.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bsv-auto-fail.timer
```

---

## 10. Rollback

```bash
sudo systemctl disable --now bsv-auto-fail.timer
```
Auto-fail POA&Ms created by the engine can be identified by `created_by LIKE 'auto_fail:%'`
and soft-deleted if the trigger was a false positive.

---

## 11. Acceptance Criteria

- [ ] `bsv-auto-fail.timer` is active and shows next trigger at 02:00 UTC
- [ ] `journalctl -u bsv-auto-fail` shows at least one successful run entry
- [ ] At least one auto-fail POA&M exists in DB (`created_by LIKE 'auto_fail:%'`)
- [ ] Telegram notification received when POA&M items created
- [ ] Zero duplicate POA&Ms for same trigger+resource+day
