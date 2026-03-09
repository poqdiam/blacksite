#!/usr/bin/env python3
"""
BLACKSITE SOP Screenshot Capture Script
Captures UI screenshots for all Help Center SOPs at 2x device scale.
Saves to workflows/screenshots/ using naming convention:
  workflow-slug-step-##-short-label.png
"""
import os, sys, time, json
from pathlib import Path

BASE_URL   = "http://127.0.0.1:8100"
OUT_DIR    = Path(__file__).parent.parent / "workflows" / "screenshots"
SYSID      = "bsv-main-00000000-0000-0000-0000-000000000001"
PLAYWRIGHT_PATH = str(Path(__file__).parent.parent / ".playwright")

OUT_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_PATH

# ─── Helper ──────────────────────────────────────────────────────────────────

def url(path: str) -> str:
    return BASE_URL + path

def shot_path(slug: str, step: int, label: str) -> Path:
    fname = f"{slug}-step-{step:02d}-{label}.png"
    return OUT_DIR / fname

# ─── Capture specification ────────────────────────────────────────────────────
# Each entry: (slug, step_num, label, user, path, [pre_actions])
# pre_actions: list of (action_type, selector_or_value)
#   action_type: "fill", "click", "select", "wait", "scroll"

CAPTURES = [

  # ── 01 SESSION ──────────────────────────────────────────────────────────────
  ("session-auth", 1,  "no-header-401",        "NOAUTH", "/dashboard"),
  ("session-auth", 2,  "dashboard-redirect",   "dan",    "/"),
  ("session-auth", 3,  "health-endpoint",       "dan",    "/health"),
  ("session-auth", 4,  "session-timeout-toast", "alice.chen", "/dashboard"),
  ("session-auth", 5,  "logout-redirect",       "dan",    "/logout"),
  ("session-auth", 6,  "api-version",           "dan",    "/api/version"),

  # ── 02 DASHBOARD ────────────────────────────────────────────────────────────
  ("dashboard-access", 1, "admin-dashboard",       "dan",           "/dashboard"),
  ("dashboard-access", 2, "isso-dashboard",        "alice.chen",    "/dashboard"),
  ("dashboard-access", 3, "issm-dashboard",        "marcus.okafor", "/issm/dashboard"),
  ("dashboard-access", 4, "ciso-dashboard",        "priya.sharma",  "/ciso/dashboard"),   # priya=sca, no ciso dash
  ("dashboard-access", 5, "ao-decisions",          "dan",           "/ao/decisions"),
  ("dashboard-access", 6, "sca-dashboard",         "priya.sharma",  "/sca/dashboard"),
  ("dashboard-access", 7, "issm-daily-portfolio",  "marcus.okafor", "/issm/daily"),
  ("dashboard-access", 8, "system-owner-dash",     "derek.holloway", "/system-owner/dashboard"),
  ("dashboard-access", 9, "posture-dashboard",     "dan",           "/posture"),
  ("dashboard-access",10, "notifications-inbox",   "alice.chen",    "/notifications"),

  # ── 03 VIEW-AS AND ROLE SHELL ────────────────────────────────────────────────
  ("view-as-role-shell", 1, "admin-users-list",      "dan",  "/admin/users"),
  ("view-as-role-shell", 2, "view-as-banner",        "dan",  "/view-as/alice.chen"),
  ("view-as-role-shell", 3, "isso-view-dashboard",   "dan",  "/dashboard"),
  ("view-as-role-shell", 4, "exit-view-as",          "dan",  "/exit-view-as"),
  ("view-as-role-shell", 5, "switch-view-isso",      "alice.chen", "/switch-view"),
  ("view-as-role-shell", 6, "switch-role-view",      "dan",  "/switch-role-view"),
  ("view-as-role-shell", 7, "exit-shell",            "dan",  "/exit-shell"),

  # ── 04 SYSTEM LIFECYCLE ───────────────────────────────────────────────────────
  ("system-lifecycle", 1, "systems-list",            "dan",        "/systems"),
  ("system-lifecycle", 2, "new-system-form",         "dan",        "/systems/new"),
  ("system-lifecycle", 3, "system-detail-overview",  "dan",        f"/systems/{SYSID}"),
  ("system-lifecycle", 4, "system-edit-form",        "dan",        f"/systems/{SYSID}/edit"),
  ("system-lifecycle", 5, "system-assignments",      "dan",        f"/systems/{SYSID}/assignments"),
  ("system-lifecycle", 6, "archived-systems",        "dan",        "/admin/systems/archived"),
  ("system-lifecycle", 7, "system-report-print",     "alice.chen", f"/systems/{SYSID}/report"),

  # ── 05 SYSTEM DETAIL TABS ──────────────────────────────────────────────────
  ("system-detail-nav", 1, "system-overview-tab",    "alice.chen", f"/systems/{SYSID}"),
  ("system-detail-nav", 2, "controls-tab",           "alice.chen", f"/systems/{SYSID}/controls"),
  ("system-detail-nav", 3, "inventory-tab",          "alice.chen", f"/systems/{SYSID}/inventory"),
  ("system-detail-nav", 4, "connections-tab",        "alice.chen", f"/systems/{SYSID}/connections"),
  ("system-detail-nav", 5, "artifacts-tab",          "alice.chen", f"/systems/{SYSID}/artifacts"),
  ("system-detail-nav", 6, "teams-tab",              "alice.chen", f"/systems/{SYSID}/teams"),
  ("system-detail-nav", 7, "eis-assessment-tab",     "alice.chen", f"/systems/{SYSID}/eis-assessment"),
  ("system-detail-nav", 8, "parameters-tab",         "alice.chen", f"/systems/{SYSID}/parameters"),
  ("system-detail-nav", 9, "daily-ops-tab",          "alice.chen", f"/systems/{SYSID}/daily"),

  # ── 06 CONTROL CATALOG ────────────────────────────────────────────────────
  ("control-catalog", 1, "catalog-browse",            "alice.chen", "/controls"),
  ("control-catalog", 2, "control-detail-ac1",        "alice.chen", "/controls/ac-1"),
  ("control-catalog", 3, "control-detail-ac2",        "alice.chen", "/controls/ac-2"),
  ("control-catalog", 4, "system-controls-list",      "alice.chen", f"/systems/{SYSID}/controls"),
  ("control-catalog", 5, "system-control-workspace",  "alice.chen", f"/systems/{SYSID}/workspace/ac-1"),
  ("control-catalog", 6, "import-controls-page",      "alice.chen", f"/systems/{SYSID}/controls"),

  # ── 07 ASSESSMENT UPLOAD ───────────────────────────────────────────────────
  ("assessment-upload", 1, "upload-form",             "alice.chen", "/upload"),
  ("assessment-upload", 2, "admin-assessments-list",  "dan",        "/admin"),
  ("assessment-upload", 3, "sca-workspace",           "priya.sharma", "/sca/workspace"),
  ("assessment-upload", 4, "results-page",            "dan",        "/admin"),

  # ── 08 SSP AND OSCAL EXPORT ────────────────────────────────────────────────
  ("ssp-export", 1, "ssp-mode-select",               "alice.chen", "/admin"),
  ("ssp-export", 2, "admin-ssp-analyzer",            "dan",        "/admin/ssp"),
  ("ssp-export", 3, "ssp-review-detail",             "dan",        "/admin/ssp"),
  ("ssp-export", 4, "reports-center",                "dan",        "/reports"),

  # ── 09 POAM LIFECYCLE ─────────────────────────────────────────────────────
  ("poam-lifecycle", 1,  "poam-list-all",            "alice.chen", "/poam"),
  ("poam-lifecycle", 2,  "poam-new-form",            "alice.chen", "/poam/new"),
  ("poam-lifecycle", 3,  "poam-detail-draft",        "alice.chen", "/poam"),
  ("poam-lifecycle", 4,  "poam-import-page",         "alice.chen", "/poam/import"),
  ("poam-lifecycle", 5,  "poam-export-page",         "alice.chen", "/poam/export"),
  ("poam-lifecycle", 6,  "poam-status-open",         "alice.chen", "/poam"),
  ("poam-lifecycle", 7,  "poam-blocked-form",        "alice.chen", "/poam"),
  ("poam-lifecycle", 8,  "poam-ready-for-review",    "alice.chen", "/poam"),
  ("poam-lifecycle", 9,  "poam-closed-verified",     "alice.chen", "/poam"),
  ("poam-lifecycle", 10, "poam-deferred-waiver",     "alice.chen", "/poam"),
  ("poam-lifecycle", 11, "poam-accepted-risk",       "alice.chen", "/poam"),
  ("poam-lifecycle", 12, "poam-false-positive",      "alice.chen", "/poam"),

  # ── 10 POAM EVIDENCE ─────────────────────────────────────────────────────
  ("poam-evidence", 1, "poam-detail-evidence-section",  "alice.chen", "/poam"),
  ("poam-evidence", 2, "poam-detail-with-evidence",     "alice.chen", "/poam"),

  # ── 11 RISK REGISTER ────────────────────────────────────────────────────
  ("risk-register", 1, "risks-list",            "alice.chen", "/risks"),
  ("risk-register", 2, "risk-new-form",         "alice.chen", "/risks/new"),
  ("risk-register", 3, "risk-detail",           "alice.chen", "/risks"),
  ("risk-register", 4, "risks-export",          "alice.chen", "/risks/export"),

  # ── 12 OBSERVATIONS ────────────────────────────────────────────────────
  ("observations", 1, "observations-list",        "alice.chen", "/observations"),
  ("observations", 2, "observation-new-form",     "alice.chen", "/observations/new"),
  ("observations", 3, "observation-detail",       "alice.chen", "/observations"),
  ("observations", 4, "observation-promote",      "alice.chen", "/observations"),

  # ── 13 ATO DOCUMENTS ────────────────────────────────────────────────────
  ("ato-documents", 1, "ato-dashboard",              "dan",        "/ato"),
  ("ato-documents", 2, "ato-system-matrix",          "dan",        f"/ato/{SYSID}"),
  ("ato-documents", 3, "ato-doc-detail-ssp",         "dan",        f"/ato/{SYSID}/system_security_plan"),
  ("ato-documents", 4, "ato-doc-draft-form",         "dan",        f"/ato/{SYSID}/plan_of_action"),
  ("ato-documents", 5, "ato-doc-generate",           "dan",        f"/ato/{SYSID}/fips_199"),
  ("ato-documents", 6, "ato-doc-upload",             "dan",        f"/ato/{SYSID}/risk_assessment"),
  ("ato-documents", 7, "ato-doc-action-submit",      "alice.chen", f"/ato/{SYSID}/system_security_plan"),
  ("ato-documents", 8, "ato-doc-approved-status",    "dan",        f"/ato/{SYSID}/authorization_decision"),

  # ── 14 SUBMISSION AND AO DECISION ────────────────────────────────────────
  ("submission-ao", 1, "submission-form",            "alice.chen", f"/systems/{SYSID}/submit"),
  ("submission-ao", 2, "submissions-list",           "alice.chen", "/submissions"),
  ("submission-ao", 3, "submission-detail",          "alice.chen", "/submissions"),
  ("submission-ao", 4, "ao-decisions-list",          "dan",        "/ao/decisions"),
  ("submission-ao", 5, "ao-decision-form",           "dan",        "/ao/decisions"),
  ("submission-ao", 6, "auth-status-authorized",     "dan",        f"/systems/{SYSID}"),

  # ── 15 REPORTS AND EXPORTS ───────────────────────────────────────────────
  ("reports-exports", 1, "reports-center-main",      "dan",        "/reports"),
  ("reports-exports", 2, "system-report-print",      "alice.chen", f"/systems/{SYSID}/report"),
  ("reports-exports", 3, "system-reports-list",      "alice.chen", f"/systems/{SYSID}/reports"),
  ("reports-exports", 4, "poam-export",              "alice.chen", "/poam/export"),
  ("reports-exports", 5, "risks-export",             "alice.chen", "/risks/export"),
  ("reports-exports", 6, "audit-export",             "dan",        "/admin/audit"),

  # ── 16 USER MANAGEMENT ───────────────────────────────────────────────────
  ("user-management", 1, "admin-users-list",         "dan", "/admin/users"),
  ("user-management", 2, "add-user-form",            "dan", "/admin/users"),
  ("user-management", 3, "provision-form",           "dan", "/admin/users/provision"),
  ("user-management", 4, "user-freeze-confirm",      "dan", "/admin/users"),
  ("user-management", 5, "user-remove-confirm",      "dan", "/admin/users"),
  ("user-management", 6, "user-reservations",        "dan", "/admin/users/reservations"),
  ("user-management", 7, "shadow-users",             "dan", "/admin/users/shadow"),
  ("user-management", 8, "bulk-role-assign",         "dan", "/admin/users"),
  ("user-management", 9, "max-packages-setting",     "dan", "/issm/dashboard"),

  # ── 17 AUDIT LOG ─────────────────────────────────────────────────────────
  ("audit-log", 1, "audit-log-list",              "dan", "/admin/audit"),
  ("audit-log", 2, "audit-log-filter-user",       "dan", "/admin/audit"),
  ("audit-log", 3, "audit-log-export-link",       "dan", "/admin/audit"),

  # ── 18 SIEM SECURITY EVENTS ─────────────────────────────────────────────
  ("siem-events", 1, "siem-list",                "dan", "/admin/siem"),
  ("siem-events", 2, "siem-filter-severity",     "dan", "/admin/siem"),
  ("siem-events", 3, "siem-drilldown",           "dan", "/admin/siem"),

  # ── 19 BCDR WORKFLOW ────────────────────────────────────────────────────
  ("bcdr-workflow", 1, "bcdr-dashboard",             "dan",                  "/bcdr/dashboard"),
  ("bcdr-workflow", 2, "bcdr-create-event",          "samira.nazari",        "/bcdr/dashboard"),
  ("bcdr-workflow", 3, "bcdr-event-detail",          "samira.nazari",        "/bcdr/dashboard"),
  ("bcdr-workflow", 4, "bcdr-signoff",               "samira.nazari",        "/bcdr/dashboard"),
  ("bcdr-workflow", 5, "system-teams-page",          "alice.chen",           f"/systems/{SYSID}/teams"),

  # ── 20 DAILY OPS HUB ────────────────────────────────────────────────────
  ("daily-ops", 1, "daily-hub-isso",            "alice.chen",    f"/systems/{SYSID}/daily"),
  ("daily-ops", 2, "daily-save-form",           "alice.chen",    f"/systems/{SYSID}/daily"),
  ("daily-ops", 3, "daily-history",             "alice.chen",    f"/systems/{SYSID}/daily/history"),
  ("daily-ops", 4, "change-review-form",        "alice.chen",    f"/systems/{SYSID}/daily/change-review"),
  ("daily-ops", 5, "backup-check-form",         "alice.chen",    f"/systems/{SYSID}/daily/backup-check"),
  ("daily-ops", 6, "access-spotcheck-form",     "alice.chen",    f"/systems/{SYSID}/daily/access-spotcheck"),
  ("daily-ops", 7, "daily-hub-issm",            "marcus.okafor", f"/systems/{SYSID}/daily"),
  ("daily-ops", 8, "daily-hub-sca",             "priya.sharma",  f"/systems/{SYSID}/daily"),

  # ── 21 DEEP WORK ROTATION ────────────────────────────────────────────────
  ("deep-work-rotation", 1, "rotation-current-day",  "alice.chen", f"/systems/{SYSID}/rotation"),
  ("deep-work-rotation", 2, "rotation-history",      "alice.chen", f"/systems/{SYSID}/rotation/history"),
  ("deep-work-rotation", 3, "rotation-calendar",     "alice.chen", f"/systems/{SYSID}/rotation/calendar"),
  ("deep-work-rotation", 4, "rotation-complete-form","alice.chen", f"/systems/{SYSID}/rotation"),
  ("deep-work-rotation", 5, "issm-daily-portfolio",  "marcus.okafor", "/issm/daily"),

  # ── 22 COMPLIANCE RECORDS ───────────────────────────────────────────────
  ("compliance-records", 1, "vendors-list",           "alice.chen", f"/systems/{SYSID}/vendors"),
  ("compliance-records", 2, "interconnections-list",  "alice.chen", f"/systems/{SYSID}/interconnections"),
  ("compliance-records", 3, "dataflows-list",         "alice.chen", f"/systems/{SYSID}/dataflows"),
  ("compliance-records", 4, "privacy-assessments-list","alice.chen",f"/systems/{SYSID}/privacy-assessments"),
  ("compliance-records", 5, "restore-tests-list",     "alice.chen", f"/systems/{SYSID}/restore-tests"),

  # ── 23 EMPLOYEE QUIZ ────────────────────────────────────────────────────
  ("employee-quiz", 1, "quiz-dashboard-card",    "alice.chen", "/dashboard"),
  ("employee-quiz", 2, "quiz-page",              "alice.chen", "/dashboard/quiz"),
  ("employee-quiz", 3, "quiz-submit",            "alice.chen", "/dashboard/quiz"),
  ("employee-quiz", 4, "quiz-streak-result",     "alice.chen", "/dashboard"),

  # ── 24 PROFILE ───────────────────────────────────────────────────────────
  ("profile-preferences", 1, "profile-page",        "alice.chen", "/profile"),
  ("profile-preferences", 2, "profile-feeds",       "alice.chen", "/profile/feeds"),
  ("profile-preferences", 3, "theme-switcher",      "alice.chen", "/dashboard"),

  # ── 25 ADMIN SETTINGS ────────────────────────────────────────────────────
  ("admin-settings", 1, "system-settings-page",    "dan", "/admin/system-settings"),
  ("admin-settings", 2, "feed-sources-admin",       "dan", "/admin/feeds"),
  ("admin-settings", 3, "autofail-config",          "dan", "/admin/autofail"),
  ("admin-settings", 4, "data-ingest",              "dan", "/admin/ingest"),

  # ── 26 SEARCH ─────────────────────────────────────────────────────────────
  ("global-search", 1, "search-empty",             "alice.chen", "/search"),
  ("global-search", 2, "search-results",           "alice.chen", "/search?q=access"),
  ("global-search", 3, "search-suggest",           "alice.chen", "/search?q=ac-2"),

]

# ─── Run capture ─────────────────────────────────────────────────────────────

def capture_all():
    from playwright.sync_api import sync_playwright

    done = 0
    skipped = 0
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])

        # Cache pages per user to avoid redundant navigation
        contexts: dict = {}

        def get_context(user: str):
            if user not in contexts:
                ctx = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    device_scale_factor=2,
                )
                if user != "NOAUTH":
                    ctx.set_extra_http_headers({"Remote-User": user})
                contexts[user] = {"ctx": ctx, "page": ctx.new_page()}
            return contexts[user]["ctx"], contexts[user]["page"]

        for (slug, step, label, user, path) in CAPTURES:
            out_path = shot_path(slug, step, label)
            if out_path.exists():
                print(f"  [skip] {out_path.name}")
                skipped += 1
                continue

            try:
                _, page = get_context(user)
                full_url = url(path)
                page.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass  # networkidle timeout is OK
                time.sleep(0.3)
                page.screenshot(path=str(out_path), full_page=False)
                print(f"  [ok]   {out_path.name}  ({os.path.getsize(out_path)//1024}KB)")
                done += 1
            except Exception as e:
                err_msg = f"{slug}-step-{step:02d}: {e}"
                errors.append(err_msg)
                print(f"  [ERR]  {err_msg}")
                # Take a blank placeholder
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    img = Image.new("RGB", (1440, 900), color=(30, 30, 46))
                    draw = ImageDraw.Draw(img)
                    draw.text((20, 20), f"CAPTURE ERROR\n{slug} step {step}\n{label}\n{str(e)[:120]}",
                              fill=(200, 200, 200))
                    img.save(str(out_path))
                    print(f"         (saved placeholder)")
                except Exception:
                    pass

        for ctx_data in contexts.values():
            try:
                ctx_data["ctx"].close()
            except Exception:
                pass
        browser.close()

    print(f"\nCapture complete: {done} captured, {skipped} skipped, {len(errors)} errors")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")
    return errors

if __name__ == "__main__":
    print(f"Capturing {len(CAPTURES)} screenshots to {OUT_DIR}")
    capture_all()
    print("Done.")
