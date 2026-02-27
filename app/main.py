"""
BLACKSITE — FastAPI application entry point.

Routes:
  GET  /                            Redirect → /admin (admin) or /dashboard (employee)
  GET  /upload                      Upload form
  POST /upload                      Accept SSP file + candidate name
  GET  /status/{id}                 Status/polling page
  GET  /api/status/{id}             JSON status poll
  GET  /results/{id}                Full report (proctor view)
  POST /results/{id}/proctor        Save proctor note for a control
  POST /results/{id}/link-system    Link assessment to a system
  GET  /quiz/{id}                   Assessment quiz (standalone)
  POST /quiz/{id}/submit            Submit assessment quiz
  GET  /admin                       Admin management dashboard (admin only)
  GET  /admin/view-as/{username}    Admin — view employee dashboard as that user
  GET  /admin/download/{id}/json    Download assessment as JSON
  GET  /admin/download/{id}/original Download original uploaded file
  GET  /admin/download/{id}/print   Printable HTML report
  POST /admin/forward/{id}          Forward assessment to employee via email
  GET  /admin/audit                 Audit log (admin only, last 200 entries)
  GET  /dashboard                   Employee personal dashboard
  GET  /switch-view?mode=admin|employee  Toggle admin/employee view (admin only, sets bsv_mode cookie)
  GET  /logout                      Redirect to Authelia logout
  GET  /dashboard/quiz              Take today's daily quiz
  POST /dashboard/quiz/submit       Submit daily quiz
  GET  /profile                     View/edit user profile
  POST /profile                     Save profile changes
  GET  /systems                     System catalog list
  GET  /systems/new                 Create system form
  POST /systems                     Create system
  GET  /systems/{id}                System detail (info + assessments + POA&Ms + risks)
  GET  /systems/{id}/edit           Edit system form
  POST /systems/{id}/edit           Update system
  POST /systems/{id}/delete         Delete system (admin only)
  POST /systems/{id}/assign         Assign employee to system (admin only)
  POST /systems/{id}/unassign       Remove employee assignment (admin only)
  GET  /systems/{id}/assignments    List current assignments (admin only, JSON)
  POST /results/{id}/controls/{ctrl}/edit  Edit a control field (assigned user or admin)
  GET  /poam                        POA&M dashboard
  GET  /poam/import                 CSV bulk import form
  POST /poam/import                 Parse + insert from CSV
  GET  /poam/import/template        Download blank CSV template
  GET  /poam/new                    Create POA&M item form
  POST /poam                        Create POA&M item
  GET  /poam/{id}                   POA&M item detail + edit
  POST /poam/{id}/update            Update POA&M item
  POST /poam/auto/{assessment_id}   Auto-create POA&M from failing controls
  GET  /poam/export                 Printable POA&M table
  GET  /risks                       Risk register dashboard
  GET  /risks/new                   Create risk form
  POST /risks                       Create risk
  GET  /risks/{id}                  Risk detail + edit
  POST /risks/{id}/update           Update risk
  GET  /risks/export                Printable risk register
  GET  /ssp/{assessment_id}         Generated SSP document (HTML, print-to-PDF)
  GET  /ssp/{assessment_id}/oscal   OSCAL-format JSON export
  POST /api/review/{assessment_id}  Trigger rule-based analysis
  POST /api/update-controls         Trigger NIST catalog update
  GET  /health                      Health check

  ── Phase 5 — Full GRC Package ──────────────────────────────────────────────
  GET  /controls                    NIST 800-53r5 control catalog browser
  GET  /controls/{ctrl_id}          Single control detail
  GET  /systems/{id}/controls       System control plan (per-system implementation tracker)
  POST /systems/{id}/controls/{ctrl_id}  Update system control record
  POST /systems/{id}/import-controls    Bulk-import control status from latest assessment
  GET  /systems/{id}/report         Printable compliance report (PDF-ready)
  GET  /systems/{id}/submit         ATO submission form
  POST /systems/{id}/submit         Create ATO submission
  GET  /submissions                 All submissions list (admin)
  GET  /submissions/{id}            Submission detail
  POST /submissions/{id}/update     Update submission status/decision
"""

from __future__ import annotations

import asyncio
import json
import logging
import csv
import io
import os
import random
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Optional, Dict, List

import aiofiles
import yaml
from fastapi import (
    BackgroundTasks, FastAPI, File, Form, HTTPException,
    Request, UploadFile
)
from fastapi.responses import (
    FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, update, text, case as sa_case

from app.models import (
    Assessment, Candidate, ControlResult, ControlsMeta, DailyQuizActivity, QuizResponse,
    System, PoamItem, Risk, UserProfile, AuditLog, SystemAssignment, ControlEdit,
    SystemControl, Submission, RmfRecord,
    AtoDocument, AtoDocumentVersion, AtoWorkflowEvent,
    init_db, make_engine, make_session_factory
)
from app.updater    import load_catalog, update_if_needed
from app.parser     import parse_ssp
from app.assessor   import run_assessment, compute_combined_score, is_allstar
from app.quiz       import QUESTIONS, grade_quiz, grade_daily_quiz
from app.mailer     import send_report, forward_assessment
from app.remediation import get_remediation
from app.scorer     import analyze_assessment, compute_risk_level, compute_overall_impact

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s"
)
log = logging.getLogger("blacksite")

# ── Load config ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        with open(cfg_path) as f:
            return yaml.safe_load(f) or {}
    return {}

CONFIG = load_config()

# ── App factory ────────────────────────────────────────────────────────────────

engine       = make_engine(CONFIG)
SessionLocal = make_session_factory(engine)
templates    = Jinja2Templates(directory="templates")
templates.env.filters["fromjson"] = lambda s: (json.loads(s) if s else {})

CATALOG: dict = {}

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global CATALOG
    await init_db(engine)
    for d in ["uploads", "results", "controls", "static"]:
        Path(d).mkdir(exist_ok=True)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, update_if_needed, CONFIG)
        CATALOG = await loop.run_in_executor(None, load_catalog, CONFIG)
        log.info("NIST catalog loaded: %d controls.", len(CATALOG))
    except Exception as e:
        log.warning("Could not load NIST catalog at startup: %s", e)
        CATALOG = {}
    yield
    await engine.dispose()


app = FastAPI(title="BLACKSITE", lifespan=lifespan)

if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Security headers middleware ─────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add defensive HTTP security headers to every response."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Skip static asset routes (no need for HTML security headers on CSS/JS/images)
        path = request.url.path
        if path.startswith("/static/"):
            return response
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # CSP: self-only, allow Chart.js CDN, inline styles for our design system
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cfg(key: str, default=None):
    keys = key.split(".")
    val  = CONFIG
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, default)
        else:
            return default
    return val


def _is_admin(request: Request) -> bool:
    user = request.headers.get("Remote-User", "")
    return bool(user) and user in set(CONFIG.get("app", {}).get("admin_users", ["dan"]))


def _view_mode(request: Request) -> str:
    """Return 'employee' or 'admin' for the current session.
    Only admins can be in employee mode (via bsv_mode cookie).
    Regular employees always get 'employee'.
    """
    if not _is_admin(request):
        return "employee"
    return request.cookies.get("bsv_mode", "admin")


def _tpl_ctx(request: Request) -> dict:
    """Common template context included in every page render."""
    user = request.headers.get("Remote-User", "")
    employees = CONFIG.get("employees", [])
    # Best-effort display name: check employees config first, then title-case username
    emp_map = {e.get("username"): e.get("name") for e in employees if e.get("username")}
    display_name = emp_map.get(user) or (user.replace(".", " ").title() if user else "")
    return {
        "app_name":    _cfg("app.name", "BLACKSITE"),
        "brand":       _cfg("app.brand", "TheKramerica"),
        "tagline":     _cfg("app.tagline", "Security Assessment Platform"),
        "remote_user": user,
        "display_name": display_name,
        "is_admin":    _is_admin(request),
        "view_mode":   _view_mode(request),
        "employees":   employees,
    }


async def _get_assessment(assessment_id: str, session) -> Assessment:
    result = await session.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return obj


async def _get_candidate(candidate_id: str, session) -> Candidate:
    result = await session.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    return result.scalar_one_or_none()


async def _log_audit(session, remote_user: str, action: str,
                     resource_type: str, resource_id: str, details: dict = None):
    """Write an audit log entry."""
    entry = AuditLog(
        remote_user   = remote_user,
        action        = action,
        resource_type = resource_type,
        resource_id   = str(resource_id),
        details       = json.dumps(details or {}, default=str),
    )
    session.add(entry)


async def _can_access_system(system_id: str, request: Request, session) -> bool:
    """Returns True if user is admin OR is assigned to this system."""
    if _is_admin(request):
        return True
    user = request.headers.get("Remote-User", "")
    result = await session.execute(
        select(SystemAssignment)
        .where(SystemAssignment.system_id == system_id)
        .where(SystemAssignment.remote_user == user)
    )
    return result.scalar_one_or_none() is not None


async def _user_system_ids(request: Request, session) -> list:
    """Returns list of system_ids the current user can access."""
    if _is_admin(request):
        result = await session.execute(select(System.id))
        return [r[0] for r in result.all()]
    user = request.headers.get("Remote-User", "")
    result = await session.execute(
        select(SystemAssignment.system_id)
        .where(SystemAssignment.remote_user == user)
    )
    return [r[0] for r in result.all()]


async def _get_user_role(request: Request, session) -> str:
    """Return the RBAC role string for the current user."""
    if _is_admin(request):
        return "admin"
    user = request.headers.get("Remote-User", "")
    if not user:
        return "anonymous"
    row = (await session.execute(
        select(UserProfile.role).where(UserProfile.remote_user == user)
    )).scalar_one_or_none()
    return row or "employee"


def _require_role(role: str, allowed: list):
    """Raise 403 if role not in allowed list."""
    if role not in allowed:
        raise HTTPException(status_code=403, detail=f"Role '{role}' cannot access this resource")


async def _full_ctx(request: Request, session, **extra) -> dict:
    """Extended template context including user_role for sidebar rendering."""
    role = await _get_user_role(request, session)
    return {**_tpl_ctx(request), "user_role": role, **extra}


# ── RMF step definitions ────────────────────────────────────────────────────────

RMF_STEPS = [
    {
        "key": "prepare",
        "num": 1,
        "title": "Prepare",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.1",
        "desc": "Establish organization- and system-level context to manage security and privacy risk.",
        "activities": [
            "Identify key roles (Risk Executive, AO, ISSO, ISSM)",
            "Define risk management strategy and risk tolerance",
            "Identify common controls and control inheritance",
            "Conduct organizational risk assessment",
        ],
        "app_link": "/systems",
        "app_label": "System Catalog",
    },
    {
        "key": "categorize",
        "num": 2,
        "title": "Categorize",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.2 / FIPS 199",
        "desc": "Categorize the system and information processed based on FIPS 199 impact levels.",
        "activities": [
            "Identify system types and information types",
            "Determine confidentiality, integrity, availability impact levels",
            "Assign overall system categorization (Low/Moderate/High)",
            "Document categorization in the System Security Plan",
        ],
        "app_link": "/systems",
        "app_label": "Impact Levels",
    },
    {
        "key": "select",
        "num": 3,
        "title": "Select",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.3 / SP 800-53",
        "desc": "Select, tailor, and document the controls that will protect the system.",
        "activities": [
            "Select baseline controls (Low/Moderate/High from SP 800-53)",
            "Apply overlays and tailoring guidance",
            "Identify control inheritance from common control providers",
            "Document control selection in the SSP",
        ],
        "app_link": "/controls",
        "app_label": "Control Catalog",
    },
    {
        "key": "implement",
        "num": 4,
        "title": "Implement",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.4",
        "desc": "Implement the controls and document implementation details.",
        "activities": [
            "Implement selected controls in the system",
            "Document implementation narratives in the SSP",
            "Apply configuration baselines and hardening guides",
            "Address planned implementations and timelines",
        ],
        "app_link": "/systems/{system_id}/controls",
        "app_label": "System Control Plan",
    },
    {
        "key": "assess",
        "num": 5,
        "title": "Assess",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.5 / SP 800-53A",
        "desc": "Assess controls to determine if implemented correctly and operating as intended.",
        "activities": [
            "Develop Security Assessment Plan (SAP)",
            "Conduct assessment using SP 800-53A procedures",
            "Produce Security Assessment Report (SAR)",
            "Identify weaknesses and deficiencies",
        ],
        "app_link": "/poam",
        "app_label": "POA&M Tracker",
    },
    {
        "key": "authorize",
        "num": 6,
        "title": "Authorize",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.6",
        "desc": "Authorizing Official reviews risk and makes an authorization decision.",
        "activities": [
            "Compile authorization package (SSP, SAR, POA&M)",
            "Conduct risk determination and acceptance",
            "Issue Authorization to Operate (ATO) or denial",
            "Document authorization decision and conditions",
        ],
        "app_link": "/submissions",
        "app_label": "ATO Submissions",
    },
    {
        "key": "monitor",
        "num": 7,
        "title": "Monitor",
        "nist_ref": "NIST SP 800-37 Rev 2, §2.7 / SP 800-137",
        "desc": "Continuously monitor controls and system security posture.",
        "activities": [
            "Implement continuous monitoring strategy",
            "Monitor security controls on an ongoing basis",
            "Report security status to authorizing official",
            "Conduct ongoing risk response and remediation",
        ],
        "app_link": "/posture",
        "app_label": "Compliance Posture",
    },
]

# Status ordering for progress calculation
_RMF_STEP_KEYS = [s["key"] for s in RMF_STEPS]

# ── ATO Document Types ──────────────────────────────────────────────────────────
# owner_roles: who drafts/edits; reviewer_roles: who approves
ATO_DOC_TYPES: dict = {
    "FIPS199":     {"name": "FIPS 199 — System Categorization",      "short": "FIPS 199",    "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "categorize"},
    "SSP":         {"name": "System Security Plan",                   "short": "SSP",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "select"},
    "SAP":         {"name": "Security Assessment Plan",               "short": "SAP",         "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess"},
    "SAR":         {"name": "Security Assessment Report",             "short": "SAR",         "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess"},
    "POAM":        {"name": "Plan of Action & Milestones",            "short": "POA\u0026M",  "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor"},
    "ABD":         {"name": "Authorization Boundary Diagram",         "short": "ABD",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "categorize"},
    "NET_DIAGRAM": {"name": "Network Diagrams",                       "short": "Net Diag.",   "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "categorize"},
    "HW_INV":      {"name": "Hardware Inventory",                     "short": "HW Inv.",     "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement"},
    "SW_INV":      {"name": "Software Inventory",                     "short": "SW Inv.",     "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement"},
    "IRP":         {"name": "Incident Response Plan",                 "short": "IRP",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor"},
    "CP":          {"name": "Contingency Plan",                       "short": "CP",          "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement"},
    "CPT":         {"name": "Contingency Plan Test",                  "short": "CPT",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor"},
    "CMP":         {"name": "Configuration Management Plan",          "short": "CMP",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement"},
    "CONMON":      {"name": "Continuous Monitoring Plan",             "short": "ConMon",      "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor"},
    "PTA":         {"name": "Privacy Threshold Analysis",             "short": "PTA",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "categorize"},
    "PIA":         {"name": "Privacy Impact Assessment",              "short": "PIA",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "categorize"},
    "ROB":         {"name": "Rules of Behavior",                      "short": "RoB",         "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement"},
    "ISA":         {"name": "Interconnection Security Agreement",     "short": "ISA/MOU",     "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement"},
    "ADD":         {"name": "Authorization Decision Document",        "short": "ADD/ATO",     "owner_roles": ["admin"],               "reviewer_roles": ["admin"],              "rmf_step": "authorize"},
}
_ATO_DOC_KEYS = list(ATO_DOC_TYPES.keys())

# ── Ticker cache ────────────────────────────────────────────────────────────────

_ticker_cache: dict = {"ts": 0.0, "items": [], "count": 0}


# ── Background: process SSP ────────────────────────────────────────────────────

async def _process_ssp(assessment_id: str, file_path: str):
    """Parse + assess SSP against ALL catalog controls. Runs in background."""
    global CATALOG

    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)
        try:
            loop = asyncio.get_event_loop()

            try:
                parsed = await loop.run_in_executor(None, parse_ssp, Path(file_path))
            except ValueError as ve:
                log.warning("SSP parse abandoned: %s", ve)
                asmt.status        = "error"
                asmt.error_message = str(ve)
                await session.commit()
                return

            if not CATALOG:
                CATALOG = await loop.run_in_executor(None, load_catalog, CONFIG)

            summary = await loop.run_in_executor(
                None, run_assessment, CATALOG, parsed, True
            )

            for r in summary["results"]:
                cr = ControlResult(
                    assessment_id         = assessment_id,
                    control_id            = r["control_id"],
                    control_family        = r["control_family"],
                    control_title         = r["control_title"],
                    found_in_ssp          = r["found_in_ssp"],
                    is_na                 = r.get("is_na", False),
                    implementation_status = r.get("implementation_status"),
                    responsible_role      = r.get("responsible_role"),
                    narrative_excerpt     = r.get("narrative_excerpt", "")[:500],
                    ai_score              = r["score"],
                    ai_grade              = r["grade"],
                    ai_issues             = "|".join(r.get("issues", [])),
                    ai_elements_covered   = r.get("elements_covered", ""),
                )
                session.add(cr)

            asmt.status                  = "complete"
            asmt.total_controls_found    = summary["controls_in_ssp"]
            asmt.controls_complete       = summary["controls_complete"]
            asmt.controls_partial        = summary["controls_partial"]
            asmt.controls_insufficient   = summary["controls_insufficient"]
            asmt.controls_not_found      = summary["controls_not_found"]
            asmt.ssp_score               = summary["ssp_score"]
            await session.commit()
            log.info(
                "Assessment %s complete — SSP score: %.1f  "
                "(%d complete, %d partial, %d insufficient, %d not_found, %d na)",
                assessment_id, summary["ssp_score"],
                summary["controls_complete"], summary["controls_partial"],
                summary["controls_insufficient"], summary["controls_not_found"],
                summary.get("controls_na", 0),
            )

        except Exception as e:
            log.exception("Assessment %s failed: %s", assessment_id, e)
            asmt.status        = "error"
            asmt.error_message = str(e)
            await session.commit()


# ── Root redirect ──────────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized — Authelia authentication required")
    if _is_admin(request):
        if _view_mode(request) == "employee":
            return RedirectResponse(url="/dashboard", status_code=302)
        return RedirectResponse(url="/admin", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)


# ── Logout ─────────────────────────────────────────────────────────────────────

@app.get("/logout")
async def logout():
    url = _cfg("app.authelia_logout_url", "https://auth.borisov.network/logout")
    return RedirectResponse(url=url, status_code=302)


# ── View mode toggle (admin only) ──────────────────────────────────────────────

@app.get("/switch-view")
async def switch_view(request: Request, mode: str = "admin"):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin only")
    if mode not in ("admin", "employee"):
        mode = "admin"
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("bsv_mode", mode, max_age=86400 * 30, httponly=True, samesite="lax")
    return response


# ── Upload ─────────────────────────────────────────────────────────────────────

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="SSP upload is restricted to administrators")
    return templates.TemplateResponse("index.html", {
        "request": request,
        **_tpl_ctx(request),
    })


@app.post("/upload")
async def upload(
    request:          Request,
    background_tasks: BackgroundTasks,
    name:             str        = Form(...),
    email:            str        = Form(""),
    file:             UploadFile = File(...),
):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="SSP upload is restricted to administrators")
    allowed = {".docx", ".pdf", ".txt", ".xlsx", ".csv"}
    suffix  = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(allowed)}")

    submitted_by = request.headers.get("Remote-User", "")

    uploads_dir = Path(_cfg("storage.uploads_dir", "uploads"))
    uploads_dir.mkdir(exist_ok=True)
    save_name = f"{uuid.uuid4()}{suffix}"
    save_path = uploads_dir / save_name

    async with aiofiles.open(save_path, "wb") as out:
        while chunk := await file.read(65536):
            await out.write(chunk)

    async with SessionLocal() as session:
        candidate = Candidate(name=name, email=email or None)
        session.add(candidate)
        await session.flush()
        asmt = Assessment(
            candidate_id = candidate.id,
            filename     = file.filename,
            file_path    = str(save_path),
            submitted_by = submitted_by,
        )
        session.add(asmt)
        await _log_audit(session, submitted_by, "CREATE", "assessment", asmt.id,
                         {"filename": file.filename, "candidate": name})
        await session.commit()
        assessment_id = asmt.id

    background_tasks.add_task(_process_ssp, assessment_id, str(save_path))
    return RedirectResponse(url=f"/status/{assessment_id}", status_code=303)


# ── Status ─────────────────────────────────────────────────────────────────────

@app.get("/status/{assessment_id}", response_class=HTMLResponse)
async def status_page(request: Request, assessment_id: str):
    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)
    return templates.TemplateResponse("status.html", {
        "request":        request,
        "assessment_id":  assessment_id,
        "status":         asmt.status,
        "filename":       asmt.filename,
        "candidate_name": candidate.name if candidate else "Unknown",
        "error":          asmt.error_message or "",
        **_tpl_ctx(request),
    })


@app.get("/api/status/{assessment_id}")
async def status_api(assessment_id: str):
    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)
    return {
        "status":    asmt.status,
        "ssp_score": asmt.ssp_score,
        "error":     asmt.error_message,
    }


# ── Results ────────────────────────────────────────────────────────────────────

@app.get("/results/{assessment_id}", response_class=HTMLResponse)
async def results_page(request: Request, assessment_id: str):
    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)

        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .order_by(ControlResult.control_family, ControlResult.control_id)
        )
        controls = ctrl_rows.scalars().all()

        quiz_rows = await session.execute(
            select(QuizResponse).where(QuizResponse.assessment_id == assessment_id)
        )
        quiz_responses_db = {r.question_id: r for r in quiz_rows.scalars().all()}

        meta_row = await session.execute(
            select(ControlsMeta).order_by(ControlsMeta.id.desc()).limit(1)
        )
        catalog_meta = meta_row.scalar_one_or_none()

        # Linked system
        linked_system = None
        if asmt.system_id:
            sys_row = await session.execute(
                select(System).where(System.id == asmt.system_id)
            )
            linked_system = sys_row.scalar_one_or_none()

        # All systems for the linkage dropdown
        all_systems_row = await session.execute(
            select(System).order_by(System.name)
        )
        all_systems = all_systems_row.scalars().all()

        # can_edit: admin, submitter, or a user assigned to the linked system
        user = request.headers.get("Remote-User", "")
        can_edit = (
            _is_admin(request)
            or asmt.submitted_by == user
            or (asmt.system_id and await _can_access_system(asmt.system_id, request, session))
        )

    quiz_detail = []
    for q in QUESTIONS:
        resp = quiz_responses_db.get(q["id"])
        quiz_detail.append({
            "id":          q["id"],
            "question":    q["question"],
            "choices":     q["choices"],
            "selected":    resp.selected_answer if resp else None,
            "correct":     q["answer"],
            "is_correct":  resp.is_correct if resp else False,
            "explanation": q["explanation"],
        })

    family_stats = defaultdict(lambda: {
        "COMPLETE": 0, "PARTIAL": 0, "INSUFFICIENT": 0, "NOT_FOUND": 0, "NA": 0, "total": 0
    })
    for c in controls:
        fam = (c.control_family or "??").upper()
        family_stats[fam][c.ai_grade] = family_stats[fam].get(c.ai_grade, 0) + 1
        family_stats[fam]["total"] += 1

    remediation = {c.control_id: get_remediation(c.control_id) for c in controls}

    return templates.TemplateResponse("results.html", {
        "request":        request,
        "assessment_id":  assessment_id,
        "candidate_name": candidate.name if candidate else "Unknown",
        "assessment":     asmt,
        "controls":       controls,
        "quiz_detail":    quiz_detail,
        "family_stats":   dict(family_stats),
        "remediation":    remediation,
        "catalog_meta":   catalog_meta,
        "linked_system":  linked_system,
        "all_systems":    all_systems,
        "can_edit":       can_edit,
        **_tpl_ctx(request),
    })


@app.post("/results/{assessment_id}/proctor")
async def save_proctor_note(
    assessment_id:      str,
    control_id:         str         = Form(...),
    proctor_assessment: str         = Form(""),
    proctor_score:      Optional[int] = Form(None),
):
    async with SessionLocal() as session:
        await _get_assessment(assessment_id, session)
        await session.execute(
            update(ControlResult)
            .where(
                ControlResult.assessment_id == assessment_id,
                ControlResult.control_id    == control_id,
            )
            .values(
                proctor_assessment = proctor_assessment,
                proctor_score      = proctor_score,
            )
        )
        await session.commit()
    return JSONResponse({"ok": True})


@app.post("/results/{assessment_id}/link-system")
async def link_system(request: Request, assessment_id: str):
    form      = await request.form()
    system_id = str(form.get("system_id", "")).strip() or None
    user      = request.headers.get("Remote-User", "")

    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)
        asmt.system_id = system_id
        await _log_audit(session, user, "UPDATE", "assessment", assessment_id,
                         {"system_id": system_id})
        await session.commit()
    return JSONResponse({"ok": True, "system_id": system_id})


@app.post("/results/{assessment_id}/controls/{ctrl_id}/edit")
async def edit_control(
    request: Request,
    assessment_id: str,
    ctrl_id: str,
    field: str = Form(...),
    value: str = Form(""),
):
    """Employee (or admin) can edit narrative, responsible_role, or add a note on a control."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    allowed_fields = {"narrative_excerpt", "responsible_role", "implementation_status", "proctor_assessment"}
    if field not in allowed_fields:
        raise HTTPException(status_code=400, detail=f"Field '{field}' is not editable")

    async with SessionLocal() as session:
        # Verify assessment access
        asmt = await _get_assessment(assessment_id, session)

        # Access check: admin, or the person who submitted this assessment,
        # or someone assigned to the system
        is_authorized = (
            _is_admin(request)
            or asmt.submitted_by == user
            or (asmt.system_id and await _can_access_system(asmt.system_id, request, session))
        )
        if not is_authorized:
            raise HTTPException(status_code=403)

        # Get the control
        result = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .where(ControlResult.control_id == ctrl_id)
        )
        ctrl = result.scalar_one_or_none()
        if not ctrl:
            raise HTTPException(status_code=404, detail="Control not found")

        old_value = getattr(ctrl, field, None)
        setattr(ctrl, field, value)

        # Record the edit
        edit = ControlEdit(
            control_result_id=ctrl.id,
            assessment_id=assessment_id,
            remote_user=user,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=value,
        )
        session.add(edit)
        await _log_audit(session, user, "UPDATE", "control", ctrl_id,
                         {"assessment_id": assessment_id, "field": field, "new_value": value[:100]})
        await session.commit()

    return JSONResponse({"status": "saved", "control_id": ctrl_id, "field": field})


# ── Assessment quiz ────────────────────────────────────────────────────────────

@app.get("/quiz/{assessment_id}", response_class=HTMLResponse)
async def quiz_page(request: Request, assessment_id: str):
    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)
        if asmt.status == "processing":
            return RedirectResponse(url=f"/status/{assessment_id}")
    return templates.TemplateResponse("quiz.html", {
        "request":        request,
        "assessment_id":  assessment_id,
        "candidate_name": candidate.name if candidate else "Unknown",
        "questions":      QUESTIONS,
        **_tpl_ctx(request),
    })


@app.post("/quiz/{assessment_id}/submit")
async def quiz_submit(request: Request, assessment_id: str):
    form = await request.form()

    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)

        responses: Dict[int, str] = {}
        for q in QUESTIONS:
            key  = f"q{q['id']}"
            resp = form.get(key)
            if resp:
                responses[q["id"]] = str(resp).strip().upper()

        result     = grade_quiz(responses)
        quiz_score = result["percentage"]
        combined   = compute_combined_score(asmt.ssp_score, quiz_score, CONFIG)
        allstar    = is_allstar(combined, quiz_score, CONFIG)

        for r in result["results"]:
            session.add(QuizResponse(
                assessment_id   = assessment_id,
                question_id     = r["id"],
                selected_answer = r["selected"],
                is_correct      = r["is_correct"],
            ))

        asmt.quiz_score     = quiz_score
        asmt.combined_score = combined
        asmt.is_allstar     = allstar
        await session.commit()

        candidate = await _get_candidate(asmt.candidate_id, session)
        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .order_by(ControlResult.ai_score)
            .limit(10)
        )
        top_issues = [
            {
                "control_id":    cr.control_id,
                "control_title": cr.control_title,
                "grade":         cr.ai_grade,
                "issues":        (cr.ai_issues or "").split("|"),
            }
            for cr in ctrl_rows.scalars().all()
        ]

    asyncio.get_event_loop().run_in_executor(None, send_report, CONFIG,
        candidate.name if candidate else "Unknown",
        {
            "filename":       asmt.filename,
            "ssp_score":      asmt.ssp_score,
            "quiz_score":     quiz_score,
            "combined_score": combined,
            "is_allstar":     allstar,
            "grade_counts": {
                "COMPLETE":     asmt.controls_complete,
                "PARTIAL":      asmt.controls_partial,
                "INSUFFICIENT": asmt.controls_insufficient,
                "NOT_FOUND":    asmt.controls_not_found,
            },
            "top_issues": top_issues,
        },
        result,
    )

    return RedirectResponse(url=f"/results/{assessment_id}", status_code=303)


# ── Admin dashboard ────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    async with SessionLocal() as session:
        rows = await session.execute(
            select(Assessment, Candidate)
            .join(Candidate, Assessment.candidate_id == Candidate.id)
            .order_by(Assessment.uploaded_at.desc())
            .limit(200)
        )
        entries = [{"assessment": a, "candidate": c} for a, c in rows.all()]

        # Analytics: weakest control families by average AI score
        weak_rows = await session.execute(
            select(ControlResult.control_family,
                   func.avg(ControlResult.ai_score).label("avg_score"))
            .where(ControlResult.ai_grade != "NA")
            .group_by(ControlResult.control_family)
            .order_by(func.avg(ControlResult.ai_score).asc())
            .limit(8)
        )
        weak_families = [
            {"family": r.control_family, "avg": round(r.avg_score, 2)}
            for r in weak_rows
        ]

        # Phase 3: System count
        sys_count_row = await session.execute(select(func.count(System.id)))
        systems_count = sys_count_row.scalar() or 0

        # Phase 3: Open POA&M count
        poam_open_row = await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open", "in_progress"]))
        )
        poam_open_count = poam_open_row.scalar() or 0

        # Phase 3: Open Risk count
        risk_open_row = await session.execute(
            select(func.count(Risk.id))
            .where(Risk.status != "closed")
        )
        risk_open_count = risk_open_row.scalar() or 0

        # Phase 3: POA&M aging
        today_str = date.today().isoformat()
        week_str  = (date.today() + timedelta(days=7)).isoformat()

        poam_overdue_row = await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open", "in_progress"]))
            .where(PoamItem.scheduled_completion != None)
            .where(PoamItem.scheduled_completion < today_str)
        )
        poam_overdue = poam_overdue_row.scalar() or 0

        poam_due_soon_row = await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open", "in_progress"]))
            .where(PoamItem.scheduled_completion != None)
            .where(PoamItem.scheduled_completion >= today_str)
            .where(PoamItem.scheduled_completion <= week_str)
        )
        poam_due_soon = poam_due_soon_row.scalar() or 0

        poam_on_track = max(0, poam_open_count - poam_overdue - poam_due_soon)

        # Phase 3: Risk level breakdown
        risk_rows = await session.execute(
            select(Risk.risk_level, func.count(Risk.id))
            .where(Risk.status != "closed")
            .group_by(Risk.risk_level)
        )
        risk_by_level_raw = {r: c for r, c in risk_rows.all()}
        risk_by_level = {
            "Critical": risk_by_level_raw.get("Critical", 0),
            "High":     risk_by_level_raw.get("High", 0),
            "Moderate": risk_by_level_raw.get("Moderate", 0),
            "Low":      risk_by_level_raw.get("Low", 0),
        }

        # Phase 3: Audit log last 10 entries
        audit_rows = await session.execute(
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
        )
        recent_audit = audit_rows.scalars().all()

        # Phase 5: System auth breakdown
        sys_auth_row = await session.execute(
            select(func.count(System.id)).where(System.auth_status == "authorized")
        )
        systems_auth_count = sys_auth_row.scalar() or 0

        sys_ip_row = await session.execute(
            select(func.count(System.id)).where(System.auth_status == "in_progress")
        )
        systems_in_progress_count = sys_ip_row.scalar() or 0

        # Phase 5: Submissions under review
        sub_review_row = await session.execute(
            select(func.count(Submission.id))
            .where(Submission.status.in_(["submitted", "under_review"]))
        )
        submissions_review_count = sub_review_row.scalar() or 0

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    complete   = [e for e in entries if e["assessment"].status == "complete"]
    pending    = [e for e in complete if not e["assessment"].email_sent]
    allstar_ct = sum(1 for e in complete if e["assessment"].is_allstar)
    avg_ssp    = round(
        sum(e["assessment"].ssp_score for e in complete) / len(complete), 1
    ) if complete else 0.0
    this_week  = [
        e for e in entries
        if e["assessment"].uploaded_at and
        e["assessment"].uploaded_at.replace(tzinfo=timezone.utc) >= week_ago
    ]

    # Analytics: score distribution (10% bins)
    score_bins = [0] * 10
    for e in complete:
        bucket = min(int(e["assessment"].ssp_score // 10), 9)
        score_bins[bucket] += 1

    # Analytics: weekly submission counts (last 8 weeks)
    today = datetime.now(timezone.utc).date()
    weekly_labels = [
        (today - timedelta(weeks=7 - i)).strftime("%Y-W%W")
        for i in range(8)
    ]
    weekly_counts_map: dict = defaultdict(int)
    for e in entries:
        if e["assessment"].uploaded_at:
            wk = e["assessment"].uploaded_at.strftime("%Y-W%W")
            weekly_counts_map[wk] += 1
    weekly_counts = [weekly_counts_map.get(w, 0) for w in weekly_labels]

    employees = CONFIG.get("employees", [])

    return templates.TemplateResponse("admin.html", {
        "request":          request,
        "entries":          entries,
        "pending":          pending,
        "complete_ct":      len(complete),
        "allstar_ct":       allstar_ct,
        "avg_ssp":          avg_ssp,
        "this_week_ct":     len(this_week),
        "employees":        employees,
        "score_bins":       score_bins,
        "weekly_labels":    weekly_labels,
        "weekly_counts":    weekly_counts,
        "weak_families":    weak_families,
        "systems_count":    systems_count,
        "poam_open_count":  poam_open_count,
        "risk_open_count":  risk_open_count,
        "poam_overdue":     poam_overdue,
        "poam_due_soon":    poam_due_soon,
        "poam_on_track":    poam_on_track,
        "risk_by_level":             risk_by_level,
        "recent_audit":              recent_audit,
        "systems_auth_count":        systems_auth_count,
        "systems_in_progress_count": systems_in_progress_count,
        "submissions_review_count":  submissions_review_count,
        **_tpl_ctx(request),
    })


# ── Admin: audit log ───────────────────────────────────────────────────────────

@app.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit(request: Request, days: str = "90"):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    try:
        days_int = int(days)
    except ValueError:
        days_int = 90

    async with SessionLocal() as session:
        q = select(AuditLog).order_by(AuditLog.timestamp.desc())
        if days_int > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_int)
            q = q.where(AuditLog.timestamp >= cutoff)
        q = q.limit(500)
        rows = await session.execute(q)
        entries = rows.scalars().all()
        role = await _get_user_role(request, session)

    return templates.TemplateResponse("audit_log.html", {
        "request": request,
        "entries": entries,
        "days": days_int,
        "user_role": role,
        **_tpl_ctx(request),
    })


# ── Admin: view-as ─────────────────────────────────────────────────────────────

@app.get("/admin/view-as/{username}", response_class=HTMLResponse)
async def admin_view_as(request: Request, username: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    today   = date.today().isoformat()
    past_30 = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]

    async with SessionLocal() as session:
        act_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == username)
            .where(DailyQuizActivity.quiz_date.in_(past_30))
        )
        past_activities: Dict[str, DailyQuizActivity] = {
            a.quiz_date: a for a in act_result.scalars().all()
        }

        history_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == username)
            .order_by(DailyQuizActivity.quiz_date.asc())
            .limit(30)
        )
        score_history = history_result.scalars().all()

        my_rows = await session.execute(
            select(Assessment, Candidate)
            .join(Candidate, Assessment.candidate_id == Candidate.id)
            .where(Assessment.submitted_by == username)
            .order_by(Assessment.uploaded_at.desc())
            .limit(50)
        )
        my_entries = [{"assessment": a, "candidate": c} for a, c in my_rows.all()]

    today_activity = past_activities.get(today)
    quiz_done      = today_activity is not None
    quiz_passed    = today_activity.passed if today_activity else False
    quiz_score_val = today_activity.score if today_activity else 0

    streak = 0
    for i in range(30):
        act = past_activities.get(past_30[i])
        if act and act.passed:
            streak += 1
        else:
            break

    week_dates = past_30[:7]
    week_data  = [
        {
            "date":   d,
            "done":   d in past_activities,
            "passed": past_activities[d].passed if d in past_activities else False,
            "score":  past_activities[d].score  if d in past_activities else None,
        }
        for d in week_dates
    ]

    quiz_cfg       = CONFIG.get("quiz", {})
    pass_threshold = quiz_cfg.get("pass_threshold", 75)

    return templates.TemplateResponse("dashboard.html", {
        "request":        request,
        "today_activity": today_activity,
        "quiz_done":      quiz_done,
        "quiz_passed":    quiz_passed,
        "quiz_score":     quiz_score_val,
        "streak":         streak,
        "week_data":      week_data,
        "score_history":  score_history,
        "my_entries":     my_entries,
        "pass_threshold": pass_threshold,
        "view_as_mode":   True,
        "viewing_as":     username,
        **_tpl_ctx(request),
    })


# ── Admin: download routes ─────────────────────────────────────────────────────

@app.get("/admin/download/{assessment_id}/json")
async def download_json(request: Request, assessment_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)
        ctrl_rows = await session.execute(
            select(ControlResult).where(ControlResult.assessment_id == assessment_id)
        )
        controls = ctrl_rows.scalars().all()
        quiz_rows = await session.execute(
            select(QuizResponse).where(QuizResponse.assessment_id == assessment_id)
        )
        quiz_responses = quiz_rows.scalars().all()
        await _log_audit(session, request.headers.get("Remote-User", ""),
                         "EXPORT", "assessment", assessment_id, {"format": "json"})
        await session.commit()

    data = {
        "assessment_id": assessment_id,
        "candidate": {
            "name":  candidate.name if candidate else "Unknown",
            "email": candidate.email if candidate else "",
        },
        "filename":    asmt.filename,
        "uploaded_at": asmt.uploaded_at.isoformat() if asmt.uploaded_at else None,
        "submitted_by": asmt.submitted_by or "",
        "status":      asmt.status,
        "scores": {
            "ssp":      asmt.ssp_score,
            "quiz":     asmt.quiz_score,
            "combined": asmt.combined_score,
        },
        "is_allstar": asmt.is_allstar,
        "grade_counts": {
            "complete":     asmt.controls_complete,
            "partial":      asmt.controls_partial,
            "insufficient": asmt.controls_insufficient,
            "not_found":    asmt.controls_not_found,
        },
        "control_results": [
            {
                "control_id": c.control_id,
                "family":     c.control_family,
                "title":      c.control_title,
                "grade":      c.ai_grade,
                "score":      c.ai_score,
                "issues":     c.ai_issues,
            }
            for c in controls
        ],
        "quiz_responses": [
            {
                "question_id": q.question_id,
                "selected":    q.selected_answer,
                "correct":     q.is_correct,
            }
            for q in quiz_responses
        ],
    }

    short_id = assessment_id[:8]
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="blacksite-{short_id}.json"'},
    )


@app.get("/admin/download/{assessment_id}/original")
async def download_original(request: Request, assessment_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)
        file_path = Path(asmt.file_path)
        orig_name = asmt.filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    return FileResponse(
        path=file_path,
        filename=orig_name,
        media_type="application/octet-stream",
    )


@app.get("/admin/download/{assessment_id}/print", response_class=HTMLResponse)
async def print_report(request: Request, assessment_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)
        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .order_by(ControlResult.control_family, ControlResult.control_id)
        )
        controls = ctrl_rows.scalars().all()

    return templates.TemplateResponse("print_report.html", {
        "request":        request,
        "assessment_id":  assessment_id,
        "candidate_name": candidate.name if candidate else "Unknown",
        "assessment":     asmt,
        "controls":       controls,
        **_tpl_ctx(request),
    })


# ── Admin: forward to employee ─────────────────────────────────────────────────

@app.post("/admin/forward/{assessment_id}")
async def forward_to_employee(request: Request, assessment_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    form               = await request.form()
    employee_username  = str(form.get("employee_username", "")).strip()
    review_note        = str(form.get("review_note", "")).strip()

    employees = CONFIG.get("employees", [])
    employee  = next(
        (e for e in employees if e.get("username") == employee_username),
        None
    )
    if not employee or not employee.get("email"):
        return JSONResponse(
            {"ok": False, "error": "Employee not found or has no email address"},
            status_code=400,
        )

    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)

        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .order_by(ControlResult.ai_score)
            .limit(10)
        )
        top_issues = [
            {
                "control_id":    cr.control_id,
                "control_title": cr.control_title,
                "grade":         cr.ai_grade,
                "issues":        (cr.ai_issues or "").split("|"),
            }
            for cr in ctrl_rows.scalars().all()
        ]

        asmt.email_sent = True
        await _log_audit(session, request.headers.get("Remote-User", ""),
                         "EXPORT", "assessment", assessment_id,
                         {"forwarded_to": employee_username})
        await session.commit()

        cand_name = candidate.name if candidate else "Unknown"

    ok = forward_assessment(
        CONFIG, asmt, cand_name, employee,
        review_note=review_note,
        top_issues=top_issues,
    )

    return JSONResponse({"ok": ok})


# ── Employee dashboard ─────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def employee_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized — Authelia authentication required")

    today     = date.today().isoformat()
    past_30   = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]

    async with SessionLocal() as session:
        act_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == user)
            .where(DailyQuizActivity.quiz_date.in_(past_30))
        )
        past_activities: Dict[str, DailyQuizActivity] = {
            a.quiz_date: a for a in act_result.scalars().all()
        }

        history_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == user)
            .order_by(DailyQuizActivity.quiz_date.asc())
            .limit(30)
        )
        score_history = history_result.scalars().all()

        my_rows = await session.execute(
            select(Assessment, Candidate)
            .join(Candidate, Assessment.candidate_id == Candidate.id)
            .where(Assessment.submitted_by == user)
            .order_by(Assessment.uploaded_at.desc())
            .limit(50)
        )
        my_entries = [{"assessment": a, "candidate": c} for a, c in my_rows.all()]

        # Assigned systems
        assigned_result = await session.execute(
            select(SystemAssignment, System)
            .join(System, SystemAssignment.system_id == System.id)
            .where(SystemAssignment.remote_user == user)
        )
        assigned_systems = [{"assignment": a, "system": s} for a, s in assigned_result.all()]

    today_activity = past_activities.get(today)
    quiz_done      = today_activity is not None
    quiz_passed    = today_activity.passed if today_activity else False
    quiz_score_val = today_activity.score if today_activity else 0

    streak = 0
    for i in range(30):
        d   = past_30[i]
        act = past_activities.get(d)
        if act and act.passed:
            streak += 1
        else:
            break

    week_dates = past_30[:7]
    week_data  = [
        {
            "date":   d,
            "done":   d in past_activities,
            "passed": past_activities[d].passed if d in past_activities else False,
            "score":  past_activities[d].score if d in past_activities else None,
        }
        for d in week_dates
    ]

    quiz_cfg        = CONFIG.get("quiz", {})
    pass_threshold  = quiz_cfg.get("pass_threshold", 75)
    question_count  = quiz_cfg.get("question_count", 15)

    return templates.TemplateResponse("dashboard.html", {
        "request":          request,
        "today_activity":   today_activity,
        "quiz_done":        quiz_done,
        "quiz_passed":      quiz_passed,
        "quiz_score":       quiz_score_val,
        "streak":           streak,
        "week_data":        week_data,
        "score_history":    score_history,
        "my_entries":       my_entries,
        "assigned_systems": assigned_systems,
        "pass_threshold":   pass_threshold,
        "question_count":   question_count,
        "view_as_mode":     False,
        "viewing_as":       "",
        **_tpl_ctx(request),
    })


# ── Daily quiz ─────────────────────────────────────────────────────────────────

@app.get("/dashboard/quiz", response_class=HTMLResponse)
async def daily_quiz_page(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    today = date.today().isoformat()

    async with SessionLocal() as session:
        existing = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == user)
            .where(DailyQuizActivity.quiz_date == today)
        )
        if existing.scalar_one_or_none() is not None:
            return RedirectResponse(url="/dashboard", status_code=302)

    quiz_cfg    = CONFIG.get("quiz", {})
    n_questions = quiz_cfg.get("question_count", 15)
    threshold   = quiz_cfg.get("pass_threshold", 75)

    selected = random.sample(QUESTIONS, min(n_questions, len(QUESTIONS)))
    q_ids    = ",".join(str(q["id"]) for q in selected)

    return templates.TemplateResponse("daily_quiz.html", {
        "request":    request,
        "questions":  selected,
        "q_ids":      q_ids,
        "threshold":  threshold,
        "today":      today,
        **_tpl_ctx(request),
    })


@app.post("/dashboard/quiz/submit")
async def daily_quiz_submit(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form      = await request.form()
    today     = date.today().isoformat()
    q_ids_str = str(form.get("q_ids", ""))

    quiz_cfg  = CONFIG.get("quiz", {})
    threshold = quiz_cfg.get("pass_threshold", 75)

    try:
        shown_ids = [int(x) for x in q_ids_str.split(",") if x.strip()]
    except ValueError:
        shown_ids = []

    shown_q = [q for q in QUESTIONS if q["id"] in shown_ids]

    responses: Dict[int, str] = {}
    for q in shown_q:
        key  = f"q{q['id']}"
        resp = form.get(key)
        if resp:
            responses[q["id"]] = str(resp).strip().upper()

    result = grade_daily_quiz(responses, shown_q)
    pct    = result["percentage"]
    passed = pct >= threshold

    async with SessionLocal() as session:
        existing = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == user)
            .where(DailyQuizActivity.quiz_date == today)
        )
        if existing.scalar_one_or_none() is None:
            session.add(DailyQuizActivity(
                remote_user = user,
                quiz_date   = today,
                score       = int(pct),
                passed      = passed,
            ))
            await session.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


# ── User Profile ───────────────────────────────────────────────────────────────

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        row = await session.execute(
            select(UserProfile).where(UserProfile.remote_user == user)
        )
        profile = row.scalar_one_or_none()

    # Default domain options
    quiz_domains_all = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]
    selected_domains = []
    if profile and profile.quiz_domains:
        try:
            selected_domains = json.loads(profile.quiz_domains)
        except (json.JSONDecodeError, TypeError):
            selected_domains = []

    return templates.TemplateResponse("profile.html", {
        "request":         request,
        "profile":         profile,
        "quiz_domains_all": quiz_domains_all,
        "selected_domains": selected_domains,
        **_tpl_ctx(request),
    })


@app.post("/profile")
async def profile_save(
    request:             Request,
    display_name:        str  = Form(""),
    email:               str  = Form(""),
    department:          str  = Form(""),
    notifications_email: bool = Form(False),
    notifications_quiz:  bool = Form(False),
):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    quiz_domains = [v for k, v in form.multi_items() if k == "quiz_domains"]

    async with SessionLocal() as session:
        row = await session.execute(
            select(UserProfile).where(UserProfile.remote_user == user)
        )
        profile = row.scalar_one_or_none()

        if profile is None:
            profile = UserProfile(remote_user=user)
            session.add(profile)

        profile.display_name        = display_name.strip() or None
        profile.email               = email.strip() or None
        profile.department          = department.strip() or None
        profile.notifications_email = notifications_email
        profile.notifications_quiz  = notifications_quiz
        profile.quiz_domains        = json.dumps(quiz_domains) if quiz_domains else None
        profile.updated_at          = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "profile", user, {"fields": ["display_name", "email", "department"]})
        await session.commit()

    return RedirectResponse(url="/profile", status_code=303)


# ── System Catalog ─────────────────────────────────────────────────────────────

@app.get("/systems", response_class=HTMLResponse)
async def systems_list(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if _is_admin(request):
            rows = await session.execute(
                select(System).order_by(System.name)
            )
            systems = rows.scalars().all()
        else:
            # Non-admins only see systems they are assigned to
            allowed_ids = await _user_system_ids(request, session)
            if allowed_ids:
                rows = await session.execute(
                    select(System)
                    .where(System.id.in_(allowed_ids))
                    .order_by(System.name)
                )
                systems = rows.scalars().all()
            else:
                systems = []

    authorized_ct    = sum(1 for s in systems if s.auth_status == "authorized")
    in_progress_ct   = sum(1 for s in systems if s.auth_status == "in_progress")
    expired_ct       = sum(1 for s in systems if s.auth_status == "expired")
    not_auth_ct      = sum(1 for s in systems if s.auth_status == "not_authorized")

    return templates.TemplateResponse("systems.html", {
        "request":         request,
        "systems":         systems,
        "authorized_ct":   authorized_ct,
        "in_progress_ct":  in_progress_ct,
        "expired_ct":      expired_ct,
        "not_auth_ct":     not_auth_ct,
        **_tpl_ctx(request),
    })


@app.get("/systems/new", response_class=HTMLResponse)
async def system_new_form(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    return templates.TemplateResponse("system_form.html", {
        "request": request,
        "system":  None,
        "action":  "/systems",
        **_tpl_ctx(request),
    })


@app.post("/systems")
async def system_create(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()

    ci = str(form.get("confidentiality_impact", "Low"))
    ii = str(form.get("integrity_impact", "Low"))
    ai = str(form.get("availability_impact", "Low"))

    sys = System(
        name                   = str(form.get("name", "")).strip(),
        abbreviation           = str(form.get("abbreviation", "")).strip() or None,
        system_type            = str(form.get("system_type", "")).strip() or None,
        environment            = str(form.get("environment", "")).strip() or None,
        owner_name             = str(form.get("owner_name", "")).strip() or None,
        owner_email            = str(form.get("owner_email", "")).strip() or None,
        description            = str(form.get("description", "")).strip() or None,
        purpose                = str(form.get("purpose", "")).strip() or None,
        boundary               = str(form.get("boundary", "")).strip() or None,
        confidentiality_impact = ci,
        integrity_impact       = ii,
        availability_impact    = ai,
        overall_impact         = compute_overall_impact(ci, ii, ai),
        auth_status            = str(form.get("auth_status", "not_authorized")),
        auth_date              = str(form.get("auth_date", "")).strip() or None,
        auth_expiry            = str(form.get("auth_expiry", "")).strip() or None,
        created_by             = user,
    )

    async with SessionLocal() as session:
        session.add(sys)
        await session.flush()
        sys_id = sys.id
        await _log_audit(session, user, "CREATE", "system", sys_id, {"name": sys.name})
        await session.commit()

    return RedirectResponse(url=f"/systems/{sys_id}", status_code=303)


@app.get("/systems/{system_id}", response_class=HTMLResponse)
async def system_detail(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404, detail="System not found")

        # Linked assessments
        asmt_rows = await session.execute(
            select(Assessment, Candidate)
            .join(Candidate, Assessment.candidate_id == Candidate.id)
            .where(Assessment.system_id == system_id)
            .order_by(Assessment.uploaded_at.desc())
        )
        assessments = [{"assessment": a, "candidate": c} for a, c in asmt_rows.all()]

        # Linked POA&Ms
        poam_rows = await session.execute(
            select(PoamItem)
            .where(PoamItem.system_id == system_id)
            .order_by(PoamItem.severity, PoamItem.scheduled_completion)
        )
        poam_items = poam_rows.scalars().all()

        # Linked Risks
        risk_rows = await session.execute(
            select(Risk)
            .where(Risk.system_id == system_id)
            .order_by(Risk.risk_score.desc())
        )
        risks = risk_rows.scalars().all()

        # Audit history for this system
        audit_rows = await session.execute(
            select(AuditLog)
            .where(AuditLog.resource_type == "system")
            .where(AuditLog.resource_id == system_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(20)
        )
        audit_entries = audit_rows.scalars().all()

        # Access control check — non-admins must be assigned
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403, detail="You are not assigned to this system")

        # Control coverage: totals + by family
        sc_total = (await session.execute(
            select(func.count(SystemControl.id)).where(SystemControl.system_id == system_id)
        )).scalar() or 0
        sc_impl = (await session.execute(
            select(func.count(SystemControl.id))
            .where(SystemControl.system_id == system_id)
            .where(SystemControl.status.in_(["implemented","inherited","not_applicable"]))
        )).scalar() or 0
        sc_coverage_pct = round(sc_impl / max(sc_total, 1) * 100)

        # By family: {family: {total, impl, pct}}
        family_rows = await session.execute(
            select(SystemControl.control_family,
                   func.count(SystemControl.id).label("total"),
                   func.sum(
                       sa_case(
                           (SystemControl.status.in_(["implemented","inherited","not_applicable"]), 1),
                           else_=0
                       )
                   ).label("impl"))
            .where(SystemControl.system_id == system_id)
            .group_by(SystemControl.control_family)
            .order_by(SystemControl.control_family)
        )
        family_coverage: list[dict] = []
        for row in family_rows.all():
            pct = round((row.impl or 0) / max(row.total, 1) * 100)
            family_coverage.append({
                "family": row.control_family,
                "total": row.total,
                "impl":  row.impl or 0,
                "pct":   pct,
            })

        # Assignments for the access-control panel
        assign_rows = await session.execute(
            select(SystemAssignment)
            .where(SystemAssignment.system_id == system_id)
            .order_by(SystemAssignment.assigned_at)
        )
        assignments = assign_rows.scalars().all()

        # Current user's own assignment (None for admins or unassigned)
        current_user_assignment = None
        if not _is_admin(request):
            for a in assignments:
                if a.remote_user == user:
                    current_user_assignment = a
                    break

        # RMF step records for this system (used by ATO timeline)
        rmf_rr = await session.execute(
            select(RmfRecord).where(RmfRecord.system_id == system_id)
        )
        rmf_records = {rec.step: rec for rec in rmf_rr.scalars().all()}

    today_str = date.today().isoformat()
    poam_overdue  = [p for p in poam_items if p.scheduled_completion and p.scheduled_completion < today_str and p.status in ("open","in_progress")]
    poam_due_week = [p for p in poam_items if p.scheduled_completion and today_str <= p.scheduled_completion <= (date.today() + timedelta(days=7)).isoformat() and p.status in ("open","in_progress")]
    poam_open_ct  = sum(1 for p in poam_items if p.status in ("open","in_progress"))

    return templates.TemplateResponse("system_detail.html", {
        "request":                 request,
        "system":                  sys,
        "assessments":             assessments,
        "poam_items":              poam_items,
        "risks":                   risks,
        "audit_entries":           audit_entries,
        "poam_open_ct":            poam_open_ct,
        "poam_overdue":            len(poam_overdue),
        "poam_due_week":           len(poam_due_week),
        "assignments":             assignments,
        "current_user_assignment": current_user_assignment,
        "sc_total":                sc_total,
        "sc_impl":                 sc_impl,
        "sc_coverage_pct":         sc_coverage_pct,
        "family_coverage":         family_coverage,
        "rmf_records":             rmf_records,
        "rmf_steps":               RMF_STEPS,
        **_tpl_ctx(request),
    })


@app.get("/systems/{system_id}/report", response_class=HTMLResponse)
async def system_report(request: Request, system_id: str):
    """Printable compliance report — PDF-ready standalone document."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_row = await session.execute(select(System).where(System.id == system_id))
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404, detail="System not found")

        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403, detail="Access denied")

        # POA&M items (all, not paginated — report shows summary + full list)
        poam_rows = await session.execute(
            select(PoamItem)
            .where(PoamItem.system_id == system_id)
            .order_by(PoamItem.severity, PoamItem.scheduled_completion)
        )
        all_poams = poam_rows.scalars().all()

        # Risks (all)
        risk_rows = await session.execute(
            select(Risk)
            .where(Risk.system_id == system_id)
            .order_by(Risk.risk_score.desc())
        )
        all_risks = risk_rows.scalars().all()

        # Control coverage (totals + by family)
        sc_total = (await session.execute(
            select(func.count(SystemControl.id)).where(SystemControl.system_id == system_id)
        )).scalar() or 0
        sc_impl = (await session.execute(
            select(func.count(SystemControl.id))
            .where(SystemControl.system_id == system_id)
            .where(SystemControl.status.in_(["implemented", "inherited", "not_applicable"]))
        )).scalar() or 0
        sc_coverage_pct = round(sc_impl / max(sc_total, 1) * 100)

        family_rows = await session.execute(
            select(
                SystemControl.control_family,
                func.count(SystemControl.id).label("total"),
                func.sum(sa_case(
                    (SystemControl.status.in_(["implemented", "inherited", "not_applicable"]), 1),
                    else_=0
                )).label("impl"),
            )
            .where(SystemControl.system_id == system_id)
            .group_by(SystemControl.control_family)
            .order_by(SystemControl.control_family)
        )
        family_coverage = []
        for row in family_rows.all():
            pct = round((row.impl or 0) / max(row.total, 1) * 100)
            family_coverage.append({"family": row.control_family, "total": row.total,
                                    "impl": row.impl or 0, "pct": pct})

    today_str  = date.today().isoformat()
    week_str   = (date.today() + timedelta(days=7)).isoformat()

    # POA&M breakdowns
    sev_order  = ["Critical", "High", "Moderate", "Low", "Informational"]
    open_poams = [p for p in all_poams if p.status in ("open", "in_progress")]
    poam_by_sev = {s: sum(1 for p in open_poams if (p.severity or "Low") == s) for s in sev_order}
    poam_overdue  = [p for p in open_poams if p.scheduled_completion and p.scheduled_completion < today_str]
    poam_due_week = [p for p in open_poams if p.scheduled_completion and today_str <= p.scheduled_completion <= week_str]

    # Risk breakdowns
    level_order = ["Critical", "High", "Moderate", "Low"]
    open_risks  = [r for r in all_risks if r.status in ("open", "accepted")]
    risk_by_level = {l: sum(1 for r in open_risks if (r.risk_level or "Low") == l) for l in level_order}

    # Auth days remaining
    auth_days_remaining = None
    if sys.auth_expiry:
        try:
            exp = date.fromisoformat(sys.auth_expiry)
            auth_days_remaining = (exp - date.today()).days
        except ValueError:
            pass

    return templates.TemplateResponse("system_report.html", {
        "request":              request,
        "system":               sys,
        "generated_at":         datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "generated_date":       date.today().isoformat(),
        "sc_total":             sc_total,
        "sc_impl":              sc_impl,
        "sc_coverage_pct":      sc_coverage_pct,
        "family_coverage":      family_coverage,
        "open_poams":           open_poams,
        "poam_by_sev":          poam_by_sev,
        "poam_overdue_ct":      len(poam_overdue),
        "poam_due_week_ct":     len(poam_due_week),
        "open_risks":           open_risks,
        "risk_by_level":        risk_by_level,
        "auth_days_remaining":  auth_days_remaining,
        **_tpl_ctx(request),
    })


@app.get("/systems/{system_id}/edit", response_class=HTMLResponse)
async def system_edit_form(request: Request, system_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404)

    return templates.TemplateResponse("system_form.html", {
        "request": request,
        "system":  sys,
        "action":  f"/systems/{system_id}/edit",
        **_tpl_ctx(request),
    })


@app.post("/systems/{system_id}/edit")
async def system_update(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    ci = str(form.get("confidentiality_impact", "Low"))
    ii = str(form.get("integrity_impact", "Low"))
    ai = str(form.get("availability_impact", "Low"))

    async with SessionLocal() as session:
        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404)

        sys.name                   = str(form.get("name", "")).strip() or sys.name
        sys.abbreviation           = str(form.get("abbreviation", "")).strip() or None
        sys.system_type            = str(form.get("system_type", "")).strip() or None
        sys.environment            = str(form.get("environment", "")).strip() or None
        sys.owner_name             = str(form.get("owner_name", "")).strip() or None
        sys.owner_email            = str(form.get("owner_email", "")).strip() or None
        sys.description            = str(form.get("description", "")).strip() or None
        sys.purpose                = str(form.get("purpose", "")).strip() or None
        sys.boundary               = str(form.get("boundary", "")).strip() or None
        sys.confidentiality_impact = ci
        sys.integrity_impact       = ii
        sys.availability_impact    = ai
        sys.overall_impact         = compute_overall_impact(ci, ii, ai)
        sys.auth_status            = str(form.get("auth_status", "not_authorized"))
        sys.auth_date              = str(form.get("auth_date", "")).strip() or None
        sys.auth_expiry            = str(form.get("auth_expiry", "")).strip() or None
        sys.updated_at             = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "system", system_id, {"name": sys.name})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}", status_code=303)


@app.post("/systems/{system_id}/delete")
async def system_delete(request: Request, system_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    user = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404)
        await _log_audit(session, user, "DELETE", "system", system_id, {"name": sys.name})
        await session.delete(sys)
        await session.commit()

    return RedirectResponse(url="/systems", status_code=303)


# ── System Assignments (Phase 4) ────────────────────────────────────────────────

@app.post("/systems/{system_id}/assign")
async def assign_system(request: Request, system_id: str,
                        username: str = Form(...),
                        note: str = Form("")):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        # Allow admin self-assignment; otherwise validate against employees config OR UserProfile table
        if username != admin:
            known_cfg = {e["username"] for e in CONFIG.get("employees", [])}
            if username not in known_cfg:
                profile = await session.get(UserProfile, username)
                if not profile:
                    raise HTTPException(status_code=400, detail=f"Unknown user: {username!r}")
        # Check system exists
        sys_obj = await session.get(System, system_id)
        if not sys_obj:
            raise HTTPException(status_code=404)
        # Check not already assigned
        existing = await session.execute(
            select(SystemAssignment)
            .where(SystemAssignment.system_id == system_id)
            .where(SystemAssignment.remote_user == username)
        )
        if existing.scalar_one_or_none():
            return JSONResponse({"status": "already_assigned"})
        assignment = SystemAssignment(
            system_id=system_id, remote_user=username,
            assigned_by=admin, note=note or None
        )
        session.add(assignment)
        await _log_audit(session, admin, "CREATE", "system_assignment",
                         system_id, {"assigned_to": username})
        await session.commit()
    return JSONResponse({"status": "assigned", "user": username})


@app.post("/systems/{system_id}/unassign")
async def unassign_system(request: Request, system_id: str, username: str = Form(...)):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        result = await session.execute(
            select(SystemAssignment)
            .where(SystemAssignment.system_id == system_id)
            .where(SystemAssignment.remote_user == username)
        )
        obj = result.scalar_one_or_none()
        if obj:
            await session.delete(obj)
            await _log_audit(session, admin, "DELETE", "system_assignment",
                             system_id, {"removed_user": username})
            await session.commit()
    return JSONResponse({"status": "removed", "user": username})


@app.get("/systems/{system_id}/assignments")
async def list_assignments(request: Request, system_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as session:
        result = await session.execute(
            select(SystemAssignment)
            .where(SystemAssignment.system_id == system_id)
        )
        assignments = result.scalars().all()
    return JSONResponse([{
        "remote_user": a.remote_user,
        "assigned_by": a.assigned_by,
        "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        "note": a.note,
    } for a in assignments])


# ── POA&M ──────────────────────────────────────────────────────────────────────

@app.get("/poam", response_class=HTMLResponse)
async def poam_dashboard(request: Request):
    user    = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    is_adm  = _is_admin(request)

    today_str = date.today().isoformat()
    week_str  = (date.today() + timedelta(days=7)).isoformat()
    month_ago = (date.today() - timedelta(days=30)).isoformat()

    # Query params for filtering / pagination
    status_filter = request.query_params.get("status", "open")   # open|in_progress|all|closed
    severity_filter = request.query_params.get("severity", "")
    system_filter   = request.query_params.get("system_id", "")
    PAGE_SIZE = 50
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    async with SessionLocal() as session:
        # Scope to assigned systems for employees
        scoped_sys_ids: list | None = None
        if not is_adm:
            scoped_sys_ids = await _user_system_ids(request, session)

        def _build_q(base_q):
            if scoped_sys_ids is not None:
                base_q = base_q.where(PoamItem.system_id.in_(scoped_sys_ids))
            if status_filter == "all":
                pass
            elif status_filter == "open":
                base_q = base_q.where(PoamItem.status.in_(["open", "in_progress"]))
            else:
                base_q = base_q.where(PoamItem.status == status_filter)
            if severity_filter:
                base_q = base_q.where(PoamItem.severity == severity_filter)
            if system_filter:
                base_q = base_q.where(PoamItem.system_id == system_filter)
            return base_q

        # Stat counts (indexed queries, no full table scan for rendering)
        open_statuses = ["open", "in_progress"]
        base_open = select(func.count(PoamItem.id)).where(PoamItem.status.in_(open_statuses))
        if scoped_sys_ids is not None:
            base_open = base_open.where(PoamItem.system_id.in_(scoped_sys_ids))

        total_open   = (await session.execute(base_open)).scalar() or 0
        crit_high_ct = (await session.execute(
            base_open.where(PoamItem.severity.in_(["Critical","High"]))
        )).scalar() or 0
        overdue_ct   = (await session.execute(
            base_open.where(PoamItem.scheduled_completion < today_str)
            .where(PoamItem.scheduled_completion.isnot(None))
        )).scalar() or 0
        due_soon_ct  = (await session.execute(
            base_open.where(PoamItem.scheduled_completion >= today_str)
                     .where(PoamItem.scheduled_completion <= week_str)
        )).scalar() or 0
        base_closed = select(func.count(PoamItem.id)).where(PoamItem.status == "closed")
        if scoped_sys_ids is not None:
            base_closed = base_closed.where(PoamItem.system_id.in_(scoped_sys_ids))
        closed_month_ct = (await session.execute(
            base_closed.where(PoamItem.completion_date >= month_ago)
        )).scalar() or 0

        sev_counts = {}
        for sev in ("Critical", "High", "Moderate", "Low"):
            ct = (await session.execute(
                base_open.where(PoamItem.severity == sev)
            )).scalar() or 0
            sev_counts[sev] = ct

        # Aging (use raw SQL for speed)
        aging = {"0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0}
        age_q = select(PoamItem.created_at).where(PoamItem.status.in_(open_statuses))
        if scoped_sys_ids is not None:
            age_q = age_q.where(PoamItem.system_id.in_(scoped_sys_ids))
        age_rows = (await session.execute(age_q)).fetchall()
        today_dt = date.today()
        for (created_at,) in age_rows:
            if created_at:
                age = (today_dt - created_at.date()).days
            else:
                age = 0
            if age <= 30:   aging["0_30"] += 1
            elif age <= 60: aging["31_60"] += 1
            elif age <= 90: aging["61_90"] += 1
            else:           aging["90_plus"] += 1

        # Filtered + paginated list
        list_q = _build_q(select(PoamItem)).order_by(
            PoamItem.severity, PoamItem.scheduled_completion
        )
        total_filtered = (await session.execute(
            _build_q(select(func.count(PoamItem.id)))
        )).scalar() or 0
        list_q = list_q.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
        page_items = (await session.execute(list_q)).scalars().all()

        # Systems map for display
        sys_ids = {p.system_id for p in page_items if p.system_id}
        systems_map = {}
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(list(sys_ids)))
            )
            systems_map = {s.id: s for s in sys_rows.scalars().all()}

        # System list for filter dropdown
        if is_adm:
            all_sys = (await session.execute(select(System).order_by(System.name))).scalars().all()
        else:
            all_sys = []
            if scoped_sys_ids:
                all_sys = (await session.execute(
                    select(System).where(System.id.in_(scoped_sys_ids)).order_by(System.name)
                )).scalars().all()

    total_pages = max(1, (total_filtered + PAGE_SIZE - 1) // PAGE_SIZE)

    return templates.TemplateResponse("poam.html", {
        "request":        request,
        "page_items":     page_items,
        "total_open":     total_open,
        "crit_high_ct":   crit_high_ct,
        "overdue_ct":     overdue_ct,
        "due_soon_ct":    due_soon_ct,
        "closed_month_ct":closed_month_ct,
        "sev_counts":     sev_counts,
        "aging":          aging,
        "systems_map":    systems_map,
        "all_sys":        all_sys,
        "status_filter":  status_filter,
        "severity_filter":severity_filter,
        "system_filter":  system_filter,
        "page":           page,
        "total_pages":    total_pages,
        "total_filtered": total_filtered,
        "today_str":      today_str,
        "week_str":       week_str,
        **_tpl_ctx(request),
    })


@app.get("/poam/export", response_class=HTMLResponse)
async def poam_export(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        rows = await session.execute(
            select(PoamItem)
            .where(PoamItem.status.in_(["open","in_progress"]))
            .order_by(PoamItem.severity, PoamItem.scheduled_completion)
        )
        items = rows.scalars().all()

        sys_ids = {p.system_id for p in items if p.system_id}
        systems_map = {}
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(list(sys_ids)))
            )
            systems_map = {s.id: s for s in sys_rows.scalars().all()}

    return templates.TemplateResponse("poam_export.html", {
        "request":     request,
        "items":       items,
        "systems_map": systems_map,
        "export_date": date.today().isoformat(),
        **_tpl_ctx(request),
    })


@app.get("/poam/import/template")
async def poam_import_template(request: Request):
    """Download a blank CSV template for bulk POA&M import."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    fields = [
        "weakness_name", "weakness_description", "severity", "control_id",
        "responsible_party", "scheduled_completion", "detection_source",
        "resources_required", "remediation_plan", "status", "comments",
        "system_name",
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    w.writerow({
        "weakness_name":       "Incomplete access control list",
        "weakness_description":"AC-2 not fully implemented — stale accounts present",
        "severity":            "High",
        "control_id":          "ac-2",
        "responsible_party":   "IAM Team",
        "scheduled_completion":"2026-06-30",
        "detection_source":    "audit",
        "resources_required":  "8 hours engineering",
        "remediation_plan":    "Remove stale accounts, enable quarterly reviews",
        "status":              "open",
        "comments":            "Tracked in Jira INFOSEC-123",
        "system_name":         "",
    })
    content = buf.getvalue()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=poam_import_template.csv"},
    )


@app.get("/poam/import", response_class=HTMLResponse)
async def poam_import_form(request: Request):
    """CSV bulk import form."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_rows = await session.execute(select(System).order_by(System.name))
        all_sys = sys_rows.scalars().all()

    return templates.TemplateResponse("poam_import.html", {
        "request": request,
        "all_sys": all_sys,
        **_tpl_ctx(request),
    })


@app.post("/poam/import")
async def poam_import_csv(
    request: Request,
    file: UploadFile = File(...),
    system_id: str = Form(""),
    dry_run: str = Form("0"),
):
    """Parse uploaded CSV and bulk-create POA&M items."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    content = await file.read()
    try:
        text_content = content.decode("utf-8-sig")  # handle Excel BOM
    except UnicodeDecodeError:
        text_content = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_content))
    VALID_SEVERITIES   = {"Critical", "High", "Moderate", "Low", "Informational"}
    VALID_STATUSES     = {"open", "in_progress", "closed", "risk_accepted", "false_positive"}
    VALID_SOURCES      = {"assessment", "scan", "audit", "pentest", "self_report"}

    created, skipped, errors = 0, 0, []
    items_to_insert = []

    async with SessionLocal() as session:
        # Build system name → id lookup
        sys_rows = await session.execute(select(System.id, System.name))
        name_to_id = {s.name.lower().strip(): s.id for s in sys_rows.all()}

        for i, row in enumerate(reader, start=2):  # row 1 = header
            wname = (row.get("weakness_name") or "").strip()
            if not wname:
                errors.append(f"Row {i}: missing weakness_name — skipped")
                skipped += 1
                continue

            sev = (row.get("severity") or "Low").strip().title()
            if sev not in VALID_SEVERITIES:
                sev = "Low"

            status = (row.get("status") or "open").strip().lower()
            if status not in VALID_STATUSES:
                status = "open"

            source = (row.get("detection_source") or "audit").strip().lower()
            if source not in VALID_SOURCES:
                source = "audit"

            # Resolve system: row-level system_name takes priority, else form-level system_id
            resolved_sys_id = system_id or None
            row_sys_name = (row.get("system_name") or "").strip().lower()
            if row_sys_name and row_sys_name in name_to_id:
                resolved_sys_id = name_to_id[row_sys_name]

            # Validate date
            sched = (row.get("scheduled_completion") or "").strip() or None
            if sched:
                try:
                    date.fromisoformat(sched)
                except ValueError:
                    sched = None
                    errors.append(f"Row {i}: invalid scheduled_completion date — cleared")

            items_to_insert.append(PoamItem(
                id=str(uuid.uuid4()),
                system_id=resolved_sys_id if resolved_sys_id else None,
                control_id=(row.get("control_id") or "").strip().lower() or None,
                weakness_name=wname,
                weakness_description=(row.get("weakness_description") or "").strip() or None,
                detection_source=source,
                severity=sev,
                responsible_party=(row.get("responsible_party") or "").strip() or None,
                resources_required=(row.get("resources_required") or "").strip() or None,
                scheduled_completion=sched,
                status=status,
                remediation_plan=(row.get("remediation_plan") or "").strip() or None,
                comments=(row.get("comments") or "").strip() or None,
                created_by=user,
            ))

        is_dry = dry_run.strip() in ("1", "true", "yes", "on")
        if not is_dry and items_to_insert:
            for item in items_to_insert:
                session.add(item)
            await session.commit()
            # Audit log
            await _log_audit(session, user, "CREATE", "poam_bulk_import", "",
                             {"imported": len(items_to_insert), "file": file.filename})
            await session.commit()

        created = len(items_to_insert)

    return templates.TemplateResponse("poam_import.html", {
        "request":    request,
        "all_sys":    [],
        "result": {
            "created":  created,
            "skipped":  skipped,
            "errors":   errors,
            "dry_run":  is_dry,
            "filename": file.filename,
        },
        **_tpl_ctx(request),
    })


@app.get("/poam/new", response_class=HTMLResponse)
async def poam_new_form(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    assessment_id = request.query_params.get("assessment_id", "")
    control_id    = request.query_params.get("control_id", "")

    async with SessionLocal() as session:
        sys_rows = await session.execute(select(System).order_by(System.name))
        systems  = sys_rows.scalars().all()

    return templates.TemplateResponse("poam_item.html", {
        "request":       request,
        "item":          None,
        "systems":       systems,
        "assessment_id": assessment_id,
        "control_id":    control_id,
        "action":        "/poam",
        **_tpl_ctx(request),
    })


@app.post("/poam")
async def poam_create(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    item = PoamItem(
        system_id            = str(form.get("system_id", "")).strip() or None,
        assessment_id        = str(form.get("assessment_id", "")).strip() or None,
        control_id           = str(form.get("control_id", "")).strip() or None,
        weakness_name        = str(form.get("weakness_name", "")).strip(),
        weakness_description = str(form.get("weakness_description", "")).strip() or None,
        detection_source     = str(form.get("detection_source", "")).strip() or None,
        severity             = str(form.get("severity", "Moderate")),
        responsible_party    = str(form.get("responsible_party", "")).strip() or None,
        resources_required   = str(form.get("resources_required", "")).strip() or None,
        scheduled_completion = str(form.get("scheduled_completion", "")).strip() or None,
        status               = "open",
        remediation_plan     = str(form.get("remediation_plan", "")).strip() or None,
        comments             = str(form.get("comments", "")).strip() or None,
        created_by           = user,
    )

    async with SessionLocal() as session:
        session.add(item)
        await session.flush()
        item_id = item.id
        await _log_audit(session, user, "CREATE", "poam", item_id,
                         {"weakness": item.weakness_name, "severity": item.severity})
        await session.commit()

    return RedirectResponse(url=f"/poam/{item_id}", status_code=303)


@app.get("/poam/{item_id}", response_class=HTMLResponse)
async def poam_item_detail(request: Request, item_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        row = await session.execute(
            select(PoamItem).where(PoamItem.id == item_id)
        )
        item = row.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404)

        sys_rows = await session.execute(select(System).order_by(System.name))
        systems  = sys_rows.scalars().all()

        linked_system = None
        if item.system_id:
            for s in systems:
                if s.id == item.system_id:
                    linked_system = s
                    break

    return templates.TemplateResponse("poam_item.html", {
        "request":      request,
        "item":         item,
        "systems":      systems,
        "linked_system": linked_system,
        "action":       f"/poam/{item_id}/update",
        **_tpl_ctx(request),
    })


@app.post("/poam/{item_id}/update")
async def poam_update(request: Request, item_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()

    async with SessionLocal() as session:
        row = await session.execute(
            select(PoamItem).where(PoamItem.id == item_id)
        )
        item = row.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404)

        item.system_id            = str(form.get("system_id", "")).strip() or None
        item.weakness_name        = str(form.get("weakness_name", item.weakness_name)).strip()
        item.weakness_description = str(form.get("weakness_description", "")).strip() or None
        item.detection_source     = str(form.get("detection_source", "")).strip() or None
        item.severity             = str(form.get("severity", item.severity))
        item.responsible_party    = str(form.get("responsible_party", "")).strip() or None
        item.resources_required   = str(form.get("resources_required", "")).strip() or None
        item.scheduled_completion = str(form.get("scheduled_completion", "")).strip() or None
        item.status               = str(form.get("status", item.status))
        item.remediation_plan     = str(form.get("remediation_plan", "")).strip() or None
        item.completion_date      = str(form.get("completion_date", "")).strip() or None
        item.comments             = str(form.get("comments", "")).strip() or None
        item.updated_at           = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "poam", item_id,
                         {"status": item.status, "severity": item.severity})
        await session.commit()

    return RedirectResponse(url=f"/poam/{item_id}", status_code=303)


@app.post("/api/poam/{item_id}/status")
async def poam_quick_status(request: Request, item_id: str):
    """AJAX: update just the status of a POA&M item. Returns JSON {ok, status}."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    body = await request.json()
    new_status = body.get("status", "")
    valid_statuses = {"open", "in_progress", "closed", "risk_accepted", "false_positive"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    async with SessionLocal() as session:
        row = await session.execute(select(PoamItem).where(PoamItem.id == item_id))
        item = row.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404)
        old_status = item.status
        item.status = new_status
        item.updated_at = datetime.now(timezone.utc)
        if new_status == "closed" and not item.completion_date:
            item.completion_date = date.today().isoformat()
        await _log_audit(session, user, "UPDATE", "poam", item_id,
                         {"status": f"{old_status}→{new_status}"})
        await session.commit()

    return JSONResponse({"ok": True, "status": new_status})


@app.post("/poam/auto/{assessment_id}")
async def poam_auto_create(request: Request, assessment_id: str):
    """Auto-create POA&M items from INSUFFICIENT/NOT_FOUND controls."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)

        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .where(ControlResult.ai_grade.in_(["INSUFFICIENT", "NOT_FOUND"]))
        )
        failing = ctrl_rows.scalars().all()

        created = 0
        for c in failing:
            sev = "High" if c.ai_grade == "NOT_FOUND" else "Moderate"
            item = PoamItem(
                assessment_id        = assessment_id,
                system_id            = asmt.system_id,
                control_id           = c.control_id,
                weakness_name        = f"{c.control_id.upper()} — {c.control_title}",
                weakness_description = f"Control graded {c.ai_grade}. Issues: {c.ai_issues or 'see assessment'}",
                detection_source     = "assessment",
                severity             = sev,
                status               = "open",
                created_by           = user,
            )
            session.add(item)
            created += 1

        await _log_audit(session, user, "CREATE", "poam", assessment_id,
                         {"auto_created": created, "assessment_id": assessment_id})
        await session.commit()

    return JSONResponse({"ok": True, "created": created})


# ── Risk Register ──────────────────────────────────────────────────────────────

@app.get("/risks", response_class=HTMLResponse)
async def risks_dashboard(request: Request):
    user    = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    is_adm  = _is_admin(request)

    status_filter = request.query_params.get("status", "open")   # open|closed|all|accepted
    level_filter  = request.query_params.get("level", "")
    system_filter = request.query_params.get("system_id", "")
    PAGE_SIZE = 50
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    async with SessionLocal() as session:
        scoped_sys_ids: list | None = None
        if not is_adm:
            scoped_sys_ids = await _user_system_ids(request, session)

        def _build_risk_q(base_q):
            if scoped_sys_ids is not None:
                base_q = base_q.where(Risk.system_id.in_(scoped_sys_ids))
            if status_filter == "all":
                pass
            elif status_filter == "open":
                base_q = base_q.where(Risk.status.in_(["open", "accepted"]))
            else:
                base_q = base_q.where(Risk.status == status_filter)
            if level_filter:
                base_q = base_q.where(Risk.risk_level == level_filter)
            if system_filter:
                base_q = base_q.where(Risk.system_id == system_filter)
            return base_q

        # Build heat matrix from active (non-closed) risks using count query
        matrix = [[0]*5 for _ in range(5)]
        matrix_q = select(Risk.likelihood, Risk.impact).where(Risk.status != "closed")
        if scoped_sys_ids is not None:
            matrix_q = matrix_q.where(Risk.system_id.in_(scoped_sys_ids))
        for (li, im) in (await session.execute(matrix_q)).fetchall():
            row = max(0, min(4, (li or 1) - 1))
            col = max(0, min(4, (im or 1) - 1))
            matrix[4 - row][col] += 1

        # Filtered + paginated list
        total_filtered = (await session.execute(
            _build_risk_q(select(func.count(Risk.id)))
        )).scalar() or 0
        list_q = _build_risk_q(
            select(Risk).order_by(Risk.risk_score.desc())
        ).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
        risks = (await session.execute(list_q)).scalars().all()

        sys_ids = {r.system_id for r in risks if r.system_id}
        systems_map = {}
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(list(sys_ids)))
            )
            systems_map = {s.id: s for s in sys_rows.scalars().all()}

        if is_adm:
            all_sys = (await session.execute(select(System).order_by(System.name))).scalars().all()
        else:
            all_sys = []
            if scoped_sys_ids:
                all_sys = (await session.execute(
                    select(System).where(System.id.in_(scoped_sys_ids)).order_by(System.name)
                )).scalars().all()

    total_pages = max(1, (total_filtered + PAGE_SIZE - 1) // PAGE_SIZE)

    return templates.TemplateResponse("risks.html", {
        "request":        request,
        "risks":          risks,
        "systems_map":    systems_map,
        "matrix":         matrix,
        "all_sys":        all_sys,
        "status_filter":  status_filter,
        "level_filter":   level_filter,
        "system_filter":  system_filter,
        "page":           page,
        "total_pages":    total_pages,
        "total_filtered": total_filtered,
        **_tpl_ctx(request),
    })


@app.get("/risks/export", response_class=HTMLResponse)
async def risks_export(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        rows = await session.execute(
            select(Risk)
            .where(Risk.status != "closed")
            .order_by(Risk.risk_score.desc())
        )
        risks = rows.scalars().all()

        sys_ids = {r.system_id for r in risks if r.system_id}
        systems_map = {}
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(list(sys_ids)))
            )
            systems_map = {s.id: s for s in sys_rows.scalars().all()}

    return templates.TemplateResponse("risks_export.html", {
        "request":     request,
        "risks":       risks,
        "systems_map": systems_map,
        "export_date": date.today().isoformat(),
        **_tpl_ctx(request),
    })


@app.get("/risks/new", response_class=HTMLResponse)
async def risk_new_form(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_rows = await session.execute(select(System).order_by(System.name))
        systems  = sys_rows.scalars().all()

    return templates.TemplateResponse("risk_form.html", {
        "request": request,
        "risk":    None,
        "systems": systems,
        "action":  "/risks",
        **_tpl_ctx(request),
    })


@app.post("/risks")
async def risk_create(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    likelihood = int(form.get("likelihood", 3))
    impact     = int(form.get("impact", 3))
    score      = likelihood * impact
    res_l      = int(form.get("residual_likelihood", 2))
    res_i      = int(form.get("residual_impact", 2))
    res_score  = res_l * res_i

    risk = Risk(
        system_id           = str(form.get("system_id", "")).strip() or None,
        risk_name           = str(form.get("risk_name", "")).strip(),
        risk_description    = str(form.get("risk_description", "")).strip() or None,
        threat_source       = str(form.get("threat_source", "")).strip() or None,
        threat_event        = str(form.get("threat_event", "")).strip() or None,
        vulnerability       = str(form.get("vulnerability", "")).strip() or None,
        likelihood          = likelihood,
        impact              = impact,
        risk_score          = score,
        risk_level          = compute_risk_level(score),
        treatment           = str(form.get("treatment", "Mitigate")),
        treatment_plan      = str(form.get("treatment_plan", "")).strip() or None,
        residual_likelihood = res_l,
        residual_impact     = res_i,
        residual_score      = res_score,
        residual_level      = compute_risk_level(res_score),
        owner               = str(form.get("owner", "")).strip() or None,
        status              = "open",
        review_date         = str(form.get("review_date", "")).strip() or None,
        created_by          = user,
    )

    async with SessionLocal() as session:
        session.add(risk)
        await session.flush()
        risk_id = risk.id
        await _log_audit(session, user, "CREATE", "risk", risk_id,
                         {"name": risk.risk_name, "level": risk.risk_level})
        await session.commit()

    return RedirectResponse(url=f"/risks/{risk_id}", status_code=303)


@app.get("/risks/{risk_id}", response_class=HTMLResponse)
async def risk_detail(request: Request, risk_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        row = await session.execute(
            select(Risk).where(Risk.id == risk_id)
        )
        risk = row.scalar_one_or_none()
        if not risk:
            raise HTTPException(status_code=404)

        sys_rows = await session.execute(select(System).order_by(System.name))
        systems  = sys_rows.scalars().all()

        linked_system = None
        if risk.system_id:
            for s in systems:
                if s.id == risk.system_id:
                    linked_system = s
                    break

    return templates.TemplateResponse("risk_form.html", {
        "request":       request,
        "risk":          risk,
        "systems":       systems,
        "linked_system": linked_system,
        "action":        f"/risks/{risk_id}/update",
        **_tpl_ctx(request),
    })


@app.post("/risks/{risk_id}/update")
async def risk_update(request: Request, risk_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    likelihood = int(form.get("likelihood", 3))
    impact     = int(form.get("impact", 3))
    score      = likelihood * impact
    res_l      = int(form.get("residual_likelihood", 2))
    res_i      = int(form.get("residual_impact", 2))
    res_score  = res_l * res_i

    async with SessionLocal() as session:
        row = await session.execute(select(Risk).where(Risk.id == risk_id))
        risk = row.scalar_one_or_none()
        if not risk:
            raise HTTPException(status_code=404)

        risk.system_id           = str(form.get("system_id", "")).strip() or None
        risk.risk_name           = str(form.get("risk_name", risk.risk_name)).strip()
        risk.risk_description    = str(form.get("risk_description", "")).strip() or None
        risk.threat_source       = str(form.get("threat_source", "")).strip() or None
        risk.threat_event        = str(form.get("threat_event", "")).strip() or None
        risk.vulnerability       = str(form.get("vulnerability", "")).strip() or None
        risk.likelihood          = likelihood
        risk.impact              = impact
        risk.risk_score          = score
        risk.risk_level          = compute_risk_level(score)
        risk.treatment           = str(form.get("treatment", risk.treatment))
        risk.treatment_plan      = str(form.get("treatment_plan", "")).strip() or None
        risk.residual_likelihood = res_l
        risk.residual_impact     = res_i
        risk.residual_score      = res_score
        risk.residual_level      = compute_risk_level(res_score)
        risk.owner               = str(form.get("owner", "")).strip() or None
        risk.status              = str(form.get("status", risk.status))
        risk.review_date         = str(form.get("review_date", "")).strip() or None
        risk.updated_at          = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "risk", risk_id,
                         {"status": risk.status, "level": risk.risk_level})
        await session.commit()

    return RedirectResponse(url=f"/risks/{risk_id}", status_code=303)


# ── SSP Generator ──────────────────────────────────────────────────────────────

@app.get("/ssp/{assessment_id}", response_class=HTMLResponse)
async def ssp_document(request: Request, assessment_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)

        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .order_by(ControlResult.control_family, ControlResult.control_id)
        )
        controls = ctrl_rows.scalars().all()

        linked_system = None
        if asmt.system_id:
            sys_row = await session.execute(
                select(System).where(System.id == asmt.system_id)
            )
            linked_system = sys_row.scalar_one_or_none()

        poam_items = []
        if asmt.system_id:
            poam_rows = await session.execute(
                select(PoamItem)
                .where(PoamItem.system_id == asmt.system_id)
                .where(PoamItem.status.in_(["open","in_progress"]))
                .order_by(PoamItem.severity)
            )
            poam_items = poam_rows.scalars().all()

        await _log_audit(session, user, "EXPORT", "assessment", assessment_id,
                         {"format": "ssp_html"})
        await session.commit()

    return templates.TemplateResponse("ssp_export.html", {
        "request":        request,
        "assessment_id":  assessment_id,
        "assessment":     asmt,
        "candidate":      candidate,
        "controls":       controls,
        "linked_system":  linked_system,
        "poam_items":     poam_items,
        "generated_at":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "brand":          _cfg("app.brand", "TheKramerica"),
        **_tpl_ctx(request),
    })


@app.get("/ssp/{assessment_id}/oscal")
async def ssp_oscal(request: Request, assessment_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)

        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
            .order_by(ControlResult.control_family, ControlResult.control_id)
        )
        controls = ctrl_rows.scalars().all()

        linked_system = None
        if asmt.system_id:
            sys_row = await session.execute(
                select(System).where(System.id == asmt.system_id)
            )
            linked_system = sys_row.scalar_one_or_none()

        await _log_audit(session, user, "EXPORT", "assessment", assessment_id,
                         {"format": "oscal_json"})
        await session.commit()

    oscal = {
        "system-security-plan": {
            "uuid": assessment_id,
            "metadata": {
                "title": f"System Security Plan — {candidate.name if candidate else 'Unknown'}",
                "last-modified": asmt.uploaded_at.isoformat() if asmt.uploaded_at else "",
                "version": "1.0",
                "oscal-version": "1.1.2",
            },
            "system-characteristics": {
                "system-name": linked_system.name if linked_system else candidate.name if candidate else "Unknown",
                "system-name-short": linked_system.abbreviation if linked_system else "",
                "description": linked_system.description if linked_system else "",
                "security-sensitivity-level": (linked_system.overall_impact or "Low").lower() if linked_system else "low",
                "system-information": {
                    "information-types": []
                },
                "security-impact-level": {
                    "security-objective-confidentiality": (linked_system.confidentiality_impact or "Low").lower() if linked_system else "low",
                    "security-objective-integrity":       (linked_system.integrity_impact or "Low").lower() if linked_system else "low",
                    "security-objective-availability":    (linked_system.availability_impact or "Low").lower() if linked_system else "low",
                },
                "authorization-boundary": {
                    "description": linked_system.boundary if linked_system else ""
                },
            },
            "system-implementation": {
                "users": [],
                "components": [],
            },
            "control-implementation": {
                "description": "NIST SP 800-53 Rev 5 control implementation",
                "implemented-requirements": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "control-id": c.control_id,
                        "description": c.narrative_excerpt or "",
                        "props": [
                            {"name": "implementation-status", "value": c.implementation_status or "unknown"},
                            {"name": "assessment-grade", "value": c.ai_grade or "NOT_FOUND"},
                            {"name": "assessment-score", "value": str(c.ai_score)},
                        ],
                    }
                    for c in controls
                ],
            },
        }
    }

    short_id = assessment_id[:8]
    return Response(
        content=json.dumps(oscal, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="blacksite-oscal-{short_id}.json"'},
    )


# ── Rule-Based Review API ──────────────────────────────────────────────────────

@app.post("/api/review/{assessment_id}")
async def api_review(request: Request, assessment_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        asmt = await _get_assessment(assessment_id, session)
        if asmt.status != "complete":
            return JSONResponse({"error": "Assessment not complete yet"}, status_code=400)

        ctrl_rows = await session.execute(
            select(ControlResult)
            .where(ControlResult.assessment_id == assessment_id)
        )
        controls = ctrl_rows.scalars().all()

        await _log_audit(session, user, "VIEW", "assessment", assessment_id,
                         {"action": "rule_based_review"})
        await session.commit()

    result = analyze_assessment(asmt, controls)
    return JSONResponse(result)


# ── API ────────────────────────────────────────────────────────────────────────

@app.post("/api/update-controls")
async def trigger_update():
    global CATALOG
    loop = asyncio.get_event_loop()
    ok   = await loop.run_in_executor(None, update_if_needed, CONFIG)
    if ok:
        CATALOG = await loop.run_in_executor(None, load_catalog, CONFIG)
    return {"ok": ok, "controls_loaded": len(CATALOG)}


@app.get("/health")
async def health():
    return {"status": "ok", "controls": len(CATALOG)}


# ── Compliance Posture Dashboard ──────────────────────────────────────────────

@app.get("/posture", response_class=HTMLResponse)
async def posture_dashboard(request: Request):
    """Executive-level compliance posture view — aggregate GRC health metrics."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    is_adm = _is_admin(request)

    today_str = date.today().isoformat()
    week_str  = (date.today() + timedelta(days=7)).isoformat()

    async with SessionLocal() as session:
        # System scope for employee view
        if is_adm:
            scope_q = True   # no filter
            sys_ids_scope = None
        else:
            sys_ids_scope = await _user_system_ids(request, session)

        def _sys_scope(q):
            return q if sys_ids_scope is None else q.where(System.id.in_(sys_ids_scope))
        def _poam_scope(q):
            return q if sys_ids_scope is None else q.where(PoamItem.system_id.in_(sys_ids_scope))
        def _risk_scope(q):
            return q if sys_ids_scope is None else q.where(Risk.system_id.in_(sys_ids_scope))
        def _sub_scope(q):
            return q if sys_ids_scope is None else q.where(Submission.system_id.in_(sys_ids_scope))

        # ── System KPIs ───────────────────────────────────────────────────────
        total_sys = (await session.execute(_sys_scope(select(func.count(System.id))))).scalar() or 0
        auth_by_status = {}
        for row in (await session.execute(
            _sys_scope(select(System.auth_status, func.count(System.id)).group_by(System.auth_status))
        )).all():
            auth_by_status[row[0]] = row[1]

        authorized_pct = round(auth_by_status.get("authorized", 0) / max(total_sys, 1) * 100)

        # Systems expiring in next 90 days
        in_90 = (date.today() + timedelta(days=90)).isoformat()
        expiring_soon = (await session.execute(
            _sys_scope(
                select(func.count(System.id))
                .where(System.auth_status == "authorized")
                .where(System.auth_expiry.isnot(None))
                .where(System.auth_expiry <= in_90)
                .where(System.auth_expiry >= today_str)
            )
        )).scalar() or 0

        expired_count = (await session.execute(
            _sys_scope(select(func.count(System.id)).where(System.auth_status == "expired"))
        )).scalar() or 0

        # ── POA&M KPIs ────────────────────────────────────────────────────────
        open_poams = (await session.execute(
            _poam_scope(select(func.count(PoamItem.id)).where(PoamItem.status.in_(["open","in_progress"])))
        )).scalar() or 0

        overdue_poams = (await session.execute(
            _poam_scope(
                select(func.count(PoamItem.id))
                .where(PoamItem.status.in_(["open","in_progress"]))
                .where(PoamItem.scheduled_completion.isnot(None))
                .where(PoamItem.scheduled_completion < today_str)
            )
        )).scalar() or 0

        crit_high_poams = (await session.execute(
            _poam_scope(
                select(func.count(PoamItem.id))
                .where(PoamItem.status.in_(["open","in_progress"]))
                .where(PoamItem.severity.in_(["Critical","High"]))
            )
        )).scalar() or 0

        poam_sev_data = {}
        for row in (await session.execute(
            _poam_scope(
                select(PoamItem.severity, func.count(PoamItem.id))
                .where(PoamItem.status.in_(["open","in_progress"]))
                .group_by(PoamItem.severity)
            )
        )).all():
            poam_sev_data[row[0]] = row[1]

        # ── Risk KPIs ─────────────────────────────────────────────────────────
        open_risks = (await session.execute(
            _risk_scope(select(func.count(Risk.id)).where(Risk.status != "closed"))
        )).scalar() or 0

        crit_high_risks = (await session.execute(
            _risk_scope(
                select(func.count(Risk.id))
                .where(Risk.status != "closed")
                .where(Risk.risk_level.in_(["Critical","High"]))
            )
        )).scalar() or 0

        risk_level_data = {}
        for row in (await session.execute(
            _risk_scope(
                select(Risk.risk_level, func.count(Risk.id))
                .where(Risk.status != "closed")
                .group_by(Risk.risk_level)
            )
        )).all():
            risk_level_data[row[0]] = row[1]

        # ── Control Coverage ──────────────────────────────────────────────────
        total_sc = (await session.execute(
            _sys_scope(select(func.count(SystemControl.id)).where(SystemControl.system_id == System.id)
                       .correlate(System))
            if sys_ids_scope is None
            else select(func.count(SystemControl.id)).where(SystemControl.system_id.in_(sys_ids_scope))
        )).scalar() or 0

        impl_sc = (await session.execute(
            (select(func.count(SystemControl.id)).where(SystemControl.system_id.in_(sys_ids_scope))
             .where(SystemControl.status.in_(["implemented","inherited","not_applicable"]))
             if sys_ids_scope is not None
             else select(func.count(SystemControl.id))
                  .where(SystemControl.status.in_(["implemented","inherited","not_applicable"])))
        )).scalar() or 0

        coverage_pct = round(impl_sc / max(total_sc, 1) * 100)

        sc_status_data = {}
        sc_q = (select(SystemControl.status, func.count(SystemControl.id)).group_by(SystemControl.status)
                if sys_ids_scope is None
                else select(SystemControl.status, func.count(SystemControl.id))
                     .where(SystemControl.system_id.in_(sys_ids_scope))
                     .group_by(SystemControl.status))
        for row in (await session.execute(sc_q)).all():
            sc_status_data[row[0]] = row[1]

        # ── Submission / ATO pipeline ─────────────────────────────────────────
        sub_pipeline = {}
        for row in (await session.execute(
            _sub_scope(select(Submission.status, func.count(Submission.id)).group_by(Submission.status))
        )).all():
            sub_pipeline[row[0]] = row[1]

        # ── 30-day activity: new POA&Ms and closed POA&Ms ─────────────────────
        month_ago = (date.today() - timedelta(days=30)).isoformat()
        new_poams_30d = (await session.execute(
            _poam_scope(
                select(func.count(PoamItem.id))
                .where(PoamItem.created_at >= month_ago)
            )
        )).scalar() or 0
        closed_poams_30d = (await session.execute(
            _poam_scope(
                select(func.count(PoamItem.id))
                .where(PoamItem.status == "closed")
                .where(PoamItem.updated_at >= month_ago)
            )
        )).scalar() or 0

        # Top 5 systems by open POA&M count (admin only for global view)
        top_poam_systems: list = []
        if is_adm or sys_ids_scope:
            tq = (
                select(System.name, func.count(PoamItem.id).label("cnt"))
                .join(PoamItem, PoamItem.system_id == System.id)
                .where(PoamItem.status.in_(["open","in_progress"]))
                .group_by(System.id)
                .order_by(func.count(PoamItem.id).desc())
                .limit(5)
            )
            if sys_ids_scope is not None:
                tq = tq.where(System.id.in_(sys_ids_scope))
            for row in (await session.execute(tq)).all():
                top_poam_systems.append({"name": row[0], "count": row[1]})

    # ── Posture Score (0-100, composite) ──────────────────────────────────────
    # Simple weighted formula:
    #   40% system authorization rate
    #   30% control coverage
    #   20% no overdue POA&Ms (penalty: -1 per overdue, floor 0)
    #   10% no critical/high risks
    auth_score    = authorized_pct * 0.40
    coverage_score= coverage_pct   * 0.30
    overdue_pen   = min(overdue_poams * 2, 20)
    overdue_score = (20 - overdue_pen)
    crit_pen      = min(crit_high_risks * 2, 10)
    risk_score    = (10 - crit_pen)
    posture_score = round(auth_score + coverage_score + overdue_score + risk_score)
    if posture_score >= 80:    posture_level, posture_color = "Strong",   "var(--green)"
    elif posture_score >= 60:  posture_level, posture_color = "Fair",     "var(--yellow)"
    elif posture_score >= 40:  posture_level, posture_color = "Weak",     "#ff6b35"
    else:                      posture_level, posture_color = "Critical", "var(--red)"

    return templates.TemplateResponse("posture.html", {
        "request":         request,
        "total_sys":       total_sys,
        "auth_by_status":  auth_by_status,
        "authorized_pct":  authorized_pct,
        "expiring_soon":   expiring_soon,
        "expired_count":   expired_count,
        "open_poams":      open_poams,
        "overdue_poams":   overdue_poams,
        "crit_high_poams": crit_high_poams,
        "poam_sev_data":   poam_sev_data,
        "open_risks":      open_risks,
        "crit_high_risks": crit_high_risks,
        "risk_level_data": risk_level_data,
        "total_sc":        total_sc,
        "impl_sc":         impl_sc,
        "coverage_pct":    coverage_pct,
        "sc_status_data":  sc_status_data,
        "sub_pipeline":    sub_pipeline,
        "new_poams_30d":   new_poams_30d,
        "closed_poams_30d":closed_poams_30d,
        "top_poam_systems":top_poam_systems,
        "posture_score":   posture_score,
        "posture_level":   posture_level,
        "posture_color":   posture_color,
        "today_str":       today_str,
        **_tpl_ctx(request),
    })


# ── Global search ─────────────────────────────────────────────────────────────

@app.get("/search", response_class=HTMLResponse)
async def global_search(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    is_adm = _is_admin(request)

    q = (request.query_params.get("q") or "").strip()
    results: dict[str, list] = {"systems": [], "poams": [], "risks": [], "controls": []}

    if not q or len(q) < 2:
        return templates.TemplateResponse("search.html", {
            "request": request, "q": q, "results": results,
            "total": 0, **_tpl_ctx(request),
        })

    needle = f"%{q}%"

    async with SessionLocal() as session:
        # System scope
        if is_adm:
            sys_scope = None
        else:
            sys_scope = await _user_system_ids(request, session)

        # ── Systems ──────────────────────────────────────────────────────────
        sys_q = (
            select(System)
            .where(
                System.name.ilike(needle) |
                System.abbreviation.ilike(needle) |
                System.description.ilike(needle) |
                System.owner_name.ilike(needle)
            )
            .limit(10)
        )
        if sys_scope is not None:
            sys_q = sys_q.where(System.id.in_(sys_scope))
        systems = (await session.execute(sys_q)).scalars().all()
        results["systems"] = [
            {"id": s.id, "name": s.name, "abbr": s.abbreviation,
             "type": s.system_type, "auth": s.auth_status}
            for s in systems
        ]

        # ── POA&M items ───────────────────────────────────────────────────────
        poam_q = (
            select(PoamItem)
            .where(
                PoamItem.weakness_name.ilike(needle) |
                PoamItem.weakness_description.ilike(needle) |
                PoamItem.control_id.ilike(needle) |
                PoamItem.responsible_party.ilike(needle)
            )
            .where(PoamItem.status.in_(["open", "in_progress"]))
            .limit(10)
        )
        if sys_scope is not None:
            poam_q = poam_q.where(PoamItem.system_id.in_(sys_scope))
        poams = (await session.execute(poam_q)).scalars().all()

        sys_ids_needed = {p.system_id for p in poams if p.system_id}
        sys_map: dict = {}
        if sys_ids_needed:
            sr = await session.execute(select(System).where(System.id.in_(list(sys_ids_needed))))
            sys_map = {s.id: s.name for s in sr.scalars().all()}

        results["poams"] = [
            {"id": p.id, "name": p.weakness_name, "severity": p.severity,
             "control": p.control_id, "status": p.status,
             "system": sys_map.get(p.system_id, "")}
            for p in poams
        ]

        # ── Risks ─────────────────────────────────────────────────────────────
        risk_q = (
            select(Risk)
            .where(
                Risk.risk_name.ilike(needle) |
                Risk.risk_description.ilike(needle) |
                Risk.threat_event.ilike(needle)
            )
            .where(Risk.status != "closed")
            .limit(10)
        )
        if sys_scope is not None:
            risk_q = risk_q.where(Risk.system_id.in_(sys_scope))
        risks = (await session.execute(risk_q)).scalars().all()

        rsys_ids = {r.system_id for r in risks if r.system_id} - sys_ids_needed
        if rsys_ids:
            rsr = await session.execute(select(System).where(System.id.in_(list(rsys_ids))))
            for s in rsr.scalars().all():
                sys_map[s.id] = s.name

        results["risks"] = [
            {"id": r.id, "name": r.risk_name, "level": r.risk_level,
             "score": r.risk_score, "treatment": r.treatment,
             "system": sys_map.get(r.system_id, "")}
            for r in risks
        ]

    # ── NIST Controls (in-memory) ─────────────────────────────────────────────
    q_lower = q.lower()
    ctrl_hits = []
    for ctrl_id, ctrl in CATALOG.items():
        title = ctrl.get("title", "")
        text  = ctrl.get("text", "")
        if q_lower in ctrl_id.lower() or q_lower in title.lower() or q_lower in text.lower():
            ctrl_hits.append({
                "id": ctrl_id, "title": title,
                "family": ctrl.get("family", ctrl_id.split("-")[0].upper()),
                "snippet": text[:200] if text else "",
            })
            if len(ctrl_hits) >= 10:
                break
    results["controls"] = ctrl_hits

    total = sum(len(v) for v in results.values())
    return templates.TemplateResponse("search.html", {
        "request": request,
        "q":       q,
        "results": results,
        "total":   total,
        **_tpl_ctx(request),
    })


@app.get("/api/search/suggest")
async def search_suggest(request: Request):
    """AJAX autocomplete — returns top 5 system names + control IDs matching q."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 2:
        return JSONResponse({"suggestions": []})
    needle = f"%{q}%"
    q_lower = q.lower()
    suggestions = []
    async with SessionLocal() as session:
        sys_rows = await session.execute(
            select(System.id, System.name)
            .where(System.name.ilike(needle) | System.abbreviation.ilike(needle))
            .limit(5)
        )
        for sid, sname in sys_rows.all():
            suggestions.append({"type": "system", "label": sname, "url": f"/systems/{sid}"})
    # Add control matches
    for ctrl_id, ctrl in CATALOG.items():
        if q_lower in ctrl_id.lower() or q_lower in ctrl.get("title", "").lower():
            suggestions.append({
                "type": "control", "label": f"{ctrl_id.upper()} — {ctrl.get('title','')}",
                "url": f"/controls/{ctrl_id}"
            })
            if len(suggestions) >= 8:
                break
    return JSONResponse({"suggestions": suggestions[:8]})


# ══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Full GRC Package
# ══════════════════════════════════════════════════════════════════════════════

# ── Helpers ───────────────────────────────────────────────────────────────────

def _catalog_list() -> list[dict]:
    """Flatten CATALOG dict to sorted list of control dicts."""
    items = []
    for ctrl_id, ctrl in CATALOG.items():
        items.append({
            "id":     ctrl_id,
            "family": ctrl.get("family", ctrl_id.split("-")[0].upper()),
            "title":  ctrl.get("title", ""),
            "text":   ctrl.get("text", ""),
        })
    items.sort(key=lambda x: x["id"])
    return items


def _ctrl_families() -> list[str]:
    families = sorted({c["family"] for c in _catalog_list()})
    return families


def _sc_status_color(status: str) -> str:
    return {
        "implemented":    "var(--green)",
        "in_progress":    "var(--yellow)",
        "planned":        "var(--cyan)",
        "not_applicable": "var(--muted)",
        "inherited":      "var(--cyan)",
        "not_started":    "#333",
    }.get(status, "var(--muted)")


def _sc_stats(controls: list) -> dict:
    total = len(controls)
    impl  = sum(1 for c in controls if getattr(c, "status", "not_started") == "implemented")
    inh   = sum(1 for c in controls if getattr(c, "status", "not_started") == "inherited")
    ip    = sum(1 for c in controls if getattr(c, "status", "not_started") == "in_progress")
    na    = sum(1 for c in controls if getattr(c, "status", "not_started") == "not_applicable")
    ns    = total - impl - inh - ip - na
    pct   = int(((impl + inh + na) / total * 100)) if total else 0
    return {"total": total, "implemented": impl, "inherited": inh,
            "in_progress": ip, "not_applicable": na, "not_started": ns, "pct": pct}


# ── Control Catalog Browser ───────────────────────────────────────────────────

@app.get("/controls", response_class=HTMLResponse)
async def controls_catalog(request: Request, family: str = "", q: str = ""):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    items = _catalog_list()
    families = _ctrl_families()

    if family:
        items = [c for c in items if c["family"] == family.upper()]
    if q:
        ql = q.lower()
        items = [c for c in items if ql in c["id"].lower() or ql in c["title"].lower() or ql in c["text"].lower()]

    return templates.TemplateResponse("controls.html", {
        "request":  request,
        "items":    items,
        "families": families,
        "family":   family.upper(),
        "q":        q,
        "total":    len(CATALOG),
        **_tpl_ctx(request),
    })


@app.get("/controls/{ctrl_id}", response_class=HTMLResponse)
async def control_detail(request: Request, ctrl_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    ctrl = CATALOG.get(ctrl_id.lower())
    if not ctrl:
        raise HTTPException(status_code=404, detail=f"Control {ctrl_id} not found")

    return templates.TemplateResponse("control_detail.html", {
        "request":  request,
        "ctrl_id":  ctrl_id.lower(),
        "ctrl":     ctrl,
        **_tpl_ctx(request),
    })


# ── System Control Plan ───────────────────────────────────────────────────────

@app.get("/systems/{system_id}/controls", response_class=HTMLResponse)
async def system_controls_page(request: Request, system_id: str, family: str = "", status_filter: str = ""):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403, detail="Not assigned to this system")

        sys_row = await session.execute(select(System).where(System.id == system_id))
        system = sys_row.scalar_one_or_none()
        if not system:
            raise HTTPException(status_code=404)

        sc_rows = await session.execute(
            select(SystemControl).where(SystemControl.system_id == system_id)
        )
        existing = {sc.control_id: sc for sc in sc_rows.scalars().all()}

        # Build unified list from catalog + existing records
        all_catalog = _catalog_list()
        if family:
            all_catalog = [c for c in all_catalog if c["family"] == family.upper()]

        controls = []
        for c in all_catalog:
            sc = existing.get(c["id"])
            stat = sc.status if sc else "not_started"
            if status_filter and stat != status_filter:
                continue
            controls.append({
                "id":       c["id"],
                "family":   c["family"],
                "title":    c["title"],
                "text":     c["text"],
                "sc":       sc,
                "status":   stat,
                "color":    _sc_status_color(stat),
            })

        # Stats based on ALL controls for this system (not filtered)
        all_sc = await session.execute(
            select(SystemControl).where(SystemControl.system_id == system_id)
        )
        all_sc_list = list(all_sc.scalars().all())
        # Supplement with catalog entries that have no record yet
        all_sc_objs = []
        for c in _catalog_list():
            sc = existing.get(c["id"])
            all_sc_objs.append(sc)
        stats = _sc_stats([s for s in all_sc_objs if s is not None])
        stats["total"] = len(CATALOG)

        # Other systems for inheritance dropdown (limit to 100 for performance)
        other_sys_rows = await session.execute(
            select(System).where(System.id != system_id).order_by(System.name).limit(100)
        )
        other_systems = list(other_sys_rows.scalars().all())

        await _log_audit(session, user, "VIEW", "system", system_id,
                         {"page": "control_plan"})
        await session.commit()

    return templates.TemplateResponse("system_controls.html", {
        "request":       request,
        "system":        system,
        "controls":      controls,
        "stats":         stats,
        "families":      _ctrl_families(),
        "family":        family.upper(),
        "status_filter": status_filter,
        "other_systems": other_systems,
        **_tpl_ctx(request),
    })


@app.post("/systems/{system_id}/controls/{ctrl_id}")
async def update_system_control(request: Request, system_id: str, ctrl_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        form = await request.form()
        ctrl_id = ctrl_id.lower()
        cat_ctrl = CATALOG.get(ctrl_id, {})

        sc_row = await session.execute(
            select(SystemControl)
            .where(SystemControl.system_id == system_id)
            .where(SystemControl.control_id == ctrl_id)
        )
        sc = sc_row.scalar_one_or_none()

        new_status    = str(form.get("status", "not_started"))
        new_narrative = str(form.get("narrative", "")).strip()
        new_role      = str(form.get("responsible_role", "")).strip()
        new_itype     = str(form.get("implementation_type", "system"))
        inh_from      = str(form.get("inherited_from", "")).strip() or None
        inh_narr      = str(form.get("inherited_narrative", "")).strip()

        if sc is None:
            sc = SystemControl(
                system_id           = system_id,
                control_id          = ctrl_id,
                control_family      = ctrl_id.split("-")[0].upper(),
                control_title       = cat_ctrl.get("title", ""),
                created_by          = user,
            )
            session.add(sc)

        sc.status              = new_status
        sc.narrative           = new_narrative or None
        sc.responsible_role    = new_role or None
        sc.implementation_type = new_itype
        sc.inherited_from      = inh_from
        sc.inherited_narrative = inh_narr or None
        sc.last_updated_by     = user
        sc.last_updated_at     = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "system_control",
                         f"{system_id}:{ctrl_id}",
                         {"status": new_status, "system_id": system_id})
        await session.commit()

    return JSONResponse({"ok": True, "status": new_status})


@app.post("/systems/{system_id}/import-controls")
async def import_controls_from_assessment(request: Request, system_id: str):
    """Bulk-import control implementation status from the most recent complete assessment."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        # Find most recent complete assessment linked to this system
        asmt_row = await session.execute(
            select(Assessment)
            .where(Assessment.system_id == system_id)
            .where(Assessment.status == "complete")
            .order_by(Assessment.uploaded_at.desc())
        )
        asmt = asmt_row.scalars().first()
        if not asmt:
            return JSONResponse({"ok": False, "error": "No complete assessment linked to this system"}, status_code=400)

        ctrl_rows = await session.execute(
            select(ControlResult).where(ControlResult.assessment_id == asmt.id)
        )
        ctrl_results = ctrl_rows.scalars().all()

        # Grade → status mapping
        grade_to_status = {
            "COMPLETE":      "implemented",
            "PARTIAL":       "in_progress",
            "INSUFFICIENT":  "in_progress",
            "NOT_FOUND":     "not_started",
            "NA":            "not_applicable",
        }

        imported = 0
        for cr in ctrl_results:
            sc_row = await session.execute(
                select(SystemControl)
                .where(SystemControl.system_id == system_id)
                .where(SystemControl.control_id == cr.control_id)
            )
            sc = sc_row.scalar_one_or_none()

            new_status = grade_to_status.get(cr.ai_grade, "not_started")
            if cr.is_na:
                new_status = "not_applicable"

            if sc is None:
                sc = SystemControl(
                    system_id        = system_id,
                    control_id       = cr.control_id,
                    control_family   = cr.control_family,
                    control_title    = cr.control_title,
                    status           = new_status,
                    narrative        = cr.narrative_excerpt,
                    responsible_role = cr.responsible_role,
                    last_updated_by  = user,
                    created_by       = user,
                )
                session.add(sc)
                imported += 1
            else:
                # Only update if currently not_started (don't overwrite manual edits)
                if sc.status == "not_started":
                    sc.status          = new_status
                    sc.narrative       = sc.narrative or cr.narrative_excerpt
                    sc.last_updated_by = user
                    imported += 1

        await _log_audit(session, user, "UPDATE", "system", system_id,
                         {"action": "import_controls", "assessment_id": asmt.id, "imported": imported})
        await session.commit()

    return JSONResponse({"ok": True, "imported": imported, "assessment_id": asmt.id})


# ── Submission (ATO Package) ──────────────────────────────────────────────────

@app.get("/systems/{system_id}/submit", response_class=HTMLResponse)
async def submission_form(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_row = await session.execute(select(System).where(System.id == system_id))
        system = sys_row.scalar_one_or_none()
        if not system:
            raise HTTPException(status_code=404)

        # Control plan stats for the summary
        sc_rows = await session.execute(
            select(SystemControl).where(SystemControl.system_id == system_id)
        )
        sc_list = list(sc_rows.scalars().all())
        stats   = _sc_stats(sc_list)
        stats["total"] = len(CATALOG)

        # Open POA&Ms
        poam_rows = await session.execute(
            select(PoamItem)
            .where(PoamItem.system_id == system_id)
            .where(PoamItem.status.in_(["open","in_progress"]))
        )
        open_poams = list(poam_rows.scalars().all())

        # Open Risks
        risk_rows = await session.execute(
            select(Risk)
            .where(Risk.system_id == system_id)
            .where(Risk.status == "open")
        )
        open_risks = list(risk_rows.scalars().all())

        # Past submissions
        sub_rows = await session.execute(
            select(Submission)
            .where(Submission.system_id == system_id)
            .order_by(Submission.created_at.desc())
        )
        past_submissions = list(sub_rows.scalars().all())

    return templates.TemplateResponse("submission_form.html", {
        "request":          request,
        "system":           system,
        "stats":            stats,
        "open_poams":       open_poams,
        "open_risks":       open_risks,
        "past_submissions": past_submissions,
        **_tpl_ctx(request),
    })


@app.post("/systems/{system_id}/submit")
async def create_submission(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_row = await session.execute(select(System).where(System.id == system_id))
        system = sys_row.scalar_one_or_none()
        if not system:
            raise HTTPException(status_code=404)

        form = await request.form()

        # Snapshot control stats
        sc_rows = await session.execute(
            select(SystemControl).where(SystemControl.system_id == system_id)
        )
        sc_list  = list(sc_rows.scalars().all())
        stats    = _sc_stats(sc_list)
        total_ct = len(CATALOG)

        sub = Submission(
            system_id       = system_id,
            submission_type = str(form.get("submission_type", "initial")),
            status          = "submitted",
            package_notes   = str(form.get("package_notes", "")).strip() or None,
            submitted_by    = user,
            submitted_at    = datetime.now(timezone.utc),
            controls_total  = total_ct,
            controls_impl   = stats["implemented"] + stats["inherited"],
            controls_na     = stats["not_applicable"],
            controls_gap    = stats["not_started"] + stats["in_progress"],
            created_by      = user,
        )
        session.add(sub)

        # Update system auth_status to in_progress
        system.auth_status = "in_progress"
        system.updated_at  = datetime.now(timezone.utc)

        await _log_audit(session, user, "CREATE", "submission", sub.id,
                         {"system_id": system_id, "type": sub.submission_type})
        await session.commit()

    return RedirectResponse(url=f"/submissions/{sub.id}", status_code=303)


@app.get("/submissions", response_class=HTMLResponse)
async def submissions_list(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if _is_admin(request):
            sub_rows = await session.execute(
                select(Submission).order_by(Submission.created_at.desc())
            )
        else:
            # Employee sees submissions for their systems only
            sys_ids = await _user_system_ids(request, session)
            sub_rows = await session.execute(
                select(Submission)
                .where(Submission.system_id.in_(sys_ids))
                .order_by(Submission.created_at.desc())
            )
        submissions = list(sub_rows.scalars().all())

        # Attach system names
        sys_ids_used = list({s.system_id for s in submissions})
        sys_map = {}
        if sys_ids_used:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(sys_ids_used))
            )
            sys_map = {s.id: s for s in sys_rows.scalars().all()}

    return templates.TemplateResponse("submissions.html", {
        "request":     request,
        "submissions": submissions,
        "sys_map":     sys_map,
        **_tpl_ctx(request),
    })


@app.get("/submissions/{sub_id}", response_class=HTMLResponse)
async def submission_detail(request: Request, sub_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sub_row = await session.execute(select(Submission).where(Submission.id == sub_id))
        sub = sub_row.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404)

        if not await _can_access_system(sub.system_id, request, session):
            raise HTTPException(status_code=403)

        sys_row = await session.execute(select(System).where(System.id == sub.system_id))
        system = sys_row.scalar_one_or_none()

        poam_rows = await session.execute(
            select(PoamItem)
            .where(PoamItem.system_id == sub.system_id)
            .where(PoamItem.status.in_(["open","in_progress"]))
            .order_by(PoamItem.severity)
        )
        open_poams = list(poam_rows.scalars().all())

        risk_rows = await session.execute(
            select(Risk)
            .where(Risk.system_id == sub.system_id)
            .where(Risk.status != "closed")
            .order_by(Risk.risk_score.desc())
        )
        risks = list(risk_rows.scalars().all())

        await _log_audit(session, user, "VIEW", "submission", sub_id, {})
        await session.commit()

    return templates.TemplateResponse("submission_detail.html", {
        "request":    request,
        "sub":        sub,
        "system":     system,
        "open_poams": open_poams,
        "risks":      risks,
        **_tpl_ctx(request),
    })


@app.post("/submissions/{sub_id}/update")
async def update_submission(request: Request, sub_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin only")
    user = request.headers.get("Remote-User", "")

    async with SessionLocal() as session:
        sub_row = await session.execute(select(Submission).where(Submission.id == sub_id))
        sub = sub_row.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404)

        form = await request.form()
        sub.status       = str(form.get("status", sub.status))
        sub.reviewer     = str(form.get("reviewer", "")).strip() or sub.reviewer
        sub.decision     = str(form.get("decision", "")).strip() or None
        sub.decision_date= str(form.get("decision_date", "")).strip() or None
        sub.ato_expiry   = str(form.get("ato_expiry", "")).strip() or None
        sub.package_notes= str(form.get("package_notes", "")).strip() or sub.package_notes
        sub.reviewed_at  = datetime.now(timezone.utc) if sub.decision else sub.reviewed_at
        sub.updated_at   = datetime.now(timezone.utc)

        # If authorized, update the system auth status
        if sub.decision == "authorized":
            sys_row = await session.execute(select(System).where(System.id == sub.system_id))
            system = sys_row.scalar_one_or_none()
            if system:
                system.auth_status  = "authorized"
                system.auth_date    = sub.decision_date
                system.auth_expiry  = sub.ato_expiry
                system.updated_at   = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "submission", sub_id,
                         {"status": sub.status, "decision": sub.decision})
        await session.commit()

    return RedirectResponse(url=f"/submissions/{sub_id}", status_code=303)


# ── RSS / Advisory Feed ────────────────────────────────────────────────────────

from app.rss_feed import get_feed_items, get_all_feed_items

@app.get("/api/alerts")
async def api_alerts(request: Request):
    """
    Return actionable GRC alerts for the current user.
    Admin: org-wide alerts. Employee: scoped to their systems.
    """
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    is_adm = _is_admin(request)

    today_str = date.today().isoformat()
    week_str  = (date.today() + timedelta(days=7)).isoformat()
    in_90     = (date.today() + timedelta(days=90)).isoformat()

    alerts = []
    async with SessionLocal() as session:
        if is_adm:
            sys_scope = None
        else:
            sys_scope = await _user_system_ids(request, session)

        def _ps(q):
            return q if sys_scope is None else q.where(PoamItem.system_id.in_(sys_scope))
        def _rs(q):
            return q if sys_scope is None else q.where(Risk.system_id.in_(sys_scope))
        def _ss(q):
            return q if sys_scope is None else q.where(System.id.in_(sys_scope))

        # Overdue POA&Ms
        overdue_ct = (await session.execute(
            _ps(select(func.count(PoamItem.id))
                .where(PoamItem.status.in_(["open","in_progress"]))
                .where(PoamItem.scheduled_completion.isnot(None))
                .where(PoamItem.scheduled_completion < today_str))
        )).scalar() or 0
        if overdue_ct:
            alerts.append({
                "level": "critical", "icon": "⚑",
                "title": f"{overdue_ct} POA&M{'s' if overdue_ct!=1 else ''} Overdue",
                "body": "Remediation milestones have passed without closure.",
                "url": "/poam?status=open",
                "action": "View Overdue"
            })

        # Critical/High POA&Ms
        crit_ct = (await session.execute(
            _ps(select(func.count(PoamItem.id))
                .where(PoamItem.status.in_(["open","in_progress"]))
                .where(PoamItem.severity.in_(["Critical","High"])))
        )).scalar() or 0
        if crit_ct:
            alerts.append({
                "level": "high", "icon": "◈",
                "title": f"{crit_ct} Critical/High POA&M{'s' if crit_ct!=1 else ''}",
                "body": "High-severity weaknesses require priority remediation.",
                "url": "/poam?status=open&severity=Critical",
                "action": "Review Now"
            })

        # Critical/High risks unreviewed
        crit_risk_ct = (await session.execute(
            _rs(select(func.count(Risk.id))
                .where(Risk.status != "closed")
                .where(Risk.risk_level.in_(["Critical","High"])))
        )).scalar() or 0
        if crit_risk_ct:
            alerts.append({
                "level": "high", "icon": "⚠",
                "title": f"{crit_risk_ct} Critical/High Risk{'s' if crit_risk_ct!=1 else ''}",
                "body": "Unaccepted high-impact risks need treatment plans.",
                "url": "/risks?level=Critical",
                "action": "View Risks"
            })

        # Expired ATOs
        expired_ct = (await session.execute(
            _ss(select(func.count(System.id)).where(System.auth_status == "expired"))
        )).scalar() or 0
        if expired_ct:
            alerts.append({
                "level": "critical", "icon": "⏳",
                "title": f"{expired_ct} System ATO{'s' if expired_ct!=1 else ''} Expired",
                "body": "Systems operating without valid authorization.",
                "url": "/systems",
                "action": "View Systems"
            })

        # ATOs expiring in 90 days
        expiring_ct = (await session.execute(
            _ss(select(func.count(System.id))
                .where(System.auth_status == "authorized")
                .where(System.auth_expiry.isnot(None))
                .where(System.auth_expiry <= in_90)
                .where(System.auth_expiry >= today_str))
        )).scalar() or 0
        if expiring_ct:
            alerts.append({
                "level": "warn", "icon": "📋",
                "title": f"{expiring_ct} ATO{'s' if expiring_ct!=1 else ''} Expiring in 90 Days",
                "body": "Begin reauthorization packages before expiry.",
                "url": "/submissions",
                "action": "Start Reauth"
            })

        # POA&Ms due this week
        due_soon_ct = (await session.execute(
            _ps(select(func.count(PoamItem.id))
                .where(PoamItem.status.in_(["open","in_progress"]))
                .where(PoamItem.scheduled_completion.isnot(None))
                .where(PoamItem.scheduled_completion >= today_str)
                .where(PoamItem.scheduled_completion <= week_str))
        )).scalar() or 0
        if due_soon_ct:
            alerts.append({
                "level": "warn", "icon": "⏱",
                "title": f"{due_soon_ct} POA&M{'s' if due_soon_ct!=1 else ''} Due This Week",
                "body": "Scheduled remediation deadlines approaching.",
                "url": "/poam?status=open",
                "action": "View Due"
            })

    return JSONResponse({"alerts": alerts, "count": len(alerts)})


@app.get("/api/feeds")
async def api_feeds(request: Request):
    """Return merged advisory feed items as JSON. Filtered by user's systems if available."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_ids = await _user_system_ids(request, session)
        systems_list = []
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(sys_ids))
            )
            systems_list = list(sys_rows.scalars().all())

    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(
        None, lambda: get_feed_items(systems=systems_list, max_items=25, min_score=0)
    )
    return JSONResponse({"items": items, "system_count": len(systems_list)})


# ── Phase 6 routes ──────────────────────────────────────────────────────────────

# ── Ticker ─────────────────────────────────────────────────────────────────────

@app.get("/api/ticker")
async def api_ticker(request: Request):
    """Security advisory ticker feed — 60-minute cached, combines internal alerts + CISA KEV."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    now = time.time()
    if now - _ticker_cache["ts"] < 3600:
        return JSONResponse(_ticker_cache)

    items = []

    # Internal GRC alerts (reuse alert query logic)
    today_str = date.today().isoformat()
    week_str  = (date.today() + timedelta(days=7)).isoformat()
    in_90     = (date.today() + timedelta(days=90)).isoformat()

    async with SessionLocal() as session:
        overdue_ct = (await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open","in_progress"]))
            .where(PoamItem.scheduled_completion.isnot(None))
            .where(PoamItem.scheduled_completion < today_str)
        )).scalar() or 0
        if overdue_ct:
            items.append({"text": f"{overdue_ct} POA&M item{'s' if overdue_ct!=1 else ''} overdue — remediation milestones past due", "level": "critical"})

        crit_ct = (await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open","in_progress"]))
            .where(PoamItem.severity.in_(["Critical","High"]))
        )).scalar() or 0
        if crit_ct:
            items.append({"text": f"{crit_ct} Critical/High severity weakness{'es' if crit_ct!=1 else ''} open — priority remediation required", "level": "high"})

        expired_ct = (await session.execute(
            select(func.count(System.id)).where(System.auth_status == "expired")
        )).scalar() or 0
        if expired_ct:
            items.append({"text": f"{expired_ct} system ATO{'s' if expired_ct!=1 else ''} expired — reauthorization required", "level": "critical"})

        expiring_ct = (await session.execute(
            select(func.count(System.id))
            .where(System.auth_status == "authorized")
            .where(System.auth_expiry.isnot(None))
            .where(System.auth_expiry <= in_90)
            .where(System.auth_expiry >= today_str)
        )).scalar() or 0
        if expiring_ct:
            items.append({"text": f"{expiring_ct} ATO{'s' if expiring_ct!=1 else ''} expiring within 90 days — begin reauthorization package", "level": "warn"})

    # CISA KEV — latest 8 entries
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
            )
        kev = r.json()
        vulns = sorted(
            kev.get("vulnerabilities", []),
            key=lambda x: x.get("dateAdded", ""),
            reverse=True
        )[:8]
        for v in vulns:
            desc = v.get("shortDescription", "")[:80]
            items.append({
                "text": f"{v['cveID']} · {v.get('vendorProject','')} {v.get('product','')} — {desc}",
                "level": "warn"
            })
    except Exception:
        pass  # graceful degradation — CISA feed optional

    if not items:
        items = [{"text": "All systems nominal · No active security advisories", "level": "info"}]

    _ticker_cache.update({"ts": now, "items": items, "count": len(items)})
    return JSONResponse(_ticker_cache)


# ── RMF Lifecycle Tracker ───────────────────────────────────────────────────────

@app.get("/rmf", response_class=HTMLResponse)
async def rmf_overview(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_ids = await _user_system_ids(request, session)
        systems = []
        if sys_ids:
            rows = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            systems = list(rows.scalars().all())

        # Fetch all RMF records for these systems
        rmf_rows = {}
        if sys_ids:
            rr = await session.execute(
                select(RmfRecord).where(RmfRecord.system_id.in_(sys_ids))
            )
            for rec in rr.scalars().all():
                rmf_rows.setdefault(rec.system_id, {})[rec.step] = rec

        ctx = await _full_ctx(request, session,
                              systems=systems,
                              rmf_rows=rmf_rows,
                              rmf_steps=RMF_STEPS,
                              step_keys=_RMF_STEP_KEYS)

    return templates.TemplateResponse("rmf.html", {"request": request, **ctx})


@app.get("/rmf/{system_id}", response_class=HTMLResponse)
async def rmf_system(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_obj = await session.get(System, system_id)
        if not sys_obj:
            raise HTTPException(status_code=404)

        rr = await session.execute(
            select(RmfRecord).where(RmfRecord.system_id == system_id)
        )
        records = {rec.step: rec for rec in rr.scalars().all()}

        # Recent audit for each step
        audit_rows = await session.execute(
            select(AuditLog)
            .where(AuditLog.resource_type == "rmf_record")
            .where(AuditLog.resource_id.like(f"{system_id}%"))
            .order_by(AuditLog.timestamp.desc())
            .limit(21)
        )
        all_audit = list(audit_rows.scalars().all())

        complete_ct = sum(1 for s in _RMF_STEP_KEYS if records.get(s) and records[s].status == "complete")
        ctx = await _full_ctx(request, session,
                              system=sys_obj,
                              records=records,
                              rmf_steps=RMF_STEPS,
                              step_keys=_RMF_STEP_KEYS,
                              complete_ct=complete_ct,
                              all_audit=all_audit)

    return templates.TemplateResponse("rmf_system.html", {"request": request, **ctx})


@app.post("/rmf/{system_id}/step/{step}")
async def rmf_update_step(request: Request, system_id: str, step: str,
                          status: str = Form("not_started"),
                          owner: str = Form(""),
                          target_date: str = Form(""),
                          actual_date: str = Form(""),
                          evidence: str = Form("")):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if step not in _RMF_STEP_KEYS:
        raise HTTPException(status_code=400, detail="Invalid RMF step")
    valid_statuses = {"not_started", "in_progress", "complete", "waived"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        existing = (await session.execute(
            select(RmfRecord)
            .where(RmfRecord.system_id == system_id)
            .where(RmfRecord.step == step)
        )).scalar_one_or_none()

        if existing:
            old_status = existing.status
            existing.status      = status
            existing.owner       = owner or None
            existing.target_date = target_date or None
            existing.actual_date = actual_date or None
            existing.evidence    = evidence or None
            existing.updated_at  = datetime.now(timezone.utc)
            details = {"step": step, "old_status": old_status, "new_status": status}
            rid = f"{system_id}:{step}"
        else:
            rec = RmfRecord(
                system_id   = system_id,
                step        = step,
                status      = status,
                owner       = owner or None,
                target_date = target_date or None,
                actual_date = actual_date or None,
                evidence    = evidence or None,
                created_by  = user,
            )
            session.add(rec)
            details = {"step": step, "status": status}
            rid = f"{system_id}:{step}"

        await _log_audit(session, user, "UPDATE", "rmf_record", rid, details)
        await session.commit()

    return RedirectResponse(url=f"/rmf/{system_id}", status_code=303)


# ── Admin: User Management ──────────────────────────────────────────────────────

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        rows = await session.execute(
            select(UserProfile).order_by(UserProfile.remote_user)
        )
        profiles = list(rows.scalars().all())

        # Count assignments per user
        assign_rows = await session.execute(
            select(SystemAssignment.remote_user, func.count(SystemAssignment.id))
            .group_by(SystemAssignment.remote_user)
        )
        assign_counts = dict(assign_rows.all())

        role = await _get_user_role(request, session)

    admin_users_cfg = set(CONFIG.get("app", {}).get("admin_users", ["dan"]))
    employees_cfg   = CONFIG.get("employees", [])

    role_counts: dict = {}
    for p in profiles:
        r = "admin" if p.remote_user in admin_users_cfg else (p.role or "employee")
        role_counts[r] = role_counts.get(r, 0) + 1

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "profiles": profiles,
        "assign_counts": assign_counts,
        "admin_users_cfg": admin_users_cfg,
        "employees_cfg": employees_cfg,
        "role_counts": role_counts,
        "user_role": role,
        **_tpl_ctx(request),
    })


@app.post("/admin/users/add")
async def admin_add_user(request: Request,
                         username: str = Form(...),
                         display_name: str = Form(""),
                         email: str = Form(""),
                         role: str = Form("employee")):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    valid_roles = {"employee", "auditor", "bcdr", "system_owner"}
    if role not in valid_roles:
        role = "employee"

    async with SessionLocal() as session:
        existing = await session.get(UserProfile, username)
        if existing:
            existing.display_name = display_name or existing.display_name
            existing.email        = email or existing.email
            existing.role         = role
        else:
            profile = UserProfile(
                remote_user  = username,
                display_name = display_name or None,
                email        = email or None,
                role         = role,
            )
            session.add(profile)
        await _log_audit(session, admin, "CREATE", "user_profile", username,
                         {"display_name": display_name, "role": role})
        await session.commit()

    return RedirectResponse(url="/admin/users", status_code=303)


@app.post("/admin/users/{username}/role")
async def admin_set_role(request: Request, username: str, role: str = Form(...)):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    valid_roles = {"employee", "auditor", "bcdr", "system_owner"}
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    async with SessionLocal() as session:
        profile = await session.get(UserProfile, username)
        if not profile:
            profile = UserProfile(remote_user=username, role=role)
            session.add(profile)
        else:
            old_role = profile.role
            profile.role = role
            await _log_audit(session, admin, "UPDATE", "user_profile", username,
                             {"old_role": old_role, "new_role": role})
        await session.commit()

    return JSONResponse({"status": "ok", "username": username, "role": role})


# ── Audit export ────────────────────────────────────────────────────────────────

@app.get("/admin/audit/export")
async def audit_export(request: Request, format: str = "csv", days: str = "90"):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    try:
        days_int = int(days)
    except ValueError:
        days_int = 90

    async with SessionLocal() as session:
        q = select(AuditLog).order_by(AuditLog.timestamp.desc())
        if days_int > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_int)
            q = q.where(AuditLog.timestamp >= cutoff)
        rows = await session.execute(q)
        entries = list(rows.scalars().all())

    today_str = date.today().isoformat()
    admin_user = request.headers.get("Remote-User", "unknown")
    async with SessionLocal() as session:
        await _log_audit(session, admin_user, "EXPORT", "audit_log", "bulk",
                         {"format": format, "days": days_int, "count": len(entries)})
        await session.commit()

    if format == "json":
        data = [
            {
                "id":            e.id,
                "timestamp":     e.timestamp.isoformat() if e.timestamp else None,
                "remote_user":   e.remote_user,
                "action":        e.action,
                "resource_type": e.resource_type,
                "resource_id":   e.resource_id,
                "details":       e.details,
            }
            for e in entries
        ]
        content = json.dumps(data, indent=2, default=str)
        return Response(
            content     = content,
            media_type  = "application/json",
            headers     = {"Content-Disposition": f'attachment; filename="audit_log_{today_str}.json"'},
        )
    else:
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "timestamp", "remote_user", "action", "resource_type", "resource_id", "details"])
        for e in entries:
            writer.writerow([
                e.id,
                e.timestamp.isoformat() if e.timestamp else "",
                e.remote_user or "",
                e.action or "",
                e.resource_type or "",
                e.resource_id or "",
                e.details or "",
            ])
        return Response(
            content     = buf.getvalue(),
            media_type  = "text/csv",
            headers     = {"Content-Disposition": f'attachment; filename="audit_log_{today_str}.csv"'},
        )


# ── Reports center ────────────────────────────────────────────────────────────

@app.get("/reports", response_class=HTMLResponse)
async def reports_center(request: Request):
    """Aggregated reporting center — all downloadable/viewable reports."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    is_adm = _is_admin(request)

    today_str = date.today().isoformat()

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)

        # Scope for non-admins
        if is_adm:
            sys_ids_scope = None
        else:
            sys_ids_scope = await _user_system_ids(request, session)

        def _sys_scope(q):
            return q if sys_ids_scope is None else q.where(System.id.in_(sys_ids_scope))
        def _poam_scope(q):
            return q if sys_ids_scope is None else q.where(PoamItem.system_id.in_(sys_ids_scope))
        def _risk_scope(q):
            return q if sys_ids_scope is None else q.where(Risk.system_id.in_(sys_ids_scope))

        # ── Summary stats for report cards ────────────────────────────────────
        total_sys   = (await session.execute(_sys_scope(select(func.count(System.id))))).scalar() or 0
        total_poams = (await session.execute(_poam_scope(select(func.count(PoamItem.id))))).scalar() or 0
        total_risks = (await session.execute(_risk_scope(select(func.count(Risk.id))))).scalar() or 0

        auth_counts: dict = {}
        for row in (await session.execute(
            _sys_scope(select(System.auth_status, func.count(System.id)).group_by(System.auth_status))
        )).all():
            auth_counts[row[0]] = row[1]

        open_poams = (await session.execute(
            _poam_scope(select(func.count(PoamItem.id)).where(PoamItem.status == "open"))
        )).scalar() or 0

        overdue_poams = (await session.execute(
            _poam_scope(select(func.count(PoamItem.id)).where(
                PoamItem.status == "open",
                PoamItem.scheduled_completion < today_str,
                PoamItem.scheduled_completion.isnot(None),
            ))
        )).scalar() or 0

        high_risks = (await session.execute(
            _risk_scope(select(func.count(Risk.id)).where(
                (Risk.likelihood * Risk.impact) >= 15
            ))
        )).scalar() or 0

        # Submissions count
        total_subs = (await session.execute(select(func.count(Submission.id)))).scalar() or 0

        # RMF step completion across systems
        rmf_complete = (await session.execute(
            select(func.count(RmfRecord.id)).where(RmfRecord.status == "complete")
        )).scalar() or 0

        rmf_total_records = (await session.execute(
            select(func.count(RmfRecord.id))
        )).scalar() or 0

        ctx = await _full_ctx(request, session,
            today=today_str,
            total_sys=total_sys,
            total_poams=total_poams,
            total_risks=total_risks,
            open_poams=open_poams,
            overdue_poams=overdue_poams,
            high_risks=high_risks,
            auth_counts=auth_counts,
            total_subs=total_subs,
            rmf_complete=rmf_complete,
            rmf_total_records=rmf_total_records,
            user_role=role,
        )

    return templates.TemplateResponse("reports.html", {"request": request, **ctx})


# ══════════════════════════════════════════════════════════════════════════════
# Phase 7 — ATO Document Workflow Engine
# ══════════════════════════════════════════════════════════════════════════════

def _ato_user_role(request: Request, profile_role: str) -> str:
    """Map UserProfile role + admin flag to ATO action role string."""
    if _is_admin(request):
        return "admin"
    return profile_role  # system_owner | auditor | bcdr | employee


def _ato_can_edit(ato_role: str, doc_type: str) -> bool:
    return ato_role in ATO_DOC_TYPES.get(doc_type, {}).get("owner_roles", [])


def _ato_can_review(ato_role: str, doc_type: str) -> bool:
    return ato_role in ATO_DOC_TYPES.get(doc_type, {}).get("reviewer_roles", [])


def _ato_status_color(status: str) -> str:
    return {"draft": "var(--muted)", "in_review": "var(--warn)", "approved": "var(--ok)", "finalized": "var(--accent)"}.get(status, "var(--muted)")


def _ato_next_version(current: str) -> str:
    """Bump minor version: '0.1' -> '0.2', '1.3' -> '1.4'."""
    try:
        parts = current.split(".")
        return f"{parts[0]}.{int(parts[1]) + 1}"
    except Exception:
        return "1.0"


@app.get("/ato", response_class=HTMLResponse)
async def ato_dashboard(request: Request):
    """ATO Package dashboard — matrix of all systems x all doc types."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_ids = await _user_system_ids(request, session)
        systems = []
        if sys_ids:
            rows = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            systems = list(rows.scalars().all())

        # All ATO docs for these systems, keyed by (system_id, doc_type)
        ato_map: dict = {}
        if sys_ids:
            ato_rows = await session.execute(
                select(AtoDocument).where(AtoDocument.system_id.in_(sys_ids))
            )
            for doc in ato_rows.scalars().all():
                ato_map[(doc.system_id, doc.doc_type)] = doc

        # Summary counts per system
        sys_summary: dict = {}
        for sys in systems:
            total = len(_ATO_DOC_KEYS)
            finalized = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "finalized")
            approved  = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "approved")
            in_review = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "in_review")
            draft     = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "draft")
            missing   = total - finalized - approved - in_review - draft
            sys_summary[sys.id] = {"total": total, "finalized": finalized, "approved": approved, "in_review": in_review, "draft": draft, "missing": missing}

        ctx = await _full_ctx(request, session,
                              systems=systems,
                              ato_map=ato_map,
                              ato_doc_types=ATO_DOC_TYPES,
                              ato_doc_keys=_ATO_DOC_KEYS,
                              sys_summary=sys_summary,
                              status_color=_ato_status_color)

    return templates.TemplateResponse("ato_dashboard.html", {"request": request, **ctx})


@app.get("/ato/{system_id}", response_class=HTMLResponse)
async def ato_system(request: Request, system_id: str):
    """Per-system ATO package — list of all 19 doc types with status."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_obj = await session.get(System, system_id)
        if not sys_obj:
            raise HTTPException(status_code=404)

        ato_rows = await session.execute(
            select(AtoDocument).where(AtoDocument.system_id == system_id)
        )
        docs = {doc.doc_type: doc for doc in ato_rows.scalars().all()}

        role = await _get_user_role(request, session)
        ato_role = _ato_user_role(request, role)

        finalized_ct = sum(1 for k in _ATO_DOC_KEYS if docs.get(k) and docs[k].status == "finalized")
        ato_pct = round(finalized_ct / len(_ATO_DOC_KEYS) * 100)

        today_str = date.today().isoformat()

        ctx = await _full_ctx(request, session,
                              system=sys_obj,
                              docs=docs,
                              ato_doc_types=ATO_DOC_TYPES,
                              ato_doc_keys=_ATO_DOC_KEYS,
                              ato_role=ato_role,
                              finalized_ct=finalized_ct,
                              ato_pct=ato_pct,
                              today_str=today_str,
                              status_color=_ato_status_color)

    return templates.TemplateResponse("ato_system.html", {"request": request, **ctx})


@app.get("/ato/{system_id}/{doc_type}", response_class=HTMLResponse)
async def ato_document(request: Request, system_id: str, doc_type: str):
    """ATO document detail — content editor + workflow + history."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if doc_type not in ATO_DOC_TYPES:
        raise HTTPException(status_code=404, detail="Unknown document type")

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_obj = await session.get(System, system_id)
        if not sys_obj:
            raise HTTPException(status_code=404)

        doc = (await session.execute(
            select(AtoDocument)
            .where(AtoDocument.system_id == system_id)
            .where(AtoDocument.doc_type == doc_type)
        )).scalar_one_or_none()

        # Workflow event history
        events: list = []
        if doc:
            ev_rows = await session.execute(
                select(AtoWorkflowEvent)
                .where(AtoWorkflowEvent.document_id == doc.id)
                .order_by(AtoWorkflowEvent.timestamp.desc())
            )
            events = list(ev_rows.scalars().all())

        # Version history
        versions: list = []
        if doc:
            ver_rows = await session.execute(
                select(AtoDocumentVersion)
                .where(AtoDocumentVersion.document_id == doc.id)
                .order_by(AtoDocumentVersion.changed_at.desc())
                .limit(20)
            )
            versions = list(ver_rows.scalars().all())

        role = await _get_user_role(request, session)
        ato_role = _ato_user_role(request, role)
        can_edit   = _ato_can_edit(ato_role, doc_type) and (not doc or doc.status == "draft")
        can_submit = _ato_can_edit(ato_role, doc_type) and doc and doc.status == "draft"
        can_approve = _ato_can_review(ato_role, doc_type) and doc and doc.status == "in_review"
        can_reject  = _ato_can_review(ato_role, doc_type) and doc and doc.status == "in_review"
        can_finalize = _is_admin(request) and doc and doc.status == "approved"
        can_revise   = (_is_admin(request) or _ato_can_edit(ato_role, doc_type)) and doc and doc.status == "finalized"

        doc_meta = ATO_DOC_TYPES[doc_type]

        today_str = date.today().isoformat()

        ctx = await _full_ctx(request, session,
                              system=sys_obj,
                              doc=doc,
                              doc_type=doc_type,
                              doc_meta=doc_meta,
                              events=events,
                              versions=versions,
                              ato_role=ato_role,
                              can_edit=can_edit,
                              can_submit=can_submit,
                              can_approve=can_approve,
                              can_reject=can_reject,
                              can_finalize=can_finalize,
                              can_revise=can_revise,
                              today_str=today_str,
                              status_color=_ato_status_color)

    return templates.TemplateResponse("ato_document.html", {"request": request, **ctx})


@app.post("/ato/{system_id}/{doc_type}/save")
async def ato_save(request: Request, system_id: str, doc_type: str,
                   content: str = Form(""),
                   title: str = Form(""),
                   assigned_to: str = Form(""),
                   due_date: str = Form("")):
    """Save draft content (create document if doesn't exist yet)."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if doc_type not in ATO_DOC_TYPES:
        raise HTTPException(status_code=404)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        role = await _get_user_role(request, session)
        ato_role = _ato_user_role(request, role)
        if not _ato_can_edit(ato_role, doc_type):
            raise HTTPException(status_code=403, detail="Not authorized to edit this document type")

        doc = (await session.execute(
            select(AtoDocument)
            .where(AtoDocument.system_id == system_id)
            .where(AtoDocument.doc_type == doc_type)
        )).scalar_one_or_none()

        doc_title = title.strip() or ATO_DOC_TYPES[doc_type]["name"]

        if doc:
            if doc.status != "draft":
                raise HTTPException(status_code=400, detail="Cannot edit — document is not in draft status")
            doc.content     = content
            doc.title       = doc_title
            doc.assigned_to = assigned_to or None
            doc.due_date    = due_date or None
            doc.updated_at  = datetime.now(timezone.utc)
        else:
            doc = AtoDocument(
                system_id   = system_id,
                doc_type    = doc_type,
                title       = doc_title,
                content     = content,
                assigned_to = assigned_to or None,
                due_date    = due_date or None,
                created_by  = user,
            )
            session.add(doc)

        await _log_audit(session, user, "SAVE", "ato_document", f"{system_id}/{doc_type}",
                         {"title": doc_title, "status": doc.status if hasattr(doc, 'id') else "draft"})
        await session.commit()

    return RedirectResponse(url=f"/ato/{system_id}/{doc_type}", status_code=303)


@app.post("/ato/{system_id}/{doc_type}/action")
async def ato_workflow_action(request: Request, system_id: str, doc_type: str,
                              action: str = Form(...),
                              comment: str = Form("")):
    """Execute a workflow transition: submit | approve | reject | finalize | revise."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if doc_type not in ATO_DOC_TYPES:
        raise HTTPException(status_code=404)

    valid_actions = {"submit", "approve", "reject", "finalize", "revise"}
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail="Invalid action")

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        doc = (await session.execute(
            select(AtoDocument)
            .where(AtoDocument.system_id == system_id)
            .where(AtoDocument.doc_type == doc_type)
        )).scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found — save a draft first")

        role = await _get_user_role(request, session)
        ato_role = _ato_user_role(request, role)

        # Validate transition
        transitions = {
            "submit":   ("draft",      "in_review",  _ato_can_edit(ato_role, doc_type)),
            "approve":  ("in_review",  "approved",   _ato_can_review(ato_role, doc_type)),
            "reject":   ("in_review",  "draft",      _ato_can_review(ato_role, doc_type)),
            "finalize": ("approved",   "finalized",  _is_admin(request)),
            "revise":   ("finalized",  "draft",      _is_admin(request) or _ato_can_edit(ato_role, doc_type)),
        }
        expected_status, new_status, authorized = transitions[action]

        if doc.status != expected_status:
            raise HTTPException(status_code=400, detail=f"Cannot {action}: document is in '{doc.status}' status")
        if not authorized:
            raise HTTPException(status_code=403, detail=f"Not authorized to {action} this document type")

        from_status = doc.status

        # Snapshot version on submit/approve/finalize
        if action in ("submit", "approve", "finalize"):
            snap = AtoDocumentVersion(
                document_id  = doc.id,
                version      = doc.version,
                content_snap = doc.content,
                from_status  = from_status,
                to_status    = new_status,
                changed_by   = user,
                change_note  = comment or f"{action} by {user}",
            )
            session.add(snap)

        # Bump version on revise
        if action == "revise":
            doc.version = _ato_next_version(doc.version)

        doc.status     = new_status
        doc.updated_at = datetime.now(timezone.utc)

        # Workflow event
        ev = AtoWorkflowEvent(
            document_id = doc.id,
            from_status = from_status,
            to_status   = new_status,
            actor       = user,
            actor_role  = ato_role,
            comment     = comment or None,
        )
        session.add(ev)

        await _log_audit(session, user, action.upper(), "ato_document", f"{system_id}/{doc_type}",
                         {"from": from_status, "to": new_status, "comment": comment})
        await session.commit()

        # Email notification on submit/approve/reject/finalize (fire-and-forget)
        try:
            sys_obj = await session.get(System, system_id)
            sys_name = sys_obj.name if sys_obj else system_id
            doc_name = ATO_DOC_TYPES[doc_type]["name"]
            action_labels = {
                "submit":   "submitted for review",
                "approve":  "approved",
                "reject":   "rejected — returned to draft",
                "finalize": "FINALIZED (ATO granted)",
                "revise":   "opened for revision",
            }
            log.info("ATO workflow: %s %s [%s] by %s (%s)", action_labels.get(action, action), doc_name, sys_name, user, ato_role)
        except Exception:
            pass

    return RedirectResponse(url=f"/ato/{system_id}/{doc_type}", status_code=303)
