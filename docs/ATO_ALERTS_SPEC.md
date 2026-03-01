# ATO_ALERTS_SPEC.md — BLACKSITE ATO Expiry Notification Policy

Version: 1.0 | Owner: dan (AO) | Updated: 2026-03-01

---

## 1. Purpose

Define when, how, and to whom ATO expiry notifications are sent to prevent systems from
operating without valid authorization (which constitutes a material compliance violation
under FISMA and NIST SP 800-37 Rev 2).

---

## 2. Trigger Conditions

| Condition | Threshold | Alert Tier | Severity |
|-----------|-----------|------------|----------|
| ATO expiring | ≤ 90 days | Tier 4 — Informational | NOTICE |
| ATO expiring | ≤ 60 days | Tier 3 — Operational | WARNING |
| ATO expiring | ≤ 30 days | Tier 2 — Governance | HIGH |
| ATO expired | Past expiry date | Tier 1 — Executive | CRITICAL |

---

## 3. Alert Routing

| Tier | Recipients | Content |
|------|------------|---------|
| Tier 1 (expired) | AO (dan) via Telegram | System name, days overdue, required action: immediate reauthorization or emergency authorization |
| Tier 2 (30d) | ISSO + ISSM via Telegram | Package status, AO review timeline, evidence checklist |
| Tier 3 (60d) | ISSO via Telegram | ATO package readiness, control gap count, outstanding POA&Ms |
| Tier 4 (90d) | ISSO via Telegram | Advance notice, begin reauthorization planning |

---

## 4. Delivery Mechanism

- **Transport**: Telegram via `notify-telegram.sh` bot (chat_id: 2054649730)
- **Schedule**: Daily at 07:00 UTC via `bsv-ato-alerts.timer`
- **Endpoint**: `GET /api/alerts/ato-expiry` (admin-scoped)
- **Dedupe key**: `ato_alert:{system_id}:{threshold}:{date}` stored in `system_settings` table
- **Dedupe window**: 1 alert per system per threshold window per day

---

## 5. Alert Message Format

### Tier 1 — Expired
```
🔴 BLACKSITE ATO Alert — EXPIRED

System: [name]
ATO Expiry: [date]
Days: EXPIRED (N days ago)
Action: Begin reauthorization package immediately.
Review: https://blacksite.borisov.network/systems/{id}
```

### Tier 2 — 30-day warning
```
🟠 BLACKSITE ATO Alert — 30-day warning

System: [name]
ATO Expiry: [date]
Days: 30
Action: Begin reauthorization package immediately.
Review: https://blacksite.borisov.network/systems/{id}
```

---

## 6. Acceptance Criteria

- [ ] Alert fires within 24h of system crossing a threshold
- [ ] Each system receives at most one alert per threshold per day
- [ ] Expired systems trigger Tier 1 every day until reauthorized
- [ ] Alert includes system name, expiry date, days remaining, and review URL
- [ ] Service job logs run results to `journalctl -u bsv-ato-alerts`

---

## 7. Test Verification

To verify: create a test system with `auth_expiry` set to today - 1 day, then run:
```bash
curl -s -H "Remote-User: dan" http://127.0.0.1:8100/api/alerts/ato-expiry
# Expected: {"alerts_sent": 1, "detail": [{"system": "...", "threshold": "expired", ...}]}
```
Check journalctl for confirmation and Telegram for delivery.

---

## 8. Installation

```bash
sudo cp /home/graycat/scripts/bsv-ato-alerts.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bsv-ato-alerts.timer
sudo systemctl list-timers bsv-ato-alerts.timer
```

---

## 9. Rollback

```bash
sudo systemctl disable --now bsv-ato-alerts.timer
sudo systemctl disable bsv-ato-alerts.service
```
Alert dedupe keys in `system_settings` can be cleared via:
```bash
sqlite3 /home/graycat/projects/blacksite/data/blacksite.db \
  "DELETE FROM system_settings WHERE key LIKE 'ato_alert:%';"
```
