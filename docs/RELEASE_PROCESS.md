# RELEASE_PROCESS.md — BLACKSITE Release and Deployment Process

Version: 1.0 | Owner: dan | Updated: 2026-03-01

---

## Branch Strategy

| Branch | Purpose | Protected | Direct Push |
|--------|---------|-----------|-------------|
| `main` | Production | Yes | No |
| `dev` | Active development | No | Yes (graycat only) |
| `hotfix/*` | Emergency fixes | No | Yes (graycat only) |

---

## Release Flow

```
feature work on dev
  → all tests pass locally
  → bsv RBAC runner: exit code 0
  → PR: dev → main
  → code review
  → merge
  → restart services on borisov
  → smoke test
  → update RBAC_RUN_SUMMARY.md
```

---

## Pre-Release Checklist

- [ ] `bsv` (RBAC runner) exits 0 — no violations, no failures
- [ ] `curl http://127.0.0.1:8100/health` returns `{"status":"ok"}`
- [ ] `curl http://127.0.0.1:8100/api/version` returns expected sha
- [ ] BLACKSITE, BLACKSITE-CO, AEGIS all responding
- [ ] No ERROR-level entries in `journalctl -u blacksite --since "1h ago"`
- [ ] Templates render without Jinja2 errors on key routes
- [ ] DB migrations applied (check `init_db()` ran cleanly)

---

## Deployment Steps

```bash
# 1. Pull latest main
cd /home/graycat/projects/blacksite
git pull origin main

# 2. Restart services (requires sudo)
sudo systemctl restart blacksite.service
sudo systemctl restart blacksite-co.service
# AEGIS reads via symlink — same code, restart too:
sudo systemctl restart greensite.service

# 3. Verify
curl -s http://127.0.0.1:8100/api/version
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8102/api/version

# 4. Smoke test auth guard
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8102/employer  # → 403
curl -s -o /dev/null -w "%{http_code}" -H "Remote-User: dan" http://127.0.0.1:8102/employer  # → 200

# 5. Update RBAC_RUN_SUMMARY.md with run results
```

---

## Rollback

If deployment fails:
```bash
cd /home/graycat/projects/blacksite
git log --oneline -5  # find previous commit
git checkout <prev-sha> -- app/main.py app/models.py templates/
sudo systemctl restart blacksite.service
# Verify
curl -s http://127.0.0.1:8100/health
```

For DB schema rollback: SQLite migrations are additive (ADD COLUMN only). Column additions
cannot be rolled back without a full restore from backup. Restore from
`iapetus:clawd/backups/borisov/` if needed.

---

## Required Checks (future CI)

Once GitHub repos are set up, add these as required checks on the `main` branch:
1. RBAC regression runner (`bsv` exit code 0)
2. Python syntax check (`python3 -m py_compile app/main.py`)
3. Template lint (check for undefined variables)

---

## Accepted Operational Constraints

- No blue/green deployment (single server, single instance per port)
- Zero-downtime not guaranteed — service restarts take ~3 seconds
- Maintenance window: any time (not public-facing beyond Caddy/Authelia gate)
- Rollback RTO: ~5 minutes (git checkout + service restart)
