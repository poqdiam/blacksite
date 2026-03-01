# BLACKSITE — CHANGELOG

## Phase 5 — 2026-03-01

### 5.1 Remove "View Dashboard As" from menus
- **File:** `templates/base.html`
- Removed `{% if employees %}...{% endif %}` block containing "View Dashboard As…" select dropdown from the admin user-menu dropdown.
- Feature remains accessible on the admin dashboard page (`/admin`).

### 5.2 Remove Appearance from task bar
- **File:** `templates/base.html`
- Removed "Appearance" section heading, theme-picker div, and its preceding divider from the topbar user-menu dropdown.
- Theme control is now exclusively on the Profile page.

### 5.3 All 14 themes on profile page
- **File:** `templates/profile.html`
- Added 6 Phase-22 themes to the `THEMES` JavaScript array in the Interface Theme section: Terminal, Synthwave, Crimson, Ocean, Amber, Noir.
- Profile theme grid now shows all 14 options via `repeat(auto-fill, minmax(90px, 1fr))` responsive grid.

### 5.4 Remove "last updated" from profile badge
- **File:** `templates/profile.html`
- Removed the `{% if profile and profile.updated_at %}...{% endif %}` block from the left-column identity card.
- "Member Since" (created_at) remains visible.

### 5.5 Profile picture upload with in-avatar edit icon + crop
- **Backend (`app/main.py`):**
  - `POST /profile/avatar` — accepts jpg/jpeg/png/gif/webp ≤ 5 MB; saves to `data/avatars/{user}.{ext}`; updates `UserProfile.avatar_url`; logs audit event.
  - `GET /profile/avatar/{username}` — serves stored avatar image with 1-hour cache header.
- **Database (`app/models.py`):** Added `avatar_url` column (`String, nullable`) to `UserProfile`.
- **Migration:** `ALTER TABLE user_profiles ADD COLUMN avatar_url TEXT` — applied.
- **Frontend (`templates/profile.html`):**
  - Avatar circle now shows `<img>` when `profile.avatar_url` is set; falls back to initials otherwise.
  - Camera icon overlay button (`.avatar-edit-btn`) positioned bottom-right inside `.avatar-wrap`.
  - Cropper.js 1.6.2 loaded from CDN (CORS + SRI integrity hash).
  - Crop modal: select file → Cropper.js 1:1 square crop → `toBlob()` → `POST /profile/avatar` → updates `<img>` src without page reload.
  - Client-side 5 MB size check before upload.

### 5.6 Limit All Assessments to 20 with expand
- **File:** `templates/admin.html`
- First 20 rows shown by default; rows beyond 20 are `display:none` with class `.assess-extra`.
- "Show N more ↓" button below table reveals all hidden rows via `showAllAssessments()` JS.
- Count badge shows "Showing 20 of N" / "Showing all N" states.

### 5.7 Assign button state
- **Backend (`app/main.py`):** `GET /systems` now queries `SystemAssignment` for the current user's own assignments and passes `my_assigned_sys_ids` (a set) to the template.
- **Frontend (`templates/systems.html`):**
  - `.sc-btn-assigned` CSS class added: muted green, `cursor:default`, `opacity:0.7`.
  - Per-card: if `sys.id in my_assigned_sys_ids`, button renders as `✓ Assigned` with `disabled` attribute; otherwise renders as `⊕ Assign` with `openAssignModal()` handler.

### 5.8 Daily work product bundle zip + email
- **Backend (`app/main.py`):**
  - `POST /admin/bundle/daily` — admin only; scans `results/`, `data/ssp_reviews/`, `data/uploads/poam_evidence/`, `data/ato_generated/`, `data/rbac-runs/` for files created today; builds `MMDDYY_workproducts.zip` in `data/bundles/`; generates `INDEX.md` with per-file metadata (timestamp, category, speed-up idea); emails zip to requesting user via `send_bundle()`; logs send event with SHA-256 prefix to `AuditLog`.
- **Mailer (`app/mailer.py`):** Added `send_bundle()` function — builds HTML email with file count + date, attaches zip as `application/zip`, sends via existing STARTTLS pipeline.
- **Frontend (`templates/reports.html`):** Added "📦 Daily Work Bundle" card below Regulatory References section with "Export Today's Bundle →" button and live feedback div.

### 5.9 External standards feeds and overlays
- **Database (`app/models.py`):** Added 3 new models:
  - `NistPublication` — NIST CSRC publication metadata (doc_id, title, series, pub_date, status, url, raw_json, last_fetched)
  - `NvdCve` — NVD CVE records (cve_id, description, cvss_score/vector/severity, affected_products JSON, published_date, modified_date, patched_date, raw_json, last_fetched)
  - `ControlParameter` — per-system control parameter tracking (system_id, control_id, parameter_key, required_value, current_value, source, drift_detected, last_checked, notes)
- **Backend (`app/main.py`):**
  - `POST /admin/feeds/nist/ingest` — fetches NIST CSRC Atom feed, upserts `NistPublication` records.
  - `POST /admin/feeds/nvd/ingest?days=30` — fetches NVD CVE 2.0 API, upserts `NvdCve` records; capped at `days` param (1–120).
  - `GET /systems/{id}/parameters` — view per-system control parameters.
  - `POST /systems/{id}/parameters` — add/update parameter record; sets `drift_detected = (required != current)`.
- **Template:** `templates/system_parameters.html` — tabular parameter editor with form; drift shown as ⚠ DRIFT badge.
- Draft guidance note: system respects `source` field (`nist_baseline|org_policy|ssp`); admin must manually promote parameter changes via the form before drift triggers fire.

### 5.10 Auto-fail triggers
- **Database (`app/models.py`):**
  - `AutoFailEvent` — records each trigger evaluation (system_id, trigger_type, control_id, resource_type, resource_id, title, details JSON, severity, poam_id FK, status, resolved_at)
  - `PoamItem` — added `system_generated` (Boolean) and `auto_fail_event_id` (Integer FK) columns.
- **Engine (`app/main.py`, `_run_auto_fail_checks()`):** Evaluates 7 trigger types per system:
  1. **parameter_drift** — `ControlParameter.drift_detected = True`
  2. **review_overdue** — `RmfRecord` with `target_date` in the past and status not complete
  3. **document_expired** — `AtoDocument` last updated > 365 days ago
  4. **evidence_stale** — `SystemControl` evidence last updated > 365 days ago
  5. **config_drift** — alias for parameter_drift (same underlying check)
  6. **patch_sla_breach** — `NvdCve` where CRITICAL (>15d) or HIGH (>30d) without `patched_date`
  7. **governance_drift** — new `SystemConnection` (last 30d) without corresponding CA-3 `ControlParameter` review record
- **Dedup logic:** `_upsert_auto_fail_event()` matches on `(system_id, trigger_type, resource_type, resource_id)`; re-opens resolved events; skips suppressed.

### 5.11 Auto-create system-generated POA&M
- Integrated into `_upsert_auto_fail_event()`.
- On new `AutoFailEvent`: creates a `PoamItem` with `system_generated=True`, `created_by=f"auto_fail:{trigger_type}:{resource_id}"`, `poam_id=AUTFMMDDYY-XXXXSG`, due 30 days from trigger date.
- Dedup: matches existing system-generated POA&M by `created_by` key; re-opens if needed (does not re-open waived items).
- Links `AutoFailEvent.poam_id` → created/found POA&M.
- **Backend (`app/main.py`):**
  - `POST /admin/autofail/evaluate?system_id=` — runs engine; returns event count + detail list.
  - `GET /admin/autofail` — views auto-fail events with trigger badges, severity, POA&M links; includes feed ingest buttons.
- **Navigation (`templates/base.html`):** Added "Auto-Fail Monitor" link to admin dropdown.
- **Template:** `templates/admin_autofail.html` — stats strip (total/open/resolved/critical-high), events table, feed ingest panel.

---

## Previous Phases
See prior session CHANGELOGs and `docs/RMF_BLACKSITE.md` for Phase 1–24 history.
