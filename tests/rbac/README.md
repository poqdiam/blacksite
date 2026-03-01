# BLACKSITE RBAC Regression Runner

Automated browser-driven RBAC regression test suite for the BLACKSITE GRC platform.
Tests all 13 system role lenses across 4 platform roles, running curated critical flows
and automatically-generated negative tests against the live application.

---

## 1. Overview and Purpose

The RBAC runner verifies that:

- Every role can access the pages and actions it is supposed to access (access correctness)
- No role can access pages or perform actions it is NOT supposed to (privilege violation detection)
- Role-specific dashboards, write guards, and the bsv_role_shell cookie all work as specified

The runner uses Playwright to drive a real Chromium browser session, authenticating
via Authelia (or local header injection in local-mode) and switching role lenses via
the `/switch-role-view` endpoint. Results are written as structured JSONL + JSON for
easy integration with monitoring and alerting.

---

## 2. Installation

```bash
# Activate the project venv
source /home/graycat/projects/blacksite/.venv/bin/activate

# Install playwright (if not already installed)
pip install playwright httpx pyyaml

# Install the Chromium browser binary
playwright install chromium

# Verify playwright is working
python -c "from playwright.async_api import async_playwright; print('playwright OK')"
```

---

## 3. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `BSV_TEST_USER` | `dan` | Authelia username (must be in `admin_users` in config.yaml) |
| `BSV_TEST_PASS` | _(empty)_ | Authelia password |
| `BSV_BASE_URL` | `http://127.0.0.1:8100` | App base URL |
| `BSV_AUTHELIA_URL` | `http://127.0.0.1:9091` | Authelia base URL |
| `BSV_LOCAL_MODE` | `0` | Set to `1` to skip Authelia and inject Remote-User header |
| `BSV_TELEGRAM_TOKEN` | _(from .env.rbac)_ | Telegram bot token for notifications |
| `BSV_TELEGRAM_CHAT_ID` | `2054649730` | Telegram chat ID |

Create `/home/graycat/projects/blacksite/.env.rbac`:
```
BSV_TEST_PASS=your_authelia_password
BSV_TELEGRAM_TOKEN=your_bot_token
```

---

## 4. Bootstrap Fixtures

Before the first run, create the test fixtures in the database:

```bash
cd /home/graycat/projects/blacksite
source .venv/bin/activate

# Create fixtures (idempotent — safe to re-run)
python -m tests.rbac.fixtures --db-path blacksite.db

# Or clean and recreate
python -m tests.rbac.fixtures --db-path blacksite.db --clean
```

This creates:
- 4 test users (bsv_test_principal, bsv_test_executive, bsv_test_manager, bsv_test_analyst)
- 3 test systems (BSV-TEST-ALPHA, BSV-TEST-BRAVO, BSV-TEST-CHARLIE)
- A test Risk, POAM item, and BCDR event on ALPHA
- ProgramRoleAssignments for all 13 system roles
- DutyAssignments for pen_tester and auditor (90-day expiry)
- Writes fixture IDs to `tests/rbac/config/fixtures.yaml`

---

## 5. Run Commands

```bash
cd /home/graycat/projects/blacksite
source .venv/bin/activate
export BSV_TEST_USER=dan
export BSV_LOCAL_MODE=1  # skip Authelia for local testing

# Basic run (all personas, all lenses)
python scripts/bsv_rbac_run

# Silent run (no Telegram notification, suppress info logs)
python scripts/bsv_rbac_run --silent

# Run with visible browser (for debugging)
python scripts/bsv_rbac_run --headed

# Test only one platform role
python scripts/bsv_rbac_run --role analyst

# Test only one lens
python scripts/bsv_rbac_run --lens isso

# Test only one persona + one lens (fast debug run)
python scripts/bsv_rbac_run --role principal --lens ao

# Skip negative tests
python scripts/bsv_rbac_run --no-negative

# Bootstrap fixtures then run
python scripts/bsv_rbac_run --bootstrap

# Detach into background
python scripts/bsv_rbac_run --silent --detach

# Custom base URL
python scripts/bsv_rbac_run --base-url http://127.0.0.1:8101
```

Exit codes:
- `0`: All checks passed
- `1`: Test failures (role denied access it should have)
- `2`: RBAC VIOLATIONS (role gained access it should NOT have) — treat as critical

---

## 6. Systemd Setup

```bash
# Install service and timer
sudo cp tests/rbac/systemd/bsv-rbac-runner.service /etc/systemd/system/
sudo cp tests/rbac/systemd/bsv-rbac-runner.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now bsv-rbac-runner.timer

# Check timer status
systemctl status bsv-rbac-runner.timer

# Run manually via systemd
sudo systemctl start bsv-rbac-runner.service

# View logs
journalctl -u bsv-rbac-runner.service -f
```

The timer runs nightly at 03:30 UTC with up to 5 minutes of random delay.

---

## 7. Output Artifacts

All artifacts are written to `data/rbac-runs/{RUN_ID}/`:

### run.jsonl — Step-level JSONL log

One JSON object per step, appended in real time. Schema:

```json
{
  "run_id": "RUN-20260228-033000",
  "platform_role": "principal",
  "lens": "ao",
  "flow_id": "ao_decision_approve",
  "flow_name": "AO Decision — approve a system",
  "step_id": "a1b2c3d4",
  "action": "submit",
  "url": "/ao/decisions/550e8400-...",
  "expected_status": 200,
  "observed_status": 200,
  "expected_text": "",
  "observed_text_snippet": "<!DOCTYPE html>...",
  "expect_deny": false,
  "passed": true,
  "violation": false,
  "failure": false,
  "duration_ms": 312.5,
  "error": "",
  "screenshot_path": "",
  "snapshot_path": "",
  "timestamp": "2026-02-28T03:31:15+00:00"
}
```

### summary.json — Run-level aggregate

```json
{
  "run_id": "RUN-20260228-033000",
  "started_at": "...",
  "finished_at": "...",
  "elapsed_s": 142.3,
  "totals": {
    "flows": 48,
    "flows_passed": 48,
    "flows_failed": 0,
    "steps": 312,
    "steps_passed": 312,
    "steps_failed": 0,
    "violations": 0,
    "failures": 0
  },
  "top_5_violations": [],
  "top_5_failures": [],
  "all_violations": [],
  "all_failures": []
}
```

### screenshots/ — Failure/violation artifacts

- `{role}_{lens}_{step_id}.png` — full-page screenshot
- `{role}_{lens}_{step_id}.html` — complete HTML snapshot

### discovered_flows.json — Auto-discovered nav flows

One entry per nav link discovered from the rendered sidebar, keyed by flow ID.

---

## 8. Violations vs Failures

| Term | Meaning | Severity |
|---|---|---|
| **Violation** | A role accessed a resource it should NOT be able to (403 expected, got 200) | CRITICAL — RBAC enforcement broken |
| **Failure** | A role was denied a resource it SHOULD be able to access (200 expected, got 403) | Warning — access misconfiguration or test data issue |

Violations are RBAC security bugs. Failures may indicate test data problems (missing fixtures)
or legitimate over-restriction. Always investigate violations first.

Exit code `2` is reserved for violations to allow automated monitoring to distinguish them
from ordinary failures.

---

## 9. Adding New Flows to curated_flows.yaml

Each flow in `tests/rbac/config/curated_flows.yaml` has this structure:

```yaml
- id: my_new_flow              # unique snake_case ID
  name: "Human readable name"
  allowed_lenses: [ao, ciso]   # lenses that SHOULD succeed
  denied_lenses: [pen_tester]  # lenses that SHOULD get 403
  steps:
    - action: navigate
      url: /some/path
      expected_status: 200
      expected_text: "Expected text"   # optional substring check

    - action: submit             # POST with form data
      url: /some/path
      value: "field1=val1&field2=val2"
      expected_status: 200
      expect_deny: false
```

Supported step actions:
- `navigate` — GET the URL, check status and optional text
- `submit` — POST to the URL with `value` as URL-encoded form body
- `fill` — Fill a form field (selector + value)
- `select` — Select a dropdown option (selector + value)
- `click` — Click an element (selector)
- `upload` — File upload (currently verifies form access, not actual upload)
- `assert_text` — Navigate and assert text present
- `assert_status` — Navigate and assert HTTP status code

URL tokens substituted at runtime:
- `{SYSTEM_ID}` — BSV-TEST-ALPHA system ID
- `{SYSTEM_B}` — BSV-TEST-BRAVO system ID
- `{RISK_ID}` — Test risk ID
- `{POAM_ID}` — Test POAM item ID
- `{BCDR_ID}` — Test BCDR event ID
- `{RUN_ID}` — Current run ID (for unique naming)

---

## 10. Repo Contract

To keep the RBAC runner accurate, the BLACKSITE codebase should maintain these conventions:

### data-testid attributes

Add `data-testid="..."` attributes to critical interactive elements to make selectors
more stable than CSS class selectors:

```html
<button data-testid="ao-approve-btn">Approve</button>
<select data-testid="poam-status-select" name="status">...</select>
```

### Role gate requirements

All write routes MUST call `_require_role(role, [...])` with the explicit allowed list.
Read routes that restrict access to specific roles must also call `_require_role`.

Routes without any `_require_role` call are treated as "universally accessible to all
authenticated users" by the static analysis. If a route should be restricted, add the call.

### HMAC cookie contract

The `bsv_role_shell` cookie value format is `{role}.{hmac20hex}` where the HMAC is
computed over the role string using the app secret from `data/.app_secret`.
The runner uses `/switch-role-view?role=<value>` to set this cookie via the app,
which ensures the HMAC is always computed server-side.

Do not change the cookie name, path, or signing scheme without updating:
- `tests/rbac/personas.py` — `VALID_SHELL_ROLES` and `lens_to_shell_value()`
- `tests/rbac/config/roles.yaml` — `valid_shell_roles` and `shell_cookie_aliases`
