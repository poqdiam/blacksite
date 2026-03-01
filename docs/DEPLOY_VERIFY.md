# DEPLOY_VERIFY.md — BLACKSITE / AEGIS Fork Deployment Verification

Generated: 2026-03-01
Phase 6 — B3 delivery (live-verified 2026-03-01T09:58Z)

---

## 1. Fork Inventory

| Instance | Binds | DB | Entry Point | Git |
|----------|-------|----|-------------|-----|
| **BLACKSITE** (master) | 127.0.0.1:8100 | `blacksite/data/blacksite.db` | `app/main.py` → `uvicorn app.main:app` | git master |
| **BLACKSITE-CO** | 127.0.0.1:8101 | same as BLACKSITE (separate process, same codebase) | same entry point | git master |
| **AEGIS** (greensite) | 127.0.0.1:8102 | `greensite/greensite.db` | `greensite_main.py` → symlink shadow of blacksite app | symlink shadow |

All three forks share `app/main.py` from `/home/graycat/projects/blacksite/`. AEGIS reads it via symlink; BLACKSITE-CO runs it from a second process bound to port 8101. No branching — single codebase.

---

## 2. Live Build Verification

### BLACKSITE (port 8100)

```sh
# Version endpoint — available after Phase 6 restart
curl -s http://127.0.0.1:8100/api/version | python3 -m json.tool
```

Expected output (example):
```json
{
  "app": "BLACKSITE",
  "env": "production",
  "sha": "13e5055",
  "sha_long": "13e5055e379ebc42086a591b38ca467b0b04ed93",
  "built": "2026-03-01T09:46:08Z",
  "port": 8100
}
```

### AEGIS (port 8102)

```sh
curl -s http://127.0.0.1:8102/api/version | python3 -m json.tool
```

Expected: same sha (same codebase via symlink), `"app": "AEGIS"`, `"port": 8102`.

---

## 3. Process / Port Verification

```sh
# Show all running BLACKSITE/AEGIS processes
ps aux | grep uvicorn | grep -v grep
```

Expected PIDs (approximate — will change after restart):
| PID | Port | Instance |
|-----|------|----------|
| ~1642868 | 8101 | BLACKSITE-CO |
| ~1669036 | 8102 | AEGIS |
| (main blacksite) | 8100 | BLACKSITE |

```sh
# Confirm ports are listening
ss -tlnp | grep -E '8100|8101|8102'
```

---

## 4. Smoke Tests

### Auth guard
```sh
# /employer requires dan-only access via AEGIS greensite_guard middleware
# From localhost without Remote-User header → 403
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8102/employer
# Expected: 403
```

### Health check
```sh
curl -s http://127.0.0.1:8100/health
# Expected: {"status":"ok","controls":<N>}
```

### Version endpoint
```sh
curl -s http://127.0.0.1:8100/api/version
# Expected: 200 + JSON with sha, env, built
```

---

## 5. Theme Availability (14 themes)

All themes are served from `static/` via symlink in AEGIS. The base.html theme switcher lists all 14:
`midnight | ocean | terminal | synthwave | crimson | amber | noir | violet | carbon | navy | forest | daylight | desert | bloodmoon`

Verify in browser: user dropdown → Theme → any theme loads without 404.

---

## 6. Build Stamp in Footer

After Phase 6 restart, the sidebar footer in every page shows:
```
BLACKSITE · 13e5055 · 2026-03-01
```
(or AEGIS / BLACKSITE-CO depending on config.yaml `app.name`)

---

## 7. AEGIS-Specific Verification

```sh
# Employer routes exist
curl -s -o /dev/null -w "%{http_code}" -H "Remote-User: dan" http://127.0.0.1:8102/employer
# Expected: 200 (dan is the single authorized user)

curl -s -o /dev/null -w "%{http_code}" -H "Remote-User: alice.chen" http://127.0.0.1:8102/employer
# Expected: 403 (greensite_guard blocks non-dan users)
```

---

## 8. Caddy Proxy

```
blacksite.borisov.network   → 127.0.0.1:8100 (Authelia + forward_auth)
greensite.borisov.network   → 127.0.0.1:8102 (Authelia + forward_auth)
blacksite-co.borisov.network → 127.0.0.1:8101
```

TLS: managed by Caddy ACME (Let's Encrypt / ZeroSSL). Verify cert:
```sh
echo | openssl s_client -connect blacksite.borisov.network:443 2>/dev/null | openssl x509 -noout -dates
```
