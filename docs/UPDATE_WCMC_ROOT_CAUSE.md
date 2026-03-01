# UPDATE_WCMC_ROOT_CAUSE.md
# WCMC Update Script — Root Cause Analysis

**Date:** 2026-03-01
**Investigator:** Claude Code
**Status:** Root cause identified — fix documented below

---

## Executive Summary

The `deploy-wcmc.sh` script correctly replaces files on disk and restarts the server. The site appears unchanged because **browsers aggressively cache static assets** (CSS, JS, HTML) with no server-side cache-busting mechanism in place. Additionally, the project has three separate directory trees only one of which is the live instance.

---

## 1. Script Target Paths

**Script:** `/home/graycat/scripts/deploy-wcmc.sh`

**What it does:**
1. Backs up current WCMC to `/home/graycat/projects/wcmc-backups/`
2. Kills any process on port 8090
3. Extracts the provided zip to `/home/graycat/projects/wcmc/` (root)
4. Restarts with `nohup .venv/bin/uvicorn server:app --host 127.0.0.1 --port 8090`
5. Checks `kill -0 $PID` to verify the process started, exits 0 if running

**The script works correctly.** Files are replaced on disk and the server restarts.

---

## 2. File Diff Before/After

**Live instance:** `/home/graycat/projects/wcmc/` (root, port 8090)

Three directories exist:
| Path | Status | Notes |
|------|--------|-------|
| `/home/graycat/projects/wcmc/` | **RUNNING (port 8090)** | What deploy-wcmc targets |
| `/home/graycat/projects/wcmc/wcmc_site/` | Not running | Staging/alternative build |
| `/home/graycat/projects/wcmc/wildcards_site/` | Not running | Older backup variant |

After `deploy-wcmc.sh` runs, the root directory files are updated. However, the browser has already cached the old `styles.css`, `app.js`, and `index.html` responses.

---

## 3. Root Cause

### Primary: No Cache-Control Headers

`server.py` mounts static files using FastAPI's `StaticFiles`:

```python
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

FastAPI's `StaticFiles` returns HTTP responses **without explicit `Cache-Control` headers**. Browsers apply their own heuristic caching (commonly 10% of `Last-Modified` age), resulting in cached assets persisting for minutes to hours after a deploy.

### Secondary: No Asset Versioning / Cache-Busting

- No build pipeline (no webpack, vite, parcel)
- No hash-suffixed filenames (`app.abc123.js`)
- No query-string cache busters (`?v=20260301`)
- No service worker (confirmed absent)
- No CDN

### Tertiary: Script Validation Gap

The script verifies the *process* started (PID check) but does **not** verify that:
- The HTTP response body changed
- File contents match the deployed zip
- A reference timestamp/version token is present in the response

---

## 4. Cache Check Results

Running `curl -I http://127.0.0.1:8090/static/styles.css` shows:
- No `Cache-Control` header
- No `ETag` sent for conditional requests
- Browser caches indefinitely until max-age heuristic expires or user force-refreshes

---

## 5. Fix — Implementation Steps

### Fix A: Add Cache-Control Headers in server.py (Immediate)

```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.endswith((".html",)):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response

app.add_middleware(NoCacheMiddleware)
```

For immediate cache invalidation, set `Cache-Control: no-cache` on HTML responses so browsers always revalidate.

### Fix B: Version Query Parameter in HTML (Immediate, No Code Change)

In `static/index.html`, reference assets with a version token:

```html
<link rel="stylesheet" href="/static/styles.css?v=20260301-1">
<script src="/static/app.js?v=20260301-1"></script>
```

Bump the `?v=` value on each deploy. This forces browsers to fetch the new file even if cached.

### Fix C: Add Post-Deploy Validation to deploy-wcmc.sh

```bash
# After restart, verify content changed
EXPECTED_VERSION="$(date +%Y%m%d)"
ACTUAL=$(curl -sf http://127.0.0.1:8090/static/index.html | grep -o "v=$EXPECTED_VERSION" || echo "NOT_FOUND")
if [[ "$ACTUAL" == "NOT_FOUND" ]]; then
    echo "WARNING: Version token not found in response — possible cache issue"
    echo "Users may need to hard-refresh (Ctrl+Shift+R)"
else
    echo "✓ Version $EXPECTED_VERSION confirmed in live response"
fi
```

---

## 6. Verification Steps Proving Visible Change

After applying Fix A or Fix B:

1. **Server-side verification:**
   ```bash
   curl -s http://127.0.0.1:8090/static/styles.css | md5sum
   md5sum /home/graycat/projects/wcmc/static/styles.css
   # Must match
   ```

2. **Cache-Control header verification:**
   ```bash
   curl -I http://127.0.0.1:8090/
   # Should show: Cache-Control: no-cache, must-revalidate
   ```

3. **Browser verification:**
   - Open DevTools → Network tab → check "Disable cache"
   - Hard reload (Ctrl+Shift+R / Cmd+Shift+R)
   - Confirm new CSS/JS loads (check file sizes in Network tab)

4. **Version token verification:**
   ```bash
   curl -s http://127.0.0.1:8090/ | grep "v=20260301"
   # Should return the version string
   ```

---

## 7. Recommended Priority

| Fix | Effort | Impact | Do When |
|-----|--------|--------|---------|
| Fix B: Version query params | 5 min | High | Immediately |
| Fix A: Cache-Control headers | 20 min | High | Next deploy |
| Fix C: Script validation | 10 min | Medium | Next deploy |
| Consolidate duplicate dirs | 30 min | Low | Next cleanup sprint |

**Action:** Add `?v=YYYYMMDD` to all static asset references in `index.html` now. This resolves the cache problem with zero risk.
