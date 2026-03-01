# REPO_REMOTES.md — Repository Remote Configuration

Status: NOT STARTED — Repos do not yet exist on GitHub.
Target: Private GitHub repos under github.com/[user]

---

## Repos to Create

| Repo | Local Path | Contents | Branch Strategy |
|------|-----------|----------|----------------|
| `blacksite` | `/home/graycat/projects/blacksite/` | BLACKSITE GRC application | main (protected) |
| `compose-configs` | `/home/graycat/.docker/compose/` | Docker Compose + Caddy configs | main (protected) |
| `scripts` | `/home/graycat/scripts/` | Homelab automation scripts | main (protected) |

---

## Setup Commands (run after creating GitHub repos)

### BLACKSITE

```bash
cd /home/graycat/projects/blacksite
git init  # if not already a repo
git remote add origin git@github.com:[user]/blacksite.git
git add .
git commit -m "Initial commit — Phase 6 complete"
git branch -M main
git push -u origin main
```

### Compose configs

```bash
cd /home/graycat/.docker/compose
git init
# IMPORTANT: Add secrets exclusions first
cat > .gitignore << 'EOF'
.secrets.env
.arr-credentials.env
*.key
*.pem
*.crt
caddy/data/
caddy/config/
EOF
git remote add origin git@github.com:[user]/compose-configs.git
git add .
git commit -m "Initial commit — homelab compose configs"
git branch -M main
git push -u origin main
```

### Scripts

```bash
cd /home/graycat/scripts
git init
git remote add origin git@github.com:[user]/scripts.git
git add .
git commit -m "Initial commit — homelab scripts"
git branch -M main
git push -u origin main
```

---

## Branch Protections (set via GitHub UI after push)

For each repo → Settings → Branches → Branch protection rules → Add rule for `main`:
- [x] Require pull request reviews before merging (1 reviewer)
- [x] Require status checks to pass (if CI configured)
- [x] Require branches to be up to date
- [x] Restrict pushes (no direct pushes to main)
- [x] Require signed commits (optional but recommended)

---

## Sensitive File Exclusions

Files that MUST NOT be committed:
- `.secrets.env` (SOPS-encrypted secrets — even encrypted form should not be in GitHub)
- `.arr-credentials.env`
- `caddy/data/` (TLS certs)
- `*.key`, `*.pem`, `*.crt`
- `data/blacksite.db` (production database)
- `data/ssp_reviews/` (uploaded SSP files)
- `data/uploads/` (user uploads)

---

## Current State

No remotes configured. All repos are local-only.
Requires user action: create GitHub repos and run the setup commands above.
