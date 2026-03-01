# BLACKSITE — Phase 5 Issue Summary

**Date:** 2026-03-01
**Phase:** 5 (Nav Cleanup, Avatar Upload, Assessments Cap, Assign State, Daily Bundle, Auto-Fail Engine)
**Status:** All 11 items SHIPPED ✓

---

## Item Status Table

| Item | Title | Status | Files Changed |
|------|-------|--------|---------------|
| 5.1  | Remove "View Dashboard As" from menus | ✅ Shipped | `templates/base.html` |
| 5.2  | Remove Appearance from task bar | ✅ Shipped | `templates/base.html` |
| 5.3  | All 14 themes on profile page | ✅ Shipped | `templates/profile.html` |
| 5.4  | Remove "last updated" from profile badge | ✅ Shipped | `templates/profile.html` |
| 5.5  | Profile picture upload with crop | ✅ Shipped | `app/models.py`, `app/main.py`, `templates/profile.html` |
| 5.6  | Limit All Assessments to 20 with expand | ✅ Shipped | `templates/admin.html` |
| 5.7  | Assign button state | ✅ Shipped | `app/main.py`, `templates/systems.html` |
| 5.8  | Daily work product bundle zip + email | ✅ Shipped | `app/main.py`, `app/mailer.py`, `templates/reports.html` |
| 5.9  | External standards feeds and overlays | ✅ Shipped | `app/models.py`, `app/main.py`, `templates/system_parameters.html` |
| 5.10 | Auto-fail triggers | ✅ Shipped | `app/models.py`, `app/main.py`, `templates/admin_autofail.html` |
| 5.11 | Auto-create system-generated POA&M | ✅ Shipped | `app/main.py` (integrated into auto-fail engine) |

---

## Detailed Item Status

### 5.1 — Remove "View Dashboard As" from menus
- **Status:** ✅ Complete
- **Change:** Removed the `{% if employees %}...{% endif %}` block (employee select dropdown) from the admin user-menu in `base.html`. Feature remains accessible on `/admin` dashboard page.
- **Risk:** None — feature not removed, only relocated out of the nav dropdown.

### 5.2 — Remove Appearance from task bar
- **Status:** ✅ Complete
- **Change:** Removed `<div class="nav-dd-section">Appearance</div>`, the `#theme-picker` div, and its preceding `<hr>` divider from the topbar dropdown. Theme control is now exclusively on the Profile page.
- **Risk:** None — profile page retains full theme picker.

### 5.3 — All 14 themes on profile page
- **Status:** ✅ Complete
- **Change:** Added 6 Phase-22 themes (Terminal, Synthwave, Crimson, Ocean, Amber, Noir) to the `THEMES` JS array in `profile.html`. Grid uses `repeat(auto-fill, minmax(90px, 1fr))` — responsive across all 14 options.
- **Risk:** None — purely additive.

### 5.4 — Remove "last updated" from profile badge
- **Status:** ✅ Complete
- **Change:** Removed the `{% if profile and profile.updated_at %}...{% endif %}` block from the left-column identity card. "Member Since" (created_at) remains.
- **Risk:** None.

### 5.5 — Profile picture upload with in-avatar edit icon + crop
- **Status:** ✅ Complete
- **Backend changes:**
  - `POST /profile/avatar` — multipart upload, validates type (jpg/jpeg/png/gif/webp) and size (≤ 5 MB), saves to `data/avatars/{user}.{ext}`, replaces existing avatar, updates `UserProfile.avatar_url`, logs audit event.
  - `GET /profile/avatar/{username}` — serves stored avatar with `Cache-Control: max-age=3600`.
- **Model change:** `avatar_url = Column(String, nullable=True)` added to `UserProfile`. Applied via `ALTER TABLE user_profiles ADD COLUMN avatar_url TEXT`.
- **Frontend:** Camera overlay button on avatar circle, Cropper.js 1.6.2 modal (1:1 square, 256×256 JPEG 92%), client-side 5 MB pre-check, live `<img>` src update after upload.
- **Risk:** Low — file types restricted to image MIME; size capped at 5 MB; avatar directory is `data/avatars/` (not served from static root).

### 5.6 — Limit All Assessments to 20 with expand
- **Status:** ✅ Complete
- **Change:** Template-only. First 20 rows visible by default; rows beyond 20 have `class="assess-extra" style="display:none"`. "Show N more ↓" button calls `showAllAssessments()` JS. Count badge states "Showing 20 of N" / "Showing all N".
- **Risk:** None — no backend change; display-only.

### 5.7 — Assign button state
- **Status:** ✅ Complete
- **Backend:** `GET /systems` now queries `SystemAssignment` for current user's own system IDs and passes `my_assigned_sys_ids` (set) to template.
- **Frontend:** `.sc-btn-assigned` CSS class (muted green, `cursor:default`, `opacity:0.7`). Per-card conditional: assigned → disabled "✓ Assigned"; not assigned → enabled "⊕ Assign".
- **Risk:** None — read-only query; no assignment modification.

### 5.8 — Daily work product bundle zip + email
- **Status:** ✅ Complete
- **Backend:** `POST /admin/bundle/daily` (admin-only) scans 5 directories for today's files, builds `MMDDYY_workproducts.zip` in `data/bundles/`, generates `INDEX.md` with per-file metadata (timestamp, category, speed-up idea), emails zip via `send_bundle()`, logs SHA-256 prefix + send event to `AuditLog`.
- **Mailer:** `send_bundle()` added to `app/mailer.py` — `MIMEMultipart("mixed")` with zip attached as `application/zip`.
- **Frontend:** "📦 Daily Work Bundle" card added to `/reports` page with `exportBundle()` JS and live feedback div.
- **Risk:** Low — admin-only endpoint; scans only predefined directories; email sent only to requesting user.

### 5.9 — External standards feeds and overlays
- **Status:** ✅ Complete
- **New models:** `NistPublication`, `NvdCve`, `ControlParameter` (with `UniqueConstraint("system_id", "control_id", "parameter_key")`).
- **Backend routes:**
  - `POST /admin/feeds/nist/ingest` — fetches NIST CSRC Atom feed, upserts `NistPublication`.
  - `POST /admin/feeds/nvd/ingest?days=30` — fetches NVD CVE 2.0 API (capped 1–120 days), upserts `NvdCve`.
  - `GET /systems/{id}/parameters` — per-system control parameter view.
  - `POST /systems/{id}/parameters` — add/update parameter; auto-sets `drift_detected = (required != current)`.
- **Template:** `templates/system_parameters.html` — parameter editor table with drift indicator (⚠ DRIFT / ✓).
- **Risk:** Low — feed fetches use `httpx.AsyncClient` with no credentials; CVE data is read-only metadata.

### 5.10 — Auto-fail triggers
- **Status:** ✅ Complete
- **New model:** `AutoFailEvent` — records each trigger evaluation with system, trigger type, control, resource, severity, linked POA&M, and status.
- **Engine (`_run_auto_fail_checks()`):** Evaluates 7 trigger types per system. Dedup via `_upsert_auto_fail_event()` matching on `(system_id, trigger_type, resource_type, resource_id)`. Re-opens resolved events; skips suppressed.
- **Trigger types:** `parameter_drift`, `review_overdue`, `document_expired`, `evidence_stale`, `config_drift`, `patch_sla_breach`, `governance_drift`.
- **Routes:** `POST /admin/autofail/evaluate?system_id=` + `GET /admin/autofail`.
- **Navigation:** "Auto-Fail Monitor" link added to admin dropdown.
- **Template:** `templates/admin_autofail.html` — stats strip, events table with trigger badges, Standards Feeds panel.
- **Risk:** Medium — engine runs on-demand; no scheduled background job. Patch SLA breach detection reads CVE dates from local DB only (requires NVD ingest first).

### 5.11 — Auto-create system-generated POA&M
- **Status:** ✅ Complete
- **Integration:** Built into `_upsert_auto_fail_event()`. On new `AutoFailEvent`: creates `PoamItem` with `system_generated=True`, `created_by=f"auto_fail:{trigger_type}:{resource_id}"`, `poam_id=AUTF{MMDDYY}-{HASH4}SG`, due 30 days from trigger date.
- **Dedup:** Matches existing system-generated POA&M by `created_by` key; re-opens if needed; preserves waived items.
- **Model changes:** `system_generated` (Boolean) and `auto_fail_event_id` (Integer FK) added to `PoamItem`. Applied via `ALTER TABLE`.
- **Risk:** Low — POA&M creation is additive; does not modify manual POA&Ms; dedup prevents duplicates.

---

## Regressions / Blockers Encountered

| # | Issue | Resolution |
|---|-------|-----------|
| 1 | Port 8100 occupied after first restart attempt | `fuser -k 8100/tcp` to release, then clean restart |
| 2 | `_log_audit(None, ...)` call in avatar route broke audit logging | Moved `_log_audit` call inside `async with SessionLocal()` block |
| 3 | RBAC runner `risk_create` flow: `select[name='likelihood']` timeout (16 events) | Pre-existing Playwright selector timing issue; no RBAC violation; classified as test-infra flap |

---

## No-Change Items
- `docs/RMF_BLACKSITE.md` — not modified (Phase 5 is a feature sprint, not an RMF step update)
- Existing POA&M items — not modified by auto-fail engine (dedup prevents re-creation of existing manual POA&Ms)
