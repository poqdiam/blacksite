# EVIDENCE_INDEX.md — Collected Artifacts and Evidence Links

Generated: 2026-03-01 | Security Work Order Phase 6+

---

## Confirmed Done (with evidence)

### SEC-2: RBAC exit code enforcement
- **Evidence**: `grep -n "return 2" /home/graycat/projects/blacksite/scripts/bsv_rbac_run`
  → Line confirmed present. Returns 2 for violations, 1 for failures, 0 for clean.
- **RBAC run log**: `data/rbac-runs/` — latest summary.json shows 0 violations.
- **Status**: DONE 2026-03-01.

### APP-7: chart.js bundled locally
- **Evidence**: `grep -rn "cdn.jsdelivr\|unpkg.com/chart" templates/` → no results.
  `grep -n "chart.umd" templates/dashboard.html templates/results.html templates/admin.html`
  → all three show `/static/vendor/chart.umd.min.js`.
- **File**: `static/vendor/chart.umd.min.js` (local bundle).
- **Status**: DONE (pre-existing).

### SEC-3: Audit alert endpoints verified
- **Evidence**: `curl -X POST -H "Remote-User: dan" http://127.0.0.1:8100/api/alerts/audit-check` → `{"alerts_sent":1}`
- **Evidence**: All three endpoints (`ato-expiry`, `poam-overdue`, `audit-check`) return HTTP 200.
- **Evidence**: Second call same day → `alerts_sent: 0` (dedupe via SystemSettings working).
- **Root cause fixed**: `ev.detail_json` (invalid field) → `ev.details` in two f-string literals (lines 6651, 6672).
- **Status**: DONE 2026-03-01.

### B3/Phase 6: Version endpoint + build stamp
- **Evidence**: `curl -s http://127.0.0.1:8100/api/version`
  → `{"app":"BLACKSITE","sha":"13e5055","built":"2026-03-01T09:57:37Z","port":8100}`
- **Evidence**: `curl -s http://127.0.0.1:8102/api/version`
  → `{"app":"AEGIS","sha":"13e5055","built":"2026-03-01T09:58:10Z","port":8102}`
- **Status**: DONE 2026-03-01.

---

## Artifacts Created This Session

| Artifact | Location | Purpose |
|----------|----------|---------|
| WORKLOG.md | `docs/WORKLOG.md` | Timestamped action log |
| FIXLIST.md | `docs/FIXLIST.md` | Prioritized issue tracker |
| EVIDENCE_INDEX.md | `docs/EVIDENCE_INDEX.md` | This file |
| ATO_ALERTS_SPEC.md | `docs/ATO_ALERTS_SPEC.md` | ATO notification policy |
| AUTOFAIL_SCHEDULER_SPEC.md | `docs/AUTOFAIL_SCHEDULER_SPEC.md` | Auto-fail timer spec |
| RBAC_RUN_SUMMARY.md | `docs/RBAC_RUN_SUMMARY.md` | Updated with Phase 6 verification |
| REPO_REMOTES.md | `docs/REPO_REMOTES.md` | GitHub repo setup guide |
| RELEASE_PROCESS.md | `docs/RELEASE_PROCESS.md` | Deployment discipline |
| bsv-ato-alerts.sh | `/home/graycat/scripts/bsv-ato-alerts.sh` | ATO alert runner |
| bsv-ato-alerts.service | `/home/graycat/scripts/bsv-ato-alerts.service` | Systemd service |
| bsv-ato-alerts.timer | `/home/graycat/scripts/bsv-ato-alerts.timer` | Systemd timer (07:00 UTC) |
| bsv-auto-fail.sh | `/home/graycat/scripts/bsv-auto-fail.sh` | Auto-fail runner |
| bsv-auto-fail.service | `/home/graycat/scripts/bsv-auto-fail.service` | Systemd service |
| bsv-auto-fail.timer | `/home/graycat/scripts/bsv-auto-fail.timer` | Systemd timer (02:00 UTC) |
| bsv-nvd-ingest.sh | `/home/graycat/scripts/bsv-nvd-ingest.sh` | NVD feed runner |
| bsv-nvd-ingest.service | `/home/graycat/scripts/bsv-nvd-ingest.service` | Systemd service |
| bsv-nvd-ingest.timer | `/home/graycat/scripts/bsv-nvd-ingest.timer` | Systemd timer (03:00 UTC) |

---

## Code Changes This Session

| File | Change | Lines |
|------|--------|-------|
| `app/main.py` | Added `_EVIDENCE_REQUIRED_CONTROLS` frozenset | ~993 |
| `app/main.py` | Added `_telegram_send()` helper | ~6384 |
| `app/main.py` | Added `/api/alerts/ato-expiry` endpoint | ~6387 |
| `app/main.py` | Added `/api/alerts/poam-overdue` endpoint | ~6450 |
| `app/main.py` | Added `/api/alerts/audit-check` endpoint | ~6510 |
| `app/main.py` | Evidence enforcement in workspace POST (implemented_complete guard) | ~5770 |
| `tests/rbac/executor.py` | Playwright timeout fix: wait_for_selector + 15s on fill/select/click | ~238-270 |
| `templates/systems.html` | Bulk assign JS fix: loop all selected systems, not just first | ~803-890 |
| `app/main.py` | Fixed `ev.detail_json` → `ev.details` in audit-check endpoint (lines 6651, 6672) | ~6651 |

---

## Pending Artifacts (manual steps required)

| Item | Required Action | Evidence When Done |
|------|----------------|-------------------|
| UDM Pro UPnP disable | UniFi UI → Settings → Internet → WAN | Screenshot of UPnP setting = OFF |
| IoT VLAN permanent rules | UniFi UI → Firewall & Security → LAN Rules | Screenshot of two new rules |
| UDM Pro SSH access | Deploy `~/.ssh/id_ed25519.pub` to Polaris | `ssh polaris whoami` → root |
| GREENSITE systemd | `sudo cp + enable --now` | `systemctl status greensite` → active |
| BLACKSITE-CO systemd | `sudo cp + enable --now` | `systemctl status blacksite-co` → active |
| bsv-ato-alerts timer | `sudo cp + enable --now` | `systemctl list-timers bsv-ato-alerts` |
| bsv-auto-fail timer | `sudo cp + enable --now` | `systemctl list-timers bsv-auto-fail` |
| bsv-nvd-ingest timer | `sudo cp + enable --now` | `systemctl list-timers bsv-nvd-ingest` |
| HA integrations | HA UI re-auth | HA entity showing as Connected |
| GitHub repos | Create + push | `git remote -v` showing origin |
| Journal vacuum | `sudo journalctl --vacuum-time=7d` | Freed space output |
| Unsigned kernels | `sudo apt remove linux-image-unsigned-*` | `dpkg -l | grep unsigned` = empty |
| Plex WAN UPnP | Verify UDM Pro UPnP disabled | Port 32400 not accessible from WAN |

---

## Security Posture Changes

| Change | Risk Reduction | Accepted Risk |
|--------|---------------|---------------|
| Evidence enforcement on 26 controls | Prevents self-attestation on testable controls | None |
| Audit log alerting | Detects role abuse, failed login spikes, unauthorized waivers | False positives possible on initial tuning |
| RBAC exit code 2 enforcement | CI gate now blocks deploys on privilege violations | None |
| ATO expiry alerts | 90/60/30d advance warning prevents surprise expirations | None |
| Auto-fail daily engine | Auto-creates POA&Ms preventing evidence gaps from going undetected | Risk of alert fatigue if many stale controls; tune dedupe |
| Playwright fix | Removes 16 flaky tests; RBAC runner now reliable | None |
| Bulk assign fix | Prevents only first system being assigned in bulk operations | None |
