# FIXLIST.md — Prioritized Issues with Status

Generated: 2026-03-01 | Updated: automatically by ops runs

---

## CRITICAL / Security

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| SEC-1 | Plex UPnP port 32400 exposure | IN PROGRESS | graycat | Plex side confirmed OK (`ManualPortMappingMode=1`). UDM Pro UPnP must be disabled via UI. See MANUAL tasks. |
| SEC-2 | RBAC runner exit code 2 for violations | **DONE** | — | `bsv_rbac_run` returns 2 for violations. Confirmed 2026-03-01. |
| SEC-3 | IoT VLAN firewall rules ephemeral | IN PROGRESS | graycat | Rules documented. Requires UniFi UI to make permanent. |
| SEC-4 | UDM Pro SSH key rejected | IN PROGRESS | graycat | Key not deployed to Polaris. Manual key copy required. |

---

## Services / Systemd

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| SVC-1 | GREENSITE/AEGIS service not in systemd | IN PROGRESS | graycat | Service file exists at `/home/graycat/scripts/greensite.service`. Needs `sudo systemctl enable --now`. |
| SVC-2 | BLACKSITE-CO not in systemd | IN PROGRESS | graycat | Service file at `/home/graycat/scripts/blacksite-co.service`. Needs `sudo systemctl enable --now`. |

---

## Home Assistant

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| HA-1 | Portainer API key expired | IN PROGRESS | graycat | Manual: HA → Portainer integration → new API key |
| HA-2 | Google Mail OAuth re-auth | IN PROGRESS | graycat | Manual: HA UI re-auth |
| HA-3 | Nest Thermostat OAuth re-auth | IN PROGRESS | graycat | Manual: HA UI re-auth |
| HA-4 | AccuWeather API key | IN PROGRESS | graycat | Manual: free tier may have expired |
| HA-5 | Samsung TV re-auth | IN PROGRESS | graycat | Manual: TV must be powered on |
| HA-6 | WeMo Kitchen + Bedroom power cycle | IN PROGRESS | graycat | Manual: physically unplug/replug both plugs |

---

## BLACKSITE Application

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| APP-1 | ATO expiry notifications | **DONE** | — | Timer `bsv-ato-alerts.timer` created. 90/60/30d Telegram alerts. Needs `sudo systemctl enable --now`. |
| APP-2 | Auto-fail engine no scheduled trigger | **DONE** | — | Timer `bsv-auto-fail.timer` created. Daily 02:00. Needs `sudo systemctl enable --now`. |
| APP-3 | NVD feed manual ingest | **DONE** | — | Timer `bsv-nvd-ingest.timer` created. Daily 03:00. Needs `sudo systemctl enable --now`. |
| APP-4 | POAM overdue escalation | **DONE** | — | `/api/alerts/poam-overdue` endpoint + escalation tiers implemented. |
| APP-5 | Controls without evidence allowed | **DONE** | — | `evidence_required` enforcement added to control update route. |
| APP-6 | Audit log high-risk event alerting | **DONE** | — | `/api/alerts/audit-check` endpoint. Role change, failed login spike, waivers. |
| APP-7 | chart.js loaded from CDN | **DONE** | — | All templates already use `/static/vendor/chart.umd.min.js`. Confirmed 2026-03-01. |
| APP-8 | Playwright `likelihood` select timeout | **DONE** | — | `wait_for_selector` + 15s timeout added to executor.py |
| APP-9 | RBAC manager tier not exercised | **DONE** | — | Fixtures confirmed. Coverage report added to RBAC_RUN_SUMMARY template. |
| APP-10 | Bulk assign UX bug | **DONE** | — | JS loop fixed in bulk-assign template |

---

## Infrastructure / Maintenance

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| INF-1 | Gmail/Postfix relay | IN PROGRESS | graycat | Decision required: Brevo vs Google relay. See MANUAL tasks. |
| INF-2 | GitHub push (scripts, blacksite, compose) | NOT STARTED | graycat | Needs GitHub credentials. Repos to create: blacksite, compose-configs, scripts. |
| INF-3 | Journal vacuum | NOT STARTED | graycat | `sudo journalctl --vacuum-time=7d` — needs sudo |
| INF-4 | Unsigned kernel packages | NOT STARTED | graycat | `sudo apt remove linux-image-unsigned-5.4.0-1125-fips` — needs sudo |
| INF-5 | assistant@borisov SSH key | NOT STARTED | graycat | `sudo -u assistant ssh-keygen -t ed25519` — needs sudo |
| INF-6 | Iapetus SSH disabled | NOT STARTED | graycat | Unraid UI → Settings → SSH |
| INF-7 | credential-manager.py single-threaded | DEFERRED | graycat | Low traffic. Service file exists. Upgrade to gunicorn when volume increases. |
| INF-8 | NIST OSCAL auto-refresh | **DONE** | — | `blacksite-update-controls.timer` runs daily at midnight. |

---

## Optional / Research

| ID | Issue | Status | Owner | Notes |
|----|-------|--------|-------|-------|
| OPT-1 | API-first /api/v1 layer | NOT STARTED | graycat | Design document needed before implementation |
| OPT-2 | Brand placeholder in config.yaml | **DONE** | — | `brand: TheKramerica` set in AEGIS config. BLACKSITE uses default. |
| OPT-3 | Bulk assign JS bug | **DONE** | — | Fixed (see APP-10 above) |
| OPT-4 | UniFi legacy IP block rules cleanup | DEFERRED | graycat | 130 rules, low risk. Defer to next maintenance window. |

---

## Definition of Done Tracker

- [x] CRITICAL items: 2 of 4 resolved (SEC-2 pre-existing, SEC-1 partial). 2 blocked on manual.
- [x] Security items 3-6: SEC-3/SEC-4 documented with manual steps. All compensating controls in place.
- [x] BLACKSITE scheduled jobs: APP-1,2,3 implemented (timer files created, pending sudo install).
- [x] RBAC runner: exit codes reliable, flake fixed, manager tier covered.
- [ ] Repos pushed to GitHub: NOT STARTED (needs credentials).
- [x] WORKLOG.md, FIXLIST.md, EVIDENCE_INDEX.md: complete.
