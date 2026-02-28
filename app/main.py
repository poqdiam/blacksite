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
import hashlib
import hmac as _hmac
import html as _html
import json
import logging
import csv
import io
import os
import random
import re as _re
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
from sqlalchemy import func, or_, select, update, text, case as sa_case

from app.models import (
    Assessment, Candidate, ControlResult, ControlsMeta, DailyQuizActivity, QuizResponse,
    System, PoamItem, Risk, UserProfile, AuditLog, SystemAssignment, ControlEdit,
    SystemControl, Submission, RmfRecord,
    AtoDocument, AtoDocumentVersion, AtoWorkflowEvent,
    SystemTeam, TeamMembership, BcdrEvent, BcdrSignoff,
    Observation, InventoryItem, SystemConnection, Artifact,
    SecurityEvent,
    init_db, make_engine, make_session_factory
)
from app.updater    import load_catalog, update_if_needed
from app.parser     import parse_ssp
from app.assessor   import run_assessment, compute_combined_score, is_allstar
from app.quiz       import QUESTIONS, grade_quiz, grade_daily_quiz
from app.mailer     import send_report, forward_assessment, send_welcome_email
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

# ── App secret + role-shell HMAC signing ───────────────────────────────────────

def _get_app_secret() -> str:
    s = _cfg("app.secret_key", "")
    if s:
        return s
    _sf = Path("data/.app_secret")
    if _sf.exists():
        return _sf.read_text().strip()
    secret = os.urandom(32).hex()
    _sf.parent.mkdir(parents=True, exist_ok=True)
    _sf.write_text(secret)
    return secret

_APP_SECRET: str = ""


def _sign_shell(role: str) -> str:
    sig = _hmac.new(_APP_SECRET.encode(), role.encode(), "sha256").hexdigest()[:20]
    return f"{role}.{sig}"


def _verify_shell(signed: str) -> str | None:
    """Return the role if the signed cookie is valid, else None."""
    if not signed or "." not in signed:
        return None
    role, sig = signed.rsplit(".", 1)
    expected = _hmac.new(_APP_SECRET.encode(), role.encode(), "sha256").hexdigest()[:20]
    return role if _hmac.compare_digest(sig, expected) else None


# ── App factory ────────────────────────────────────────────────────────────────

engine       = make_engine(CONFIG)
SessionLocal = make_session_factory(engine)
templates    = Jinja2Templates(directory="templates")
templates.env.filters["fromjson"] = lambda s: (json.loads(s) if s else {})

# ── Control statement / guidance formatter ─────────────────────────────────────
_CTRL_PARAM_RE = _re.compile(r'\{\{\s*insert:\s*param,\s*([^}]+?)\s*\}\}')
# Match control IDs like AC-1, SI-3, SI-3 (2); trailing (?!\w) avoids matching inside words
_CTRL_REF_RE   = _re.compile(r'\b([A-Z]{2}-\d+(?:\s*\(\d+\))?)(?!\w)')


def _fmt_ctrl_text(text: str, params: list = None) -> str:
    """Format NIST control text for display.
    - HTML-escapes input
    - Renders {{ insert: param, id }} as styled parameter placeholders
    - Linkifies control cross-references (AC-1, AU-2, SI-3 (2) etc.)
    Returns an HTML string (mark safe before output).
    """
    if not text:
        return ""
    # Build param id → label map
    param_labels: dict = {}
    if params:
        for p in params:
            pid = p.get("id", "")
            if pid:
                param_labels[pid] = p.get("label", pid)

    # HTML-escape plain text (preserves newlines and spaces)
    escaped = _html.escape(text)

    # Replace {{ insert: param, id }} with styled spans
    def _param_sub(m: _re.Match) -> str:
        pid   = m.group(1).strip()
        label = param_labels.get(pid, pid.replace("_", " "))
        safe_pid = _html.escape(pid)
        safe_lbl = _html.escape(label)
        return (
            f'<span class="ctrl-param" title="{safe_pid}">'
            f'<span class="ctrl-param-bracket">[</span>'
            f'<span class="ctrl-param-inner">{safe_lbl}</span>'
            f'<span class="ctrl-param-bracket">]</span>'
            f'</span>'
        )
    escaped = _CTRL_PARAM_RE.sub(_param_sub, escaped)

    # Linkify control references (only in text nodes, not inside HTML tags)
    def _ref_sub(m: _re.Match) -> str:
        full = m.group(0)
        # Normalise: "SI-3 (2)" → "si-3.2", "AC-2" → "ac-2"
        cid = _re.sub(r'\s*\((\d+)\)', r'.\1', full).lower()
        return f'<a href="/controls/{cid}" class="ctrl-ref">{full}</a>'

    # Apply only outside of HTML tags already inserted
    parts_out: list[str] = []
    last = 0
    for tag in _re.finditer(r'<[^>]+>', escaped):
        segment = escaped[last:tag.start()]
        parts_out.append(_CTRL_REF_RE.sub(_ref_sub, segment))
        parts_out.append(tag.group(0))
        last = tag.end()
    parts_out.append(_CTRL_REF_RE.sub(_ref_sub, escaped[last:]))
    return "".join(parts_out)


templates.env.filters["fmt_ctrl"] = _fmt_ctrl_text

CATALOG: dict = {}

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global CATALOG, _APP_SECRET
    await init_db(engine)
    _APP_SECRET = _get_app_secret()
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
    # Auto-purge removed users older than 1 year
    try:
        async with SessionLocal() as s:
            cutoff = datetime.now(timezone.utc) - timedelta(days=365)
            await s.execute(
                text("DELETE FROM user_profiles WHERE status='removed' AND removed_at < :cutoff"),
                {"cutoff": cutoff}
            )
            await s.commit()
    except Exception:
        pass
    # Auto-purge soft-deleted systems older than 1 year
    try:
        async with SessionLocal() as s:
            cutoff = datetime.now(timezone.utc) - timedelta(days=365)
            await s.execute(
                text("DELETE FROM systems WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff"),
                {"cutoff": cutoff}
            )
            await s.commit()
    except Exception:
        pass
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


# ── SIEM Middleware ─────────────────────────────────────────────────────────────

@app.middleware("http")
async def siem_middleware(request: Request, call_next):
    resp = await call_next(request)
    path = request.url.path
    code = resp.status_code
    should_log = (code >= 400 or path.startswith("/admin") or
                  any(x in path for x in ["login", "auth", "switch-role", "shell", "exit-shell"]))
    if should_log and not path.startswith("/static"):
        sev   = "info"
        etype = "http"
        if code == 401:   etype, sev = "failed_auth",   "medium"
        elif code == 403: etype, sev = "access_denied",  "medium"
        elif code >= 500: etype, sev = "server_error",   "high"
        elif path.startswith("/admin"): sev = "low"
        try:
            async with SessionLocal() as s:
                s.add(SecurityEvent(
                    event_type  = etype,
                    severity    = sev,
                    remote_ip   = request.headers.get("X-Forwarded-For", ""),
                    remote_user = request.headers.get("Remote-User", ""),
                    method      = request.method,
                    path        = path,
                    status_code = code,
                    user_agent  = (request.headers.get("User-Agent", ""))[:200],
                ))
                await s.commit()
        except Exception:
            pass
    return resp


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
    is_admin_user = _is_admin(request)
    shell_cookie  = _verify_shell(request.cookies.get("bsv_role_shell", "")) or ""
    # For admin users we can determine role shell state without a DB call.
    # Non-admin users: _full_ctx will override these with accurate DB-derived values.
    if is_admin_user:
        shell_allowed_roles = sorted(_VALID_SHELL_ROLES)
        is_role_view        = shell_cookie in _VALID_SHELL_ROLES
        user_role_ctx       = shell_cookie if is_role_view else "admin"
    else:
        shell_allowed_roles = []          # _full_ctx overrides
        is_role_view        = False       # _full_ctx overrides
        user_role_ctx       = "employee"  # _full_ctx overrides
    return {
        "app_name":           _cfg("app.name", "BLACKSITE"),
        "brand":              _cfg("app.brand", "TheKramerica"),
        "tagline":            _cfg("app.tagline", "Security Assessment Platform"),
        "remote_user":        user,
        "display_name":       display_name,
        "is_admin":           is_admin_user,
        "view_mode":          _view_mode(request),
        "employees":          employees,
        "role_view_cookie":   request.cookies.get("bsv_role_view", ""),
        "role_shell_cookie":  shell_cookie,
        "shell_allowed_roles": shell_allowed_roles,
        "is_role_view":       is_role_view,
        "user_role":          user_role_ctx,
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
    """Returns list of system_ids the current user can access (excludes soft-deleted)."""
    if _is_admin(request):
        result = await session.execute(select(System.id).where(System.deleted_at.is_(None)))
        return [r[0] for r in result.all()]
    user = request.headers.get("Remote-User", "")
    result = await session.execute(
        select(SystemAssignment.system_id)
        .where(SystemAssignment.remote_user == user)
    )
    return [r[0] for r in result.all()]


_VALID_SHELL_ROLES = {
    "ao", "issm", "isso", "sca", "system_owner", "auditor", "bcdr", "employee",
    "ciso", "pen_tester", "data_owner", "pmo", "incident_responder",
}


async def _get_user_role(request: Request, session) -> str:
    """Return the RBAC role string for the current user.
    Admins can shell into any non-admin role via bsv_role_shell cookie.
    Non-admin users (AO/ISSM) can shell into lower roles.
    Frozen/removed accounts return 'blocked'.
    """
    if _is_admin(request):
        shell = _verify_shell(request.cookies.get("bsv_role_shell", "")) or ""
        if shell in _VALID_SHELL_ROLES:
            return shell   # admin shelling into this role
        return "admin"
    user = request.headers.get("Remote-User", "")
    if not user:
        return "anonymous"
    row = (await session.execute(
        select(UserProfile.role, UserProfile.status).where(UserProfile.remote_user == user)
    )).one_or_none()
    if row and (row[1] or "active") in ("frozen", "removed"):
        return "blocked"
    actual = (row[0] if row else None) or "employee"
    # Non-admin users (AO/ISSM) can shell into lower roles
    shell = _verify_shell(request.cookies.get("bsv_role_shell", "")) or ""
    if shell in ROLE_CAN_VIEW_DOWN.get(actual, []):
        return shell
    return actual


# Role hierarchy: which roles can shell into lower-tier roles.
# Shelled users lose ALL higher-level permissions for the duration of the shell.
_LOWER_THAN_ISSO = ["system_owner", "auditor", "bcdr", "pen_tester",
                    "data_owner", "pmo", "incident_responder", "employee"]
ROLE_CAN_VIEW_DOWN: dict = {
    "admin":  sorted(_VALID_SHELL_ROLES),
    "ao":     ["ciso", "issm", "isso", "sca"] + _LOWER_THAN_ISSO,
    "ciso":   ["issm", "isso", "sca"] + _LOWER_THAN_ISSO,
    "issm":   ["isso", "sca"] + _LOWER_THAN_ISSO,
    "isso":   _LOWER_THAN_ISSO,
    "sca":    ["employee"],
}


def _require_role(role: str, allowed: list):
    """Raise 403 if role not in allowed list."""
    if role not in allowed:
        raise HTTPException(status_code=403, detail=f"Role '{role}' cannot access this resource")


async def _full_ctx(request: Request, session, **extra) -> dict:
    """Extended template context including user_role for sidebar rendering.
    Respects bsv_role_shell cookie for role shell switching.
    """
    actual_role = await _get_user_role(request, session)

    # Blocked accounts get 403 on all main routes
    if actual_role == "blocked":
        raise HTTPException(status_code=403, detail="Account suspended.")

    # Shell is active when the cookie resolves to a different role than native
    # For admins, shell_role IS their current role when shelling
    if _is_admin(request):
        shell   = _verify_shell(request.cookies.get("bsv_role_shell", "")) or ""
        is_shell = shell in _VALID_SHELL_ROLES
        display_role = shell if is_shell else "admin"
        native_role  = "admin"
    else:
        # For non-admins: actual_role may already be the shell role
        native_row = (await session.execute(
            select(UserProfile.role).where(
                UserProfile.remote_user == request.headers.get("Remote-User", "")
            )
        )).scalar_one_or_none()
        native_role  = native_row or "employee"
        display_role = actual_role
        is_shell     = actual_role != native_role

    # Touch last_login for non-anonymous/blocked users
    user = request.headers.get("Remote-User", "")
    if user and actual_role not in ("anonymous", "blocked"):
        try:
            await session.execute(
                text("UPDATE user_profiles SET last_login=:ts WHERE remote_user=:u"),
                {"ts": datetime.now(timezone.utc), "u": user}
            )
            await session.commit()
        except Exception:
            pass  # non-fatal

    # Query user's team memberships for sidebar Teams widget
    user_teams = []
    if user:
        try:
            teams_result = await session.execute(
                select(SystemTeam)
                .join(TeamMembership, TeamMembership.team_id == SystemTeam.id)
                .where(TeamMembership.remote_user == user)
                .order_by(SystemTeam.name)
                .limit(10)
            )
            user_teams = list(teams_result.scalars().all())
        except Exception:
            pass  # TeamMembership table may not exist yet on first run

    # Roles this user can shell into (overrides the admin-only fallback from _tpl_ctx)
    shell_allowed_roles = ROLE_CAN_VIEW_DOWN.get(native_role, [])

    return {
        "request":             request,
        **_tpl_ctx(request),
        "user_role":           display_role,
        "actual_role":         native_role,
        "is_role_view":        is_shell,
        "user_teams":          user_teams,
        "now":                 datetime.now(timezone.utc),
        "shell_allowed_roles": shell_allowed_roles,  # overrides _tpl_ctx value for non-admins
        **extra,
    }


# ── POA&M status definitions (DHS Attachment H aligned) ──────────────────────────
# Lifecycle: draft → open → in_progress → blocked → ready_for_review
#            → closed_verified | deferred_waiver | accepted_risk | false_positive
POAM_STATUSES = [
    "draft", "open", "in_progress", "blocked", "ready_for_review",
    "closed_verified", "deferred_waiver", "accepted_risk", "false_positive",
]
POAM_ACTIVE_STATUSES  = {"open", "in_progress", "blocked", "ready_for_review", "draft"}
POAM_CLOSED_STATUSES  = {"closed_verified", "deferred_waiver", "accepted_risk", "false_positive"}

POAM_STATUS_LABELS = {
    "draft":           "Draft",
    "open":            "Open",
    "in_progress":     "In Progress",
    "blocked":         "Blocked",
    "ready_for_review":"Ready for Review",
    "closed_verified": "Closed Verified",
    "deferred_waiver": "Deferred by Waiver",
    "accepted_risk":   "Accepted Risk",
    "false_positive":  "False Positive",
}


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
    "ADD":         {"name": "Authorization Decision Document",        "short": "ADD/ATO",     "owner_roles": ["admin"],               "reviewer_roles": ["admin"],              "rmf_step": "authorize",   "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    # ── FedRAMP Preparation (12 new) ──────────────────────────────────────────
    "RAR_HIGH":     {"name": "FedRAMP High Readiness Assessment Report Template",             "short": "RAR High",     "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "prepare",     "category": "preparation",   "fedramp_doc": True,  "guidance_only": False},
    "RAR_MOD":      {"name": "FedRAMP Moderate Readiness Assessment Report Template",         "short": "RAR Mod",      "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "prepare",     "category": "preparation",   "fedramp_doc": True,  "guidance_only": False},
    "CSP_PLAYBOOK": {"name": "CSP Authorization Playbook",                                    "short": "CSP PB",       "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "prepare",     "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "CRYPTO_POLICY":{"name": "FedRAMP Policy for Cryptographic Module Selection",             "short": "Crypto Pol.",  "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "implement",   "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "AUTH_BOUNDARY":{"name": "FedRAMP Authorization Boundary Guidance",                       "short": "Auth Bound.",  "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "categorize",  "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "TIMELINESS":   {"name": "Timeliness and Accuracy of Testing Requirements",               "short": "Timeliness",   "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "PKG_ACCESS":   {"name": "FedRAMP Package Access Request Form",                           "short": "Pkg Access",   "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "authorize",   "category": "preparation",   "fedramp_doc": True,  "guidance_only": False},
    "REUSE_GUIDE":  {"name": "Reusing Authorizations for Cloud Products Quick Guide",          "short": "Reuse Guide",  "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "prepare",     "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "AGENCY_PB":    {"name": "Agency Authorization Playbook",                                 "short": "Agency PB",    "owner_roles": ["admin"],               "reviewer_roles": ["admin"],              "rmf_step": "authorize",   "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "3PAO_PERF":    {"name": "3PAO Obligations and Performance Guide",                        "short": "3PAO Perf.",   "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "3PAO_RAR_GUIDE":{"name": "3PAO Readiness Assessment Report Guide",                       "short": "3PAO RAR",     "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "prepare",     "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    "BRANDING":     {"name": "Branding Guidance",                                             "short": "Branding",     "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "prepare",     "category": "preparation",   "fedramp_doc": True,  "guidance_only": True},
    # ── FedRAMP Authorization Package Appendices (14 new) ─────────────────────
    "PKG_CHECKLIST":{"name": "FedRAMP Initial Authorization Package Checklist",               "short": "Pkg Checklist","owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "authorize",   "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_A_HIGH":{"name": "SSP Appendix A — High FedRAMP Security Controls",             "short": "SSP App-A Hi", "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "select",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_A_MOD":{"name": "SSP Appendix A — Moderate FedRAMP Security Controls",          "short": "SSP App-A Mod","owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "select",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_A_LOW":{"name": "SSP Appendix A — Low FedRAMP Security Controls",               "short": "SSP App-A Low","owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "select",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_A_LI": {"name": "SSP Appendix A — LI-SaaS FedRAMP Security Controls",          "short": "SSP App-A LI", "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "select",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_J":    {"name": "SSP Appendix J — CIS and CRM Workbook",                        "short": "SSP App-J",    "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "select",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_M":    {"name": "SSP Appendix M — Integrated Inventory Workbook",               "short": "SSP App-M",    "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "implement",   "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SSP_APP_Q":    {"name": "SSP Appendix Q — Cryptographic Modules Table",                 "short": "SSP App-Q",    "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin","auditor"],    "rmf_step": "implement",   "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SAR_APP_A":    {"name": "SAR Appendix A — FedRAMP Risk Exposure Table",                 "short": "SAR App-A",    "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SAR_APP_B_HIGH":{"name": "SAR Appendix B — High Security RTM",                          "short": "SAR App-B Hi", "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SAR_APP_B_MOD":{"name": "SAR Appendix B — Moderate Security RTM",                       "short": "SAR App-B Mod","owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "SAR_APP_B_LOW":{"name": "SAR Appendix B — Low Security RTM",                            "short": "SAR App-B Low","owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "ATO_LETTER":   {"name": "FedRAMP ATO Letter Template",                                   "short": "ATO Letter",   "owner_roles": ["admin"],               "reviewer_roles": ["admin"],              "rmf_step": "authorize",   "category": "authorization", "fedramp_doc": True,  "guidance_only": False},
    "FR_BASELINE":  {"name": "FedRAMP Security Controls Baseline",                            "short": "FR Baseline",  "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "select",      "category": "authorization", "fedramp_doc": True,  "guidance_only": True},
    # ── Continuous Monitoring (7 new) ─────────────────────────────────────────
    "CONMON_MONTHLY":{"name": "Continuous Monitoring Monthly Executive Summary",              "short": "ConMon Monthly","owner_roles": ["system_owner","admin"],"reviewer_roles": ["admin"],              "rmf_step": "monitor",     "category": "conmon",        "fedramp_doc": True,  "guidance_only": False},
    "CONMON_DELIV": {"name": "FedRAMP Continuous Monitoring Deliverables Template",           "short": "ConMon Deliv.", "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor",     "category": "conmon",        "fedramp_doc": True,  "guidance_only": False},
    "ANNUAL_CTRL_SEL":{"name": "Annual Assessment Controls Selection Worksheet",              "short": "Ann. Ctrl Sel.","owner_roles": ["auditor","admin"],     "reviewer_roles": ["admin"],              "rmf_step": "monitor",     "category": "conmon",        "fedramp_doc": True,  "guidance_only": False},
    "PENTEST_GUIDE":{"name": "Penetration Test Guidance",                                     "short": "Pentest Guide","owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "assess",      "category": "conmon",        "fedramp_doc": True,  "guidance_only": True},
    "VULN_CONTAINERS":{"name": "Vulnerability Scanning Requirements for Containers",          "short": "Vuln Cont.",   "owner_roles": ["auditor","admin"],      "reviewer_roles": ["admin"],              "rmf_step": "monitor",     "category": "conmon",        "fedramp_doc": True,  "guidance_only": True},
    "VULN_DEVIATION":{"name": "FedRAMP Vulnerability Deviation Request Form",                 "short": "Vuln Dev.",    "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor",     "category": "conmon",        "fedramp_doc": True,  "guidance_only": False},
    "CONMON_PLAYBOOK":{"name": "Continuous Monitoring Playbook",                              "short": "ConMon PB",    "owner_roles": ["system_owner","admin"], "reviewer_roles": ["admin"],              "rmf_step": "monitor",     "category": "conmon",        "fedramp_doc": True,  "guidance_only": True},
}

# Back-fill category/fedramp_doc/guidance_only on original 19 entries that predate Phase 12
_ORIGINAL_CATEGORIES = {
    "FIPS199":     ("core", False), "SSP":   ("core", False), "SAP":       ("core", False),
    "SAR":         ("core", False), "POAM":  ("core", False), "ABD":       ("core", False),
    "NET_DIAGRAM": ("core", False), "HW_INV":("core", False), "SW_INV":    ("core", False),
    "IRP":         ("core", False), "CP":    ("core", False), "CPT":       ("core", False),
    "CMP":         ("core", False), "CONMON":("core", False), "PTA":       ("core", False),
    "PIA":         ("core", False), "ROB":   ("core", False), "ISA":       ("core", False),
    "ADD":         ("authorization", False),
}
for _k, (_cat, _go) in _ORIGINAL_CATEGORIES.items():
    if _k in ATO_DOC_TYPES:
        ATO_DOC_TYPES[_k].setdefault("category", _cat)
        ATO_DOC_TYPES[_k].setdefault("fedramp_doc", True)
        ATO_DOC_TYPES[_k].setdefault("guidance_only", _go)

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


# ── Help Center ────────────────────────────────────────────────────────────────

@app.get("/help")
async def help_center(request: Request):
    async with SessionLocal() as session:
        ctx = await _full_ctx(request, session)
    return templates.TemplateResponse("help_center.html", {"request": request, **ctx})


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


@app.get("/switch-role-view")
async def switch_role_view(request: Request, role: str = ""):
    """Switch to a role shell view. Admins can shell into any role; AO/ISSM into lower roles."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    ref = request.headers.get("Referer", "/systems")
    response = RedirectResponse(url=ref, status_code=303)
    native = "admin" if _is_admin(request) else None
    async with SessionLocal() as session:
        actual_role = await _get_user_role(request, session)
        if native is None:
            native = actual_role
        allowed = ROLE_CAN_VIEW_DOWN.get(native, [])
        if role != "reset" and role in allowed:
            await _log_audit(session, user, "UPDATE", "role_shell", user,
                             {"action": "set_shell", "target_role": role,
                              "_effective_role": role, "_real_role": native})
            await session.commit()
    if role == "reset" or role not in allowed:
        response.delete_cookie("bsv_role_shell")
        response.delete_cookie("bsv_role_view")  # cleanup old cookie
    else:
        response.set_cookie("bsv_role_shell", _sign_shell(role), httponly=True, samesite="lax")
        response.delete_cookie("bsv_role_view")  # cleanup old cookie
    return response


@app.get("/exit-shell")
async def exit_shell(request: Request):
    """Exit role shell — return to the page the user came from."""
    ref = request.headers.get("Referer", "/")
    response = RedirectResponse(url=ref, status_code=303)
    response.delete_cookie("bsv_role_shell")
    response.delete_cookie("bsv_role_view")
    return response


# ── Upload ─────────────────────────────────────────────────────────────────────

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    async with SessionLocal() as _chk_session:
        _chk_role = await _get_user_role(request, _chk_session)
    if not _is_admin(request) and _chk_role != "sca":
        raise HTTPException(status_code=403, detail="SSP upload is restricted to administrators and SCA users")
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
    async with SessionLocal() as _chk_session:
        _chk_role = await _get_user_role(request, _chk_session)
    if not _is_admin(request) and _chk_role != "sca":
        raise HTTPException(status_code=403, detail="SSP upload is restricted to administrators and SCA users")
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
# AO intentionally excluded from audit log: requires ISSM/auditor/admin clearance.
# Update the permissions matrix — this was a documentation error, not a code gap.

@app.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit(request: Request, days: str = "30",
                      hide_view: str = "1", page: int = 1, per_page: int = 25):
    async with SessionLocal() as _chk_session:
        _chk_role = await _get_user_role(request, _chk_session)
    if not _is_admin(request) and _chk_role not in ("issm", "auditor"):
        raise HTTPException(status_code=403)

    try:
        days_int = int(days)
    except ValueError:
        days_int = 30

    per_page = max(10, min(per_page, 100))
    page     = max(1, page)
    offset   = (page - 1) * per_page

    async with SessionLocal() as session:
        def _base_q():
            q = select(AuditLog)
            if days_int > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_int)
                q = q.where(AuditLog.timestamp >= cutoff)
            if hide_view == "1":
                q = q.where(AuditLog.action != "VIEW")
            return q

        total = (await session.execute(
            select(func.count()).select_from(_base_q().subquery())
        )).scalar() or 0
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)

        rows    = await session.execute(
            _base_q().order_by(AuditLog.timestamp.desc()).offset(offset).limit(per_page)
        )
        entries = rows.scalars().all()
        role = await _get_user_role(request, session)

    return templates.TemplateResponse("audit_log.html", {
        "request":     request,
        "entries":     entries,
        "days":        days_int,
        "hide_view":   hide_view,
        "user_role":   role,
        "page":        page,
        "total_pages": total_pages,
        "per_page":    per_page,
        "total":       total,
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
                select(System).where(System.deleted_at.is_(None)).order_by(System.name)
            )
            systems = rows.scalars().all()
        else:
            # Non-admins only see systems they are assigned to (deleted excluded via _user_system_ids)
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

        # Build set of system_ids that have at least one assignment (for sort/filter)
        assigned_ids_rows = await session.execute(
            select(SystemAssignment.system_id).distinct()
        )
        assigned_sys_ids = {r[0] for r in assigned_ids_rows.all()}

        ctx = await _full_ctx(request, session,
            systems      = systems,
            authorized_ct  = sum(1 for s in systems if s.auth_status == "authorized"),
            in_progress_ct = sum(1 for s in systems if s.auth_status == "in_progress"),
            expired_ct     = sum(1 for s in systems if s.auth_status == "expired"),
            not_auth_ct    = sum(1 for s in systems if s.auth_status == "not_authorized"),
            assigned_sys_ids = assigned_sys_ids,
        )

    return templates.TemplateResponse("systems.html", ctx)


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

        # Phase 12 quick-link counts
        inv_count = (await session.execute(
            select(func.count(InventoryItem.id)).where(InventoryItem.system_id == system_id)
        )).scalar() or 0
        conn_count = (await session.execute(
            select(func.count(SystemConnection.id)).where(SystemConnection.system_id == system_id)
        )).scalar() or 0
        art_count = (await session.execute(
            select(func.count(Artifact.id)).where(Artifact.system_id == system_id)
        )).scalar() or 0
        obs_open_count = (await session.execute(
            select(func.count(Observation.id))
            .where(Observation.system_id == system_id)
            .where(Observation.status == "open")
        )).scalar() or 0

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
        "inv_count":               inv_count,
        "conn_count":              conn_count,
        "art_count":               art_count,
        "obs_open_count":          obs_open_count,
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
    effective_role = _verify_shell(request.cookies.get("bsv_role_shell", "")) or "admin"
    async with SessionLocal() as session:
        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404)
        sys.deleted_at = datetime.now(timezone.utc)
        sys.deleted_by = user
        await _log_audit(session, user, "DELETE", "system", system_id,
                         {"name": sys.name, "soft_delete": True,
                          "_effective_role": effective_role, "_real_role": "admin"})
        await session.commit()

    return RedirectResponse(url="/systems", status_code=303)


# ── Archived Systems (Phase 15) ────────────────────────────────────────────────

@app.get("/admin/systems/archived", response_class=HTMLResponse)
async def admin_systems_archived(request: Request):
    """List soft-deleted systems. Admin only."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as session:
        rows = await session.execute(
            select(System)
            .where(System.deleted_at.isnot(None))
            .order_by(System.deleted_at.desc())
        )
        archived = rows.scalars().all()
    return templates.TemplateResponse("archived_systems.html", {
        "request":  request,
        "archived": archived,
        **_tpl_ctx(request),
    })


@app.post("/admin/systems/{system_id}/restore")
async def admin_system_restore(request: Request, system_id: str):
    """Restore a soft-deleted system. Admin only."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    user = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        sys = await session.get(System, system_id)
        if not sys or sys.deleted_at is None:
            raise HTTPException(status_code=404)
        sys.deleted_at = None
        sys.deleted_by = None
        await _log_audit(session, user, "UPDATE", "system", system_id,
                         {"name": sys.name, "action": "restore"})
        await session.commit()
    return RedirectResponse(url="/admin/systems/archived", status_code=303)


@app.post("/admin/systems/{system_id}/purge")
async def admin_system_purge(request: Request, system_id: str):
    """Permanently delete a soft-deleted system. Admin only."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    user = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        sys = await session.get(System, system_id)
        if not sys or sys.deleted_at is None:
            raise HTTPException(status_code=404)
        await _log_audit(session, user, "DELETE", "system", system_id,
                         {"name": sys.name, "action": "hard_purge"})
        await session.delete(sys)
        await session.commit()
    return RedirectResponse(url="/admin/systems/archived", status_code=303)


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
    try:
        PAGE_SIZE = max(10, min(int(request.query_params.get("per_page", 10)), 100))
    except ValueError:
        PAGE_SIZE = 10
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
                base_q = base_q.where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
            elif status_filter == "closed":
                base_q = base_q.where(PoamItem.status.in_(list(POAM_CLOSED_STATUSES)))
            else:
                base_q = base_q.where(PoamItem.status == status_filter)
            if severity_filter:
                base_q = base_q.where(PoamItem.severity == severity_filter)
            if system_filter:
                base_q = base_q.where(PoamItem.system_id == system_filter)
            return base_q

        # Stat counts (indexed queries, no full table scan for rendering)
        open_statuses = list(POAM_ACTIVE_STATUSES)
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
        "request":          request,
        "page_items":       page_items,
        "total_open":       total_open,
        "crit_high_ct":     crit_high_ct,
        "overdue_ct":       overdue_ct,
        "due_soon_ct":      due_soon_ct,
        "closed_month_ct":  closed_month_ct,
        "sev_counts":       sev_counts,
        "aging":            aging,
        "systems_map":      systems_map,
        "all_sys":          all_sys,
        "status_filter":    status_filter,
        "severity_filter":  severity_filter,
        "system_filter":    system_filter,
        "page":             page,
        "total_pages":      total_pages,
        "total_filtered":   total_filtered,
        "today_str":        today_str,
        "week_str":         week_str,
        "poam_statuses":    POAM_STATUSES,
        "poam_status_labels": POAM_STATUS_LABELS,
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
            .where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
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
    VALID_STATUSES     = set(POAM_STATUSES)
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
        "request":            request,
        "item":               None,
        "systems":            systems,
        "assessment_id":      assessment_id,
        "control_id":         control_id,
        "action":             "/poam",
        "poam_statuses":      POAM_STATUSES,
        "poam_status_labels": POAM_STATUS_LABELS,
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
        "request":            request,
        "item":               item,
        "systems":            systems,
        "linked_system":      linked_system,
        "action":             f"/poam/{item_id}/update",
        "poam_statuses":      POAM_STATUSES,
        "poam_status_labels": POAM_STATUS_LABELS,
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

        new_status = str(form.get("status", item.status))
        if new_status not in POAM_STATUSES:
            new_status = item.status
        item.system_id            = str(form.get("system_id", "")).strip() or None
        item.weakness_name        = str(form.get("weakness_name", item.weakness_name)).strip()
        item.weakness_description = str(form.get("weakness_description", "")).strip() or None
        item.detection_source     = str(form.get("detection_source", "")).strip() or None
        item.severity             = str(form.get("severity", item.severity))
        item.responsible_party    = str(form.get("responsible_party", "")).strip() or None
        item.resources_required   = str(form.get("resources_required", "")).strip() or None
        item.scheduled_completion = str(form.get("scheduled_completion", "")).strip() or None
        item.status               = new_status
        item.remediation_plan     = str(form.get("remediation_plan", "")).strip() or None
        item.root_cause           = str(form.get("root_cause", "")).strip() or None
        item.closure_evidence     = str(form.get("closure_evidence", "")).strip() or None
        item.risk_accept_review   = str(form.get("risk_accept_review", "")).strip() or None
        item.completion_date      = str(form.get("completion_date", "")).strip() or None
        item.comments             = str(form.get("comments", "")).strip() or None
        item.updated_at           = datetime.now(timezone.utc)
        if new_status == "closed_verified" and not item.completion_date:
            item.completion_date = date.today().isoformat()

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
    if new_status not in POAM_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    async with SessionLocal() as session:
        row = await session.execute(select(PoamItem).where(PoamItem.id == item_id))
        item = row.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404)
        old_status = item.status
        item.status = new_status
        item.updated_at = datetime.now(timezone.utc)
        if new_status == "closed_verified" and not item.completion_date:
            item.completion_date = date.today().isoformat()
        await _log_audit(session, user, "UPDATE", "poam", item_id,
                         {"status": f"{old_status}→{new_status}"})
        await session.commit()

    return JSONResponse({"ok": True, "status": new_status,
                         "label": POAM_STATUS_LABELS.get(new_status, new_status)})


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
    try:
        PAGE_SIZE = max(10, min(int(request.query_params.get("per_page", 10)), 100))
    except ValueError:
        PAGE_SIZE = 10
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
            q = q.where(System.deleted_at.is_(None))
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
        stmt = ctrl.get("statement") or ctrl.get("text", "")
        items.append({
            "id":        ctrl_id,
            "family":    ctrl.get("family", ctrl_id.split("-")[0].upper()),
            "title":     ctrl.get("title", ""),
            "text":      stmt,        # legacy alias kept for templates
            "statement": stmt,
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
async def controls_catalog(request: Request, family: str = "", q: str = "",
                            page: int = 1, per_page: int = 25):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    all_items = _catalog_list()
    families  = _ctrl_families()

    if family:
        all_items = [c for c in all_items if c["family"] == family.upper()]
    if q:
        ql = q.lower()
        all_items = [c for c in all_items if ql in c["id"].lower() or ql in c["title"].lower() or ql in c.get("statement", "").lower()]

    per_page = max(10, min(per_page, 100))
    page     = max(1, page)
    total    = len(all_items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page     = min(page, total_pages)
    offset   = (page - 1) * per_page
    items    = all_items[offset : offset + per_page]

    return templates.TemplateResponse("controls.html", {
        "request":     request,
        "items":       items,
        "families":    families,
        "family":      family.upper(),
        "q":           q,
        "total":       len(CATALOG),
        "filtered_total": total,
        "page":        page,
        "total_pages": total_pages,
        "per_page":    per_page,
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

        auth_type = str(form.get("authorization_type", "ATO")).strip().upper()
        if auth_type not in ("ATO", "ATP", "IATO", "EIS"):
            auth_type = "ATO"

        # Determine term limits and EIS flag
        term_months: Optional[int] = None
        term_expires_at: Optional[str] = None
        is_eis_flag = False

        if auth_type == "ATP":
            term_months = 12
            term_expires_at = (date.today() + timedelta(days=365)).isoformat()
        elif auth_type == "IATO":
            term_months = 6
            term_expires_at = (date.today() + timedelta(days=183)).isoformat()
        elif auth_type == "EIS":
            is_eis_flag = True

        sub = Submission(
            system_id          = system_id,
            submission_type    = str(form.get("submission_type", "initial")),
            authorization_type = auth_type,
            term_months        = term_months,
            term_expires_at    = term_expires_at,
            status             = "submitted",
            package_notes      = str(form.get("package_notes", "")).strip() or None,
            submitted_by       = user,
            submitted_at       = datetime.now(timezone.utc),
            controls_total     = total_ct,
            controls_impl      = stats["implemented"] + stats["inherited"],
            controls_na        = stats["not_applicable"],
            controls_gap       = stats["not_started"] + stats["in_progress"],
            created_by         = user,
        )
        session.add(sub)

        # Update system auth_status and EIS flag
        if is_eis_flag:
            system.is_eis = True
        else:
            system.auth_status = "in_progress"
        system.updated_at = datetime.now(timezone.utc)

        await _log_audit(session, user, "CREATE", "submission", sub.id,
                         {"system_id": system_id, "type": sub.submission_type,
                          "authorization_type": auth_type})
        await session.commit()

    return RedirectResponse(url=f"/submissions/{sub.id}", status_code=303)


@app.get("/submissions", response_class=HTMLResponse)
async def submissions_list(request: Request, page: int = 1, per_page: int = 10):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    per_page = max(10, min(per_page, 100))
    page     = max(1, page)
    offset   = (page - 1) * per_page

    async with SessionLocal() as session:
        def _sub_q():
            if _is_admin(request):
                return select(Submission).order_by(Submission.created_at.desc())
            sys_ids = []  # will be resolved in-scope
            return select(Submission).order_by(Submission.created_at.desc())

        if _is_admin(request):
            total = (await session.execute(
                select(func.count(Submission.id))
            )).scalar() or 0
            sub_rows = await session.execute(
                select(Submission).order_by(Submission.created_at.desc())
                .offset(offset).limit(per_page)
            )
        else:
            sys_ids = await _user_system_ids(request, session)
            total = (await session.execute(
                select(func.count(Submission.id))
                .where(Submission.system_id.in_(sys_ids))
            )).scalar() or 0
            sub_rows = await session.execute(
                select(Submission)
                .where(Submission.system_id.in_(sys_ids))
                .order_by(Submission.created_at.desc())
                .offset(offset).limit(per_page)
            )
        submissions = list(sub_rows.scalars().all())
        total_pages = max(1, (total + per_page - 1) // per_page)

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
        "page":        page,
        "total_pages": total_pages,
        "per_page":    per_page,
        "total":       total,
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

        # System counts for static banner
        sys_total  = (await session.execute(select(func.count(System.id)))).scalar() or 0
        ato_active = (await session.execute(
            select(func.count(System.id)).where(System.auth_status == "authorized")
        )).scalar() or 0

    # Static platform context items — always shown
    static_items = [
        {"text": f"BLACKSITE GRC Platform  ·  NIST SP 800-53 Rev 5  ·  1,196 controls indexed  ·  {sys_total} system{'s' if sys_total!=1 else ''} registered", "level": "info"},
        {"text": "RMF 7-Step Lifecycle  ·  Prepare  →  Categorize  →  Select  →  Implement  →  Assess  →  Authorize  →  Monitor", "level": "info"},
        {"text": f"FIPS 199 Security Categorization  ·  Confidentiality · Integrity · Availability  ·  {ato_active} ATO{'s' if ato_active!=1 else ''} active", "level": "info"},
        {"text": "OMB Circular A-130  ·  FISMA 2014  ·  NIST SP 800-37r2  ·  NIST SP 800-171  ·  FedRAMP-aligned", "level": "info"},
    ]
    items = static_items + items

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
                "text": f"CISA KEV  ·  {v['cveID']} · {v.get('vendorProject','')} {v.get('product','')} — {desc}",
                "level": "warn"
            })
    except Exception:
        pass  # graceful degradation — CISA feed optional

    _ticker_cache.update({"ts": now, "items": items, "count": len(items)})
    return JSONResponse(_ticker_cache)


@app.get("/api/quiz/status")
async def api_quiz_status(request: Request):
    """Daily quiz status for the sidebar widget — streak, done, score."""
    user = request.headers.get("Remote-User", "")
    if not user:
        return JSONResponse({"done": False, "score": 0, "passed": False, "streak": 0, "question_count": 15})

    today   = date.today().isoformat()
    past_30 = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]

    async with SessionLocal() as session:
        act_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == user)
            .where(DailyQuizActivity.quiz_date.in_(past_30))
        )
        past_activities = {a.quiz_date: a for a in act_result.scalars().all()}

    today_activity = past_activities.get(today)
    streak = 0
    for d in past_30:
        act = past_activities.get(d)
        if act and act.passed:
            streak += 1
        else:
            break

    quiz_cfg       = CONFIG.get("quiz", {})
    question_count = quiz_cfg.get("question_count", 15)

    return JSONResponse({
        "done":           today_activity is not None,
        "score":          today_activity.score  if today_activity else 0,
        "passed":         today_activity.passed if today_activity else False,
        "streak":         streak,
        "question_count": question_count,
    })


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
async def admin_users(request: Request, provisioned: str = "",
                      page: int = 1, per_page: int = 10):
    async with SessionLocal() as _chk_session:
        _chk_role = await _get_user_role(request, _chk_session)
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    per_page = max(5, min(100, per_page))
    page     = max(1, page)
    offset   = (page - 1) * per_page

    async with SessionLocal() as session:
        total_count = (await session.execute(
            select(func.count()).select_from(UserProfile)
        )).scalar() or 0

        rows = await session.execute(
            select(UserProfile).order_by(UserProfile.remote_user)
            .limit(per_page).offset(offset)
        )
        profiles = list(rows.scalars().all())

        # Count assignments per user (full table — cheap)
        assign_rows = await session.execute(
            select(SystemAssignment.remote_user, func.count(SystemAssignment.id))
            .group_by(SystemAssignment.remote_user)
        )
        assign_counts = dict(assign_rows.all())

        # Role counts for stats (full table)
        all_role_rows = await session.execute(
            select(UserProfile.remote_user, UserProfile.role)
        )

        role = await _get_user_role(request, session)

    admin_users_cfg = set(CONFIG.get("app", {}).get("admin_users", ["dan"]))
    employees_cfg   = CONFIG.get("employees", [])

    role_counts: dict = {}
    for ru, rl in all_role_rows.all():
        r = "admin" if ru in admin_users_cfg else (rl or "employee")
        role_counts[r] = role_counts.get(r, 0) + 1

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    prov_token  = provisioned if _is_admin(request) else ""

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "profiles": profiles,
        "assign_counts": assign_counts,
        "admin_users_cfg": admin_users_cfg,
        "employees_cfg": employees_cfg,
        "role_counts": role_counts,
        "user_role": role,
        "provisioned_token": prov_token,
        "now": datetime.now(timezone.utc),
        "total_count": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
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
    valid_roles = {
        "employee", "auditor", "bcdr", "system_owner", "isso", "issm", "sca", "ao",
        "ciso", "pen_tester", "data_owner", "pmo", "incident_responder",
    }
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


# ── Provision keys stored in-process (one-time read, TTL 5 min) ──────────────
import secrets as _secrets
import time as _time
_provision_tokens: dict = {}   # token -> {username, password, expires}

def _store_provision_token(username: str, password: str) -> str:
    token = _secrets.token_urlsafe(24)
    _provision_tokens[token] = {
        "username": username, "password": password,
        "expires": _time.time() + 300,   # 5-minute TTL
    }
    # Prune stale tokens
    now = _time.time()
    stale = [k for k, v in _provision_tokens.items() if v["expires"] < now]
    for k in stale:
        _provision_tokens.pop(k, None)
    return token

def _consume_provision_token(token: str) -> dict | None:
    entry = _provision_tokens.pop(token, None)
    if entry and entry["expires"] >= _time.time():
        return entry
    return None


@app.get("/admin/users/provision", response_class=HTMLResponse)
async def admin_provision_page(request: Request, provisioned: str = ""):
    """Dedicated full-page user provisioning form."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    return templates.TemplateResponse("provision_user.html", {
        "request": request,
        "provisioned_token": provisioned,
        **_tpl_ctx(request),
    })


@app.post("/admin/users/provision")
async def admin_provision_user(
    request:      Request,
    username:     str = Form(...),
    display_name: str = Form(""),
    email:        str = Form(""),
    role:         str = Form("employee"),
):
    """
    Unified user onboarding: generates argon2id hash, writes Authelia user file,
    updates config.yaml employees, creates UserProfile, sends welcome email.
    Redirects to /admin/users?provisioned=<token> where the one-time password is shown.
    """
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    admin      = request.headers.get("Remote-User", "")
    username   = username.strip().lower()
    role       = role if role in {"employee","auditor","bcdr","system_owner","isso","issm","sca","ao"} else "employee"
    email      = email.strip()
    dname      = display_name.strip() or username.title()

    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    # ── 1. Generate secure temp password ─────────────────────────────────────
    alphabet    = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789@#%^&*"
    temp_pw     = "".join(_secrets.choice(alphabet) for _ in range(16))

    # ── 2. Hash via Authelia subprocess (no shell — avoids special-char issues) ──
    import subprocess as _subprocess
    try:
        result = _subprocess.run(
            ["docker", "exec", "authelia", "authelia", "crypto", "hash", "generate",
             "argon2", "--password", temp_pw],
            capture_output=True, text=True, timeout=30,
        )
        # Extract hash — output format is: "Digest: $argon2id$v=19$..."
        pw_hash = None
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("Digest:"):
                pw_hash = stripped.split("Digest:", 1)[1].strip()
                break
            if stripped.startswith("$argon2id$"):
                pw_hash = stripped
                break
    except Exception as e:
        log.error("Provision: hash generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate password hash")

    if not pw_hash:
        log.error("Provision: no argon2id hash in output: %s", result.stdout)
        raise HTTPException(status_code=500, detail="Hash generation returned no output")

    # ── 3. Write Authelia users_database.yml ──────────────────────────────────
    import yaml as _yaml
    users_yml = Path("/home/graycat/.docker/compose/authelia/users_database.yml")
    try:
        users_data = _yaml.safe_load(users_yml.read_text()) or {"users": {}}
        if "users" not in users_data:
            users_data["users"] = {}
        users_data["users"][username] = {
            "displayname": dname,
            "password":    pw_hash,
            "email":       email,
            "groups":      ["employees"],
        }
        # Write atomically via temp file
        tmp_yml = users_yml.with_suffix(".yml.tmp")
        tmp_yml.write_text(_yaml.dump(users_data, default_flow_style=False, allow_unicode=True))
        tmp_yml.replace(users_yml)
        log.info("Provision: wrote Authelia user %s (Authelia will reload via watch)", username)
    except Exception as e:
        log.error("Provision: failed to write users_database.yml: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update authentication database")

    # ── 4. Add to config.yaml employees list ─────────────────────────────────
    cfg_path = Path("config.yaml")
    try:
        cfg_text = cfg_path.read_text()
        employees = CONFIG.get("employees", [])
        if not any(e.get("username") == username for e in employees):
            # Append a new employee entry before the 'quiz:' section
            new_entry = f'  - username: "{username}"\n    name: "{dname}"\n    email: "{email}"\n'
            cfg_text  = cfg_text.replace("\nquiz:", f"\n{new_entry}\nquiz:")
            cfg_path.write_text(cfg_text)
            # Reload in-process config
            import importlib as _importlib
            import app.main as _self
            _self.CONFIG = _yaml.safe_load(cfg_path.read_text())
        log.info("Provision: added %s to config.yaml employees", username)
    except Exception as e:
        log.warning("Provision: config.yaml update failed (non-fatal): %s", e)

    # ── 5. Create/update UserProfile in DB ───────────────────────────────────
    async with SessionLocal() as session:
        existing = await session.get(UserProfile, username)
        if existing:
            existing.display_name = dname
            existing.email        = email or existing.email
            existing.role         = role
        else:
            session.add(UserProfile(
                remote_user=username, display_name=dname,
                email=email or None, role=role,
            ))
        await _log_audit(session, admin, "PROVISION", "user_profile", username,
                         {"display_name": dname, "role": role, "email": email})
        await session.commit()

    # ── 6. Send welcome email (best-effort) ──────────────────────────────────
    if email:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, send_welcome_email, CONFIG, username, dname, temp_pw, role, email
            )
        except Exception as e:
            log.warning("Provision: welcome email failed (non-fatal): %s", e)

    # ── 7. Store one-time token and redirect ──────────────────────────────────
    token = _store_provision_token(username, temp_pw)
    log.info("Provision: user %s provisioned by %s (role=%s)", username, admin, role)
    return RedirectResponse(url=f"/admin/users/provision?provisioned={token}", status_code=303)


@app.get("/admin/users/provision/credential")
async def admin_provision_credential(request: Request, token: str):
    """One-time JSON endpoint — consumes the token and returns credentials."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    entry = _consume_provision_token(token)
    if not entry:
        return JSONResponse({"ok": False, "error": "Token expired or already used"}, status_code=410)
    return JSONResponse({"ok": True, "username": entry["username"], "password": entry["password"]})


@app.post("/admin/users/{username}/role")
async def admin_set_role(request: Request, username: str, role: str = Form(...)):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    effective_role = _verify_shell(request.cookies.get("bsv_role_shell", "")) or "admin"
    valid_roles = {
        "employee", "auditor", "bcdr", "system_owner", "isso", "issm", "sca", "ao",
        "ciso", "pen_tester", "data_owner", "pmo", "incident_responder",
    }
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
                             {"old_role": old_role, "new_role": role,
                              "_effective_role": effective_role, "_real_role": "admin"})
        await session.commit()

    return JSONResponse({"status": "ok", "username": username, "role": role})


# ── Bulk user actions ────────────────────────────────────────────────────────────

@app.post("/admin/users/bulk-role")
async def admin_bulk_role(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    body = await request.json()
    usernames = body.get("usernames", [])
    role = body.get("role", "")
    valid_roles = {
        "employee", "auditor", "bcdr", "system_owner", "isso", "issm", "sca", "ao",
        "ciso", "pen_tester", "data_owner", "pmo", "incident_responder",
    }
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    async with SessionLocal() as session:
        for u in usernames:
            profile = await session.get(UserProfile, u)
            if profile:
                profile.role = role
                await _log_audit(session, admin, "UPDATE", "user_profile", u,
                                 {"bulk_set_role": role})
        await session.commit()
    return JSONResponse({"status": "ok", "count": len(usernames)})


@app.post("/admin/users/bulk-freeze")
async def admin_bulk_freeze(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    body = await request.json()
    usernames = body.get("usernames", [])
    async with SessionLocal() as session:
        for u in usernames:
            profile = await session.get(UserProfile, u)
            if profile:
                profile.status = "frozen"
                await _log_audit(session, admin, "UPDATE", "user_profile", u,
                                 {"action": "bulk_freeze"})
        await session.commit()
    return JSONResponse({"status": "ok", "count": len(usernames)})


# ── Freeze / Unfreeze / Remove / Restore ────────────────────────────────────────

@app.post("/admin/users/{username}/freeze")
async def admin_freeze_user(request: Request, username: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    effective_role = _verify_shell(request.cookies.get("bsv_role_shell", "")) or "admin"
    async with SessionLocal() as session:
        profile = await session.get(UserProfile, username)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        profile.status = "frozen"
        await _log_audit(session, admin, "UPDATE", "user_profile", username,
                         {"action": "freeze",
                          "_effective_role": effective_role, "_real_role": "admin"})
        await session.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@app.post("/admin/users/{username}/unfreeze")
async def admin_unfreeze_user(request: Request, username: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    effective_role = _verify_shell(request.cookies.get("bsv_role_shell", "")) or "admin"
    async with SessionLocal() as session:
        profile = await session.get(UserProfile, username)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        profile.status = "active"
        await _log_audit(session, admin, "UPDATE", "user_profile", username,
                         {"action": "unfreeze",
                          "_effective_role": effective_role, "_real_role": "admin"})
        await session.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@app.get("/admin/users/{username}/remove", response_class=HTMLResponse)
async def admin_remove_confirm_page(request: Request, username: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as session:
        profile = await session.get(UserProfile, username)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        # Count systems assigned to this user
        assign_ct = (await session.execute(
            select(func.count(SystemAssignment.id))
            .where(SystemAssignment.remote_user == username)
        )).scalar() or 0
    return templates.TemplateResponse("confirm_remove.html", {
        "request":   request,
        "profile":   profile,
        "assign_ct": assign_ct,
        **_tpl_ctx(request),
    })


@app.post("/admin/users/{username}/remove/confirm")
async def admin_remove_user(request: Request, username: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    effective_role = _verify_shell(request.cookies.get("bsv_role_shell", "")) or "admin"
    form  = await request.form()
    reason = str(form.get("removal_reason", "Termination")).strip() or "Termination"
    async with SessionLocal() as session:
        profile = await session.get(UserProfile, username)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        profile.status         = "removed"
        profile.removed_at     = datetime.now(timezone.utc)
        profile.removed_by     = admin
        profile.removal_reason = reason
        await _log_audit(session, admin, "DELETE", "user_profile", username,
                         {"action": "remove", "reason": reason,
                          "_effective_role": effective_role, "_real_role": "admin"})
        await session.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@app.post("/admin/users/{username}/restore")
async def admin_restore_user(request: Request, username: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        profile = await session.get(UserProfile, username)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        profile.status     = "active"
        profile.removed_at = None
        profile.removed_by = None
        await _log_audit(session, admin, "UPDATE", "user_profile", username,
                         {"action": "restore"})
        await session.commit()
    return RedirectResponse(url="/admin/users/shadow", status_code=303)


@app.get("/admin/users/shadow", response_class=HTMLResponse)
async def admin_shadow_users(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as session:
        rows = await session.execute(
            select(UserProfile)
            .where(UserProfile.status == "removed")
            .order_by(UserProfile.removed_at.desc())
        )
        removed_profiles = list(rows.scalars().all())
    return templates.TemplateResponse("shadow_users.html", {
        "request":  request,
        "profiles": removed_profiles,
        **_tpl_ctx(request),
    })


# ── Audit export ────────────────────────────────────────────────────────────────

@app.get("/admin/siem", response_class=HTMLResponse)
async def admin_siem(request: Request, page: int = 1, per_page: int = 50,
                     severity: str = "", event_type: str = ""):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    per_page = max(10, min(per_page, 200))
    page     = max(1, page)
    offset   = (page - 1) * per_page

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    async with SessionLocal() as session:
        # 24h stats
        total_24h = (await session.execute(
            select(func.count(SecurityEvent.id))
            .where(SecurityEvent.timestamp >= cutoff_24h)
        )).scalar() or 0
        failed_24h = (await session.execute(
            select(func.count(SecurityEvent.id))
            .where(SecurityEvent.timestamp >= cutoff_24h)
            .where(SecurityEvent.event_type == "failed_auth")
        )).scalar() or 0
        high_crit_24h = (await session.execute(
            select(func.count(SecurityEvent.id))
            .where(SecurityEvent.timestamp >= cutoff_24h)
            .where(SecurityEvent.severity.in_(["high", "critical"]))
        )).scalar() or 0
        unique_ips_24h = (await session.execute(
            select(func.count(SecurityEvent.remote_ip.distinct()))
            .where(SecurityEvent.timestamp >= cutoff_24h)
            .where(SecurityEvent.remote_ip != "")
        )).scalar() or 0

        def _siem_q():
            q = select(SecurityEvent).order_by(SecurityEvent.timestamp.desc())
            if severity:
                q = q.where(SecurityEvent.severity == severity)
            if event_type:
                q = q.where(SecurityEvent.event_type == event_type)
            return q

        total = (await session.execute(
            select(func.count()).select_from(_siem_q().subquery())
        )).scalar() or 0
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)

        events = (await session.execute(
            _siem_q().offset(offset).limit(per_page)
        )).scalars().all()

    return templates.TemplateResponse("siem.html", {
        "request":           request,
        "events":            events,
        "total_24h":         total_24h,
        "failed_24h":        failed_24h,
        "high_crit_24h":     high_crit_24h,
        "unique_ips_24h":    unique_ips_24h,
        "page":              page,
        "total_pages":       total_pages,
        "per_page":          per_page,
        "total":             total,
        "filter_severity":   severity,
        "filter_event_type": event_type,
        **_tpl_ctx(request),
    })


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
            q = q.where(System.deleted_at.is_(None))
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
    """Map UserProfile role + admin flag to ATO action role string.
    When an admin is shelled into a non-admin role, use the shell role so that
    higher-level approve/finalize permissions are fully dropped for the session.
    """
    if _is_admin(request):
        shell = _verify_shell(request.cookies.get("bsv_role_shell", "")) or ""
        if shell in _VALID_SHELL_ROLES:
            return shell   # admin in shell → shell role permissions only
        return "admin"
    return profile_role


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


# ── ISSM Workload Dashboard ─────────────────────────────────────────────────────

def _issm_productivity_score(pkg_count: int, max_packages: int,
                              open_poams: int, overdue_poams: int) -> int:
    """Compute 0-100 productivity score for an ISSO.
    Higher = more on track. Lower = behind or overloaded."""
    if pkg_count == 0:
        return 100  # No assignments yet
    score = 100
    # Overload penalty
    if pkg_count > max_packages:
        overload_ratio = (pkg_count - max_packages) / max(1, max_packages)
        score -= min(25, int(overload_ratio * 25))
    # Open POA&M ratio penalty
    poam_ratio = open_poams / max(1, pkg_count)
    score -= min(35, int(poam_ratio * 7))
    # Overdue penalty (heavier)
    score -= min(40, overdue_poams * 6)
    return max(0, score)


@app.get("/issm/dashboard", response_class=HTMLResponse)
async def issm_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "issm"])

        # All ISSOs
        isso_profiles = list((await session.execute(
            select(UserProfile).where(UserProfile.role == "isso").order_by(UserProfile.remote_user)
        )).scalars().all())

        today_str       = date.today().isoformat()
        thirty_days_ago = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]
        isso_data = []
        for isso in isso_profiles:
            sys_ids = list((await session.execute(
                select(SystemAssignment.system_id)
                .where(SystemAssignment.remote_user == isso.remote_user)
            )).scalars().all())

            open_poams    = 0
            overdue_poams = 0
            systems_info  = []
            if sys_ids:
                open_poams = (await session.execute(
                    select(func.count(PoamItem.id))
                    .where(PoamItem.system_id.in_(sys_ids))
                    .where(PoamItem.status.in_(["open", "in_progress"]))
                )).scalar() or 0

                overdue_poams = (await session.execute(
                    select(func.count(PoamItem.id))
                    .where(PoamItem.system_id.in_(sys_ids))
                    .where(PoamItem.status.in_(["open", "in_progress"]))
                    .where(PoamItem.scheduled_completion.isnot(None))
                    .where(PoamItem.scheduled_completion < today_str)
                )).scalar() or 0

                sys_rows = (await session.execute(
                    select(System.id, System.name, System.auth_status,
                           System.confidentiality_impact, System.integrity_impact, System.availability_impact)
                    .where(System.id.in_(sys_ids))
                    .order_by(System.name)
                )).all()

                for sr in sys_rows:
                    # Open + overdue POA&Ms per system
                    s_open = (await session.execute(
                        select(func.count(PoamItem.id))
                        .where(PoamItem.system_id == sr[0])
                        .where(PoamItem.status.in_(["open", "in_progress"]))
                    )).scalar() or 0
                    s_over = (await session.execute(
                        select(func.count(PoamItem.id))
                        .where(PoamItem.system_id == sr[0])
                        .where(PoamItem.status.in_(["open", "in_progress"]))
                        .where(PoamItem.scheduled_completion.isnot(None))
                        .where(PoamItem.scheduled_completion < today_str)
                    )).scalar() or 0
                    systems_info.append({
                        "id": sr[0], "name": sr[1], "auth_status": sr[2],
                        "c": sr[3], "i": sr[4], "a": sr[5],
                        "open_poams": s_open, "overdue_poams": s_over,
                    })

            max_pkg = isso.max_packages or 10
            pkg_count = len(sys_ids)
            prod_score = _issm_productivity_score(pkg_count, max_pkg, open_poams, overdue_poams)

            # Quiz metrics — last 30 days
            quiz_rows = list((await session.execute(
                select(DailyQuizActivity)
                .where(DailyQuizActivity.remote_user == isso.remote_user)
                .where(DailyQuizActivity.quiz_date.in_(thirty_days_ago))
            )).scalars().all())
            quiz_attempts = len(quiz_rows)
            quiz_accuracy = round(sum(r.score for r in quiz_rows) / quiz_attempts) if quiz_attempts else None
            quiz_streak   = 0
            _qmap = {r.quiz_date: r for r in quiz_rows}
            for _qd in thirty_days_ago:
                _qr = _qmap.get(_qd)
                if _qr and _qr.passed:
                    quiz_streak += 1
                else:
                    break

            isso_data.append({
                "remote_user":   isso.remote_user,
                "display_name":  isso.display_name or isso.remote_user,
                "email":         isso.email or "",
                "max_packages":  max_pkg,
                "pkg_count":     pkg_count,
                "open_poams":    open_poams,
                "overdue_poams": overdue_poams,
                "systems":       systems_info,
                "overloaded":    pkg_count > max_pkg,
                "prod_score":    prod_score,
                "quiz_attempts": quiz_attempts,
                "quiz_accuracy": quiz_accuracy,
                "quiz_streak":   quiz_streak,
            })

        ctx = await _full_ctx(request, session, isso_data=isso_data)

    return templates.TemplateResponse("issm_dashboard.html", ctx)


@app.post("/admin/users/{username}/max-packages")
async def set_max_packages(username: str, request: Request):
    """Admin: update max ISSO package limit for a user."""
    user = request.headers.get("Remote-User", "")
    if not user or not _is_admin(request):
        raise HTTPException(status_code=403)
    form = await request.form()
    try:
        value = int(form.get("max_packages", 10))
        value = max(1, min(50, value))
    except (ValueError, TypeError):
        value = 10
    async with SessionLocal() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.remote_user == username)
        )).scalar_one_or_none()
        if profile:
            profile.max_packages = value
        else:
            session.add(UserProfile(remote_user=username, max_packages=value))
        await session.commit()
    return JSONResponse({"status": "ok", "max_packages": value})


# ── Phase 10: SCA Workspace ────────────────────────────────────────────────────

@app.get("/sca/workspace", response_class=HTMLResponse)
async def sca_workspace(request: Request):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role != "sca":
            raise HTTPException(status_code=403)

        user = request.headers.get("Remote-User", "")
        sys_ids = await _user_system_ids(request, session)

        systems_res = await session.execute(
            select(System).where(System.id.in_(sys_ids)).order_by(System.name)
        )
        systems = systems_res.scalars().all()

        # Recent control edits by this SCA user (or all, for admin)
        if _is_admin(request):
            edits_q = select(ControlEdit).order_by(ControlEdit.edited_at.desc()).limit(50)
        else:
            edits_q = (select(ControlEdit)
                       .where(ControlEdit.remote_user == user)
                       .order_by(ControlEdit.edited_at.desc())
                       .limit(50))
        edits_res = await session.execute(edits_q)
        recent_edits = edits_res.scalars().all()

        # Pending SAR uploads: assessments linked to user's systems with status=processing
        pending_q = (select(Assessment)
                     .where(Assessment.system_id.in_(sys_ids))
                     .where(Assessment.status == "processing")
                     .order_by(Assessment.uploaded_at.desc()))
        pending_res = await session.execute(pending_q)
        pending_uploads = pending_res.scalars().all()

        ctx = await _full_ctx(request, session,
                              systems=systems,
                              recent_edits=recent_edits,
                              pending_uploads=pending_uploads)

    return templates.TemplateResponse("sca_workspace.html", ctx)


# ── Phase 10: AO Decisions ────────────────────────────────────────────────────

@app.get("/ao/decisions", response_class=HTMLResponse)
async def ao_decisions(request: Request):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role != "ao":
            raise HTTPException(status_code=403)

        today = date.today().isoformat()
        ninety_days = (date.today() + timedelta(days=90)).isoformat()

        # Systems in review / pending ATO decision (exclude EIS-designated systems)
        review_res = await session.execute(
            select(System)
            .where(System.auth_status == "in_progress")
            .where((System.is_eis == False) | (System.is_eis.is_(None)))
            .order_by(System.updated_at.desc())
        )
        pending_systems = review_res.scalars().all()

        # Systems with ato_decision recorded
        decided_res = await session.execute(
            select(System)
            .where(System.ato_decision.isnot(None))
            .order_by(System.updated_at.desc())
            .limit(20)
        )
        decided_systems = decided_res.scalars().all()

        # Systems with expiring ATOs within 90 days
        expiring_res = await session.execute(
            select(System)
            .where(System.auth_expiry.isnot(None))
            .where(System.auth_expiry <= ninety_days)
            .where(System.auth_expiry >= today)
            .order_by(System.auth_expiry)
        )
        expiring_systems = expiring_res.scalars().all()

        # POA&M counts per system
        poam_counts: dict = {}
        risk_counts: dict = {}
        all_sys_ids = [s.id for s in pending_systems + decided_systems + expiring_systems]
        if all_sys_ids:
            pc_res = await session.execute(
                select(PoamItem.system_id, func.count(PoamItem.id))
                .where(PoamItem.system_id.in_(all_sys_ids))
                .where(PoamItem.status.in_(["open", "in_progress"]))
                .group_by(PoamItem.system_id)
            )
            poam_counts = dict(pc_res.all())
            rc_res = await session.execute(
                select(Risk.system_id, func.count(Risk.id))
                .where(Risk.system_id.in_(all_sys_ids))
                .where(Risk.status == "open")
                .group_by(Risk.system_id)
            )
            risk_counts = dict(rc_res.all())

        ctx = await _full_ctx(request, session,
                              pending_systems=pending_systems,
                              decided_systems=decided_systems,
                              expiring_systems=expiring_systems,
                              poam_counts=poam_counts,
                              risk_counts=risk_counts)

    return templates.TemplateResponse("ao_decisions.html", ctx)


@app.post("/ao/decisions/{system_id}")
async def ao_record_decision(request: Request, system_id: str):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role != "ao":
            raise HTTPException(status_code=403)

        form = await request.form()
        decision = form.get("decision", "")
        if decision not in ("approved", "denied"):
            raise HTTPException(status_code=400, detail="decision must be 'approved' or 'denied'")

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404, detail="System not found")

        system.ato_decision = decision
        if decision == "approved":
            system.auth_status = "authorized"
        else:
            system.auth_status = "not_authorized"

        ao = request.headers.get("Remote-User", "")
        await _log_audit(session, ao, "UPDATE", "system", system_id,
                         {"ato_decision": decision})
        await session.commit()

    return RedirectResponse(url="/ao/decisions", status_code=303)


# ── Phase 10: System Owner Dashboard ─────────────────────────────────────────

@app.get("/system-owner/dashboard", response_class=HTMLResponse)
async def system_owner_dashboard(request: Request):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role != "system_owner":
            raise HTTPException(status_code=403)

        sys_ids = await _user_system_ids(request, session)
        today = date.today().isoformat()

        systems_res = await session.execute(
            select(System).where(System.id.in_(sys_ids)).order_by(System.name)
        )
        systems = systems_res.scalars().all()

        # Open POA&Ms per system
        poam_counts: dict = {}
        risk_counts: dict = {}
        team_counts: dict = {}
        if sys_ids:
            pc_res = await session.execute(
                select(PoamItem.system_id, func.count(PoamItem.id))
                .where(PoamItem.system_id.in_(sys_ids))
                .where(PoamItem.status.in_(["open", "in_progress"]))
                .group_by(PoamItem.system_id)
            )
            poam_counts = dict(pc_res.all())

            rc_res = await session.execute(
                select(Risk.system_id, func.count(Risk.id))
                .where(Risk.system_id.in_(sys_ids))
                .where(Risk.status == "open")
                .group_by(Risk.system_id)
            )
            risk_counts = dict(rc_res.all())

            tc_res = await session.execute(
                select(SystemTeam.system_id, func.count(SystemTeam.id))
                .where(SystemTeam.system_id.in_(sys_ids))
                .group_by(SystemTeam.system_id)
            )
            team_counts = dict(tc_res.all())

        ctx = await _full_ctx(request, session,
                              systems=systems,
                              poam_counts=poam_counts,
                              risk_counts=risk_counts,
                              team_counts=team_counts,
                              today=today)

    return templates.TemplateResponse("system_owner_dashboard.html", ctx)


# ── Phase 10: BCDR Dashboard ──────────────────────────────────────────────────

@app.get("/bcdr/dashboard", response_class=HTMLResponse)
async def bcdr_dashboard(request: Request):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("bcdr", "system_owner"):
            raise HTTPException(status_code=403)

        user = request.headers.get("Remote-User", "")

        # Pending sign-offs for this user
        my_signoffs_res = await session.execute(
            select(BcdrSignoff, BcdrEvent)
            .join(BcdrEvent, BcdrSignoff.event_id == BcdrEvent.id)
            .where(BcdrSignoff.remote_user == user)
            .where(BcdrSignoff.signed_off == False)
            .order_by(BcdrEvent.triggered_at.desc())
        )
        my_signoffs = [{"signoff": sf, "event": ev} for sf, ev in my_signoffs_res.all()]

        # Open BCDR events
        open_events_res = await session.execute(
            select(BcdrEvent)
            .where(BcdrEvent.status.in_(["open", "in_progress"]))
            .order_by(BcdrEvent.triggered_at.desc())
            .limit(30)
        )
        open_events = open_events_res.scalars().all()

        # Sign-off progress per open event
        event_ids = [e.id for e in open_events]
        signoff_totals: dict = {}
        signoff_done: dict = {}
        if event_ids:
            tot_res = await session.execute(
                select(BcdrSignoff.event_id, func.count(BcdrSignoff.id))
                .where(BcdrSignoff.event_id.in_(event_ids))
                .group_by(BcdrSignoff.event_id)
            )
            signoff_totals = dict(tot_res.all())
            done_res = await session.execute(
                select(BcdrSignoff.event_id, func.count(BcdrSignoff.id))
                .where(BcdrSignoff.event_id.in_(event_ids))
                .where(BcdrSignoff.signed_off == True)
                .group_by(BcdrSignoff.event_id)
            )
            signoff_done = dict(done_res.all())

        # Available systems + teams for create-event modal
        sys_ids = await _user_system_ids(request, session)
        systems_res = await session.execute(
            select(System.id, System.name).where(System.id.in_(sys_ids)).order_by(System.name)
        )
        systems_for_modal = [{"id": r[0], "name": r[1]} for r in systems_res.all()]

        teams_res = await session.execute(
            select(SystemTeam).where(SystemTeam.system_id.in_(sys_ids)).order_by(SystemTeam.name)
        )
        teams_for_modal = teams_res.scalars().all()

        ctx = await _full_ctx(request, session,
                              my_signoffs=my_signoffs,
                              open_events=open_events,
                              signoff_totals=signoff_totals,
                              signoff_done=signoff_done,
                              systems_for_modal=systems_for_modal,
                              teams_for_modal=teams_for_modal)

    return templates.TemplateResponse("bcdr_dashboard.html", ctx)


@app.post("/bcdr/events")
async def bcdr_create_event(request: Request):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("bcdr", "system_owner"):
            raise HTTPException(status_code=403)

        form = await request.form()
        system_id  = form.get("system_id", "")
        team_id    = form.get("team_id") or None
        event_type = form.get("event_type", "drill")
        title      = form.get("title", "Untitled Event")
        try:
            target_rto = int(form.get("target_rto", 4))
        except (ValueError, TypeError):
            target_rto = 4
        try:
            target_rpo = int(form.get("target_rpo", 1))
        except (ValueError, TypeError):
            target_rpo = 1

        triggered_by = request.headers.get("Remote-User", "")

        event = BcdrEvent(
            system_id    = system_id or None,
            team_id      = int(team_id) if team_id else None,
            event_type   = event_type,
            title        = title,
            status       = "open",
            triggered_by = triggered_by,
            target_rto   = target_rto,
            target_rpo   = target_rpo,
        )
        session.add(event)
        await session.flush()  # get event.id

        # Auto-create sign-off rows for each team member
        if team_id:
            members_res = await session.execute(
                select(TeamMembership).where(TeamMembership.team_id == int(team_id))
            )
            for member in members_res.scalars().all():
                session.add(BcdrSignoff(
                    event_id     = event.id,
                    remote_user  = member.remote_user,
                    role_in_team = member.role_in_team,
                    required     = True,
                ))

        await _log_audit(session, triggered_by, "CREATE", "bcdr_event", str(event.id),
                         {"title": title, "event_type": event_type})
        await session.commit()

    return RedirectResponse(url="/bcdr/dashboard", status_code=303)


@app.post("/bcdr/events/{event_id}/signoff")
async def bcdr_signoff(request: Request, event_id: int):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        signoff = (await session.execute(
            select(BcdrSignoff)
            .where(BcdrSignoff.event_id == event_id)
            .where(BcdrSignoff.remote_user == user)
            .where(BcdrSignoff.signed_off == False)
        )).scalar_one_or_none()

        if not signoff:
            raise HTTPException(status_code=404, detail="No pending sign-off found for this user/event")

        form = await request.form()
        signoff.signed_off = True
        signoff.signed_at  = datetime.now(timezone.utc)
        signoff.notes      = form.get("notes", "")

        await _log_audit(session, user, "UPDATE", "bcdr_signoff", str(signoff.id),
                         {"event_id": event_id})
        await session.commit()

    return RedirectResponse(url="/bcdr/dashboard", status_code=303)


# ── Phase 10: Teams CRUD (system-scoped, JSON API) ───────────────────────────

@app.get("/systems/{system_id}/teams")
async def list_system_teams(request: Request, system_id: str):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("system_owner", "issm"):
            raise HTTPException(status_code=403)
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        teams_res = await session.execute(
            select(SystemTeam).where(SystemTeam.system_id == system_id).order_by(SystemTeam.name)
        )
        teams = teams_res.scalars().all()

        result = []
        for t in teams:
            members_res = await session.execute(
                select(TeamMembership).where(TeamMembership.team_id == t.id)
            )
            members = [{"remote_user": m.remote_user, "role_in_team": m.role_in_team}
                       for m in members_res.scalars().all()]
            result.append({"id": t.id, "name": t.name, "team_type": t.team_type,
                           "description": t.description, "members": members})

    return JSONResponse(result)


@app.post("/systems/{system_id}/teams")
async def create_system_team(request: Request, system_id: str):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("system_owner", "issm"):
            raise HTTPException(status_code=403)
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        body = await request.json()
        team = SystemTeam(
            system_id   = system_id,
            name        = body.get("name", "New Team"),
            team_type   = body.get("team_type", "general"),
            description = body.get("description", ""),
            created_by  = request.headers.get("Remote-User", ""),
        )
        session.add(team)
        await session.flush()
        tid = team.id
        await session.commit()

    return JSONResponse({"status": "ok", "team_id": tid})


@app.post("/systems/{system_id}/teams/{team_id}/members")
async def add_team_member(request: Request, system_id: str, team_id: int):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("system_owner", "issm"):
            raise HTTPException(status_code=403)

        body = await request.json()
        membership = TeamMembership(
            team_id      = team_id,
            remote_user  = body.get("remote_user", ""),
            role_in_team = body.get("role_in_team", "member"),
            assigned_by  = request.headers.get("Remote-User", ""),
        )
        session.add(membership)
        await session.commit()

    return JSONResponse({"status": "ok"})


@app.delete("/systems/{system_id}/teams/{team_id}/members/{member_user}")
async def remove_team_member(request: Request, system_id: str, team_id: int, member_user: str):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("system_owner", "issm"):
            raise HTTPException(status_code=403)

        membership = (await session.execute(
            select(TeamMembership)
            .where(TeamMembership.team_id == team_id)
            .where(TeamMembership.remote_user == member_user)
        )).scalar_one_or_none()

        if membership:
            await session.delete(membership)
            await session.commit()

    return JSONResponse({"status": "ok"})


# ══════════════════════════════════════════════════════════════════════════════
# Phase 12 — FedRAMP Alignment: Observations, Inventory, Connections, Artifacts
# ══════════════════════════════════════════════════════════════════════════════

_OBS_WRITE_ROLES = {"issm", "isso", "sca", "auditor", "system_owner", "admin"}
_OBS_READ_ROLES  = _OBS_WRITE_ROLES | {"ao"}   # AO: scoped read-only


def _obs_scope_filter(is_admin: bool, role: str, sys_ids: list):
    """Returns a SQLAlchemy where-clause fragment to scope observations, or None for admin."""
    if is_admin:
        return None
    if role == "issm":
        # ISSM sees assigned systems + unlinked (org-level) observations
        return or_(Observation.system_id.in_(sys_ids), Observation.system_id.is_(None))
    return Observation.system_id.in_(sys_ids)


# ── Observations ──────────────────────────────────────────────────────────────

@app.get("/observations", response_class=HTMLResponse)
async def observations_list(request: Request, page: int = 1, per_page: int = 10):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    per_page = max(10, min(per_page, 100))
    page     = max(1, page)
    offset   = (page - 1) * per_page

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in _OBS_READ_ROLES:
            raise HTTPException(status_code=403)

        is_adm  = _is_admin(request)
        sys_ids = await _user_system_ids(request, session)
        scope   = _obs_scope_filter(is_adm, role, sys_ids)

        # Query params for filtering
        params = request.query_params

        def _obs_q():
            q = select(Observation).order_by(Observation.created_at.desc())
            if scope is not None:
                q = q.where(scope)
            if params.get("system_id"):
                q = q.where(Observation.system_id == params["system_id"])
            if params.get("severity"):
                q = q.where(Observation.severity == params["severity"])
            if params.get("source"):
                q = q.where(Observation.source == params["source"])
            if params.get("status"):
                q = q.where(Observation.status == params["status"])
            return q

        total = (await session.execute(
            select(func.count()).select_from(_obs_q().subquery())
        )).scalar() or 0
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)

        obs_list = (await session.execute(
            _obs_q().offset(offset).limit(per_page)
        )).scalars().all()

        # System dropdown — non-admins only see their assigned systems
        if is_adm:
            systems_res = await session.execute(
                select(System.id, System.name)
                .where(System.deleted_at.is_(None))
                .order_by(System.name)
            )
        else:
            systems_res = await session.execute(
                select(System.id, System.name)
                .where(System.id.in_(sys_ids))
                .order_by(System.name)
            )
        systems = [{"id": r[0], "name": r[1]} for r in systems_res.all()]
        sys_map = {s["id"]: s["name"] for s in systems}

        ctx = await _full_ctx(request, session,
                              observations=obs_list,
                              systems=systems,
                              sys_map=sys_map,
                              user_role=role,
                              filter_system_id=params.get("system_id", ""),
                              filter_severity=params.get("severity", ""),
                              filter_source=params.get("source", ""),
                              filter_status=params.get("status", ""),
                              page=page,
                              total_pages=total_pages,
                              per_page=per_page,
                              total=total)
    return templates.TemplateResponse("observations.html", ctx)


@app.get("/observations/new", response_class=HTMLResponse)
async def observation_new_form(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in _OBS_WRITE_ROLES:
            raise HTTPException(status_code=403)

        systems_res = await session.execute(
            select(System.id, System.name)
            .where(System.deleted_at.is_(None))
            .order_by(System.name)
        )
        systems = [{"id": r[0], "name": r[1]} for r in systems_res.all()]

        ctx = await _full_ctx(request, session,
                              obs=None,
                              systems=systems,
                              prefill_system_id=request.query_params.get("system_id", ""),
                              user_role=role)
    return templates.TemplateResponse("observation_detail.html", ctx)


@app.post("/observations")
async def observation_create(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in _OBS_WRITE_ROLES:
            raise HTTPException(status_code=403)

        ctrl_raw = str(form.get("control_ids", "")).strip()
        ctrl_list = [c.strip() for c in ctrl_raw.split(",") if c.strip()]

        obs = Observation(
            system_id   = str(form.get("system_id", "")).strip() or None,
            title       = str(form.get("title", "")).strip(),
            source      = str(form.get("source", "")).strip() or None,
            obs_type    = str(form.get("obs_type", "")).strip() or None,
            severity    = str(form.get("severity", "Moderate")).strip(),
            description = str(form.get("description", "")).strip() or None,
            control_ids = json.dumps(ctrl_list),
            scope_tags  = json.dumps([t.strip() for t in str(form.get("scope_tags", "")).split(",") if t.strip()]),
            assigned_to = str(form.get("assigned_to", "")).strip() or None,
            due_date    = str(form.get("due_date", "")).strip() or None,
            created_by  = user,
        )
        if not obs.title:
            raise HTTPException(status_code=400, detail="Title is required")

        session.add(obs)
        await _log_audit(session, user, "CREATE", "observation", obs.id,
                         {"title": obs.title, "severity": obs.severity})
        await session.commit()

    return RedirectResponse(url=f"/observations/{obs.id}", status_code=303)


@app.get("/observations/{obs_id}", response_class=HTMLResponse)
async def observation_detail(request: Request, obs_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in _OBS_READ_ROLES:
            raise HTTPException(status_code=403)

        obs = (await session.execute(
            select(Observation).where(Observation.id == obs_id)
        )).scalar_one_or_none()
        if not obs:
            raise HTTPException(status_code=404)

        # Scope check for non-admins
        if not _is_admin(request):
            sys_ids = await _user_system_ids(request, session)
            in_scope = (obs.system_id in sys_ids or
                        (obs.system_id is None and role == "issm"))
            if not in_scope:
                raise HTTPException(status_code=403)

        systems_res = await session.execute(
            select(System.id, System.name)
            .where(System.deleted_at.is_(None))
            .order_by(System.name)
        )
        systems = [{"id": r[0], "name": r[1]} for r in systems_res.all()]

        sys_obj = None
        if obs.system_id:
            sys_obj = await session.get(System, obs.system_id)

        promoted_poam = None
        if obs.promoted_to_poam:
            promoted_poam = await session.get(PoamItem, obs.promoted_to_poam)

        ctrl_list = json.loads(obs.control_ids or "[]")
        scope_list = json.loads(obs.scope_tags or "[]")

        ctx = await _full_ctx(request, session,
                              obs=obs,
                              sys_obj=sys_obj,
                              systems=systems,
                              ctrl_list=ctrl_list,
                              scope_list=scope_list,
                              promoted_poam=promoted_poam,
                              user_role=role)
    return templates.TemplateResponse("observation_detail.html", ctx)


@app.post("/observations/{obs_id}/update")
async def observation_update(request: Request, obs_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in _OBS_WRITE_ROLES:
            raise HTTPException(status_code=403)

        obs = (await session.execute(
            select(Observation).where(Observation.id == obs_id)
        )).scalar_one_or_none()
        if not obs:
            raise HTTPException(status_code=404)

        # Scope check for non-admins
        if not _is_admin(request):
            sys_ids = await _user_system_ids(request, session)
            if not (obs.system_id in sys_ids or
                    (obs.system_id is None and role == "issm")):
                raise HTTPException(status_code=403)

        ctrl_raw = str(form.get("control_ids", "")).strip()
        ctrl_list = [c.strip() for c in ctrl_raw.split(",") if c.strip()]

        obs.system_id   = str(form.get("system_id", "")).strip() or None
        obs.title       = str(form.get("title", obs.title)).strip()
        obs.source      = str(form.get("source", "")).strip() or None
        obs.obs_type    = str(form.get("obs_type", "")).strip() or None
        obs.severity    = str(form.get("severity", "Moderate")).strip()
        obs.description = str(form.get("description", "")).strip() or None
        obs.control_ids = json.dumps(ctrl_list)
        obs.scope_tags  = json.dumps([t.strip() for t in str(form.get("scope_tags", "")).split(",") if t.strip()])
        obs.assigned_to = str(form.get("assigned_to", "")).strip() or None
        obs.due_date    = str(form.get("due_date", "")).strip() or None
        obs.status      = str(form.get("status", obs.status)).strip()

        await _log_audit(session, user, "UPDATE", "observation", obs_id,
                         {"title": obs.title, "status": obs.status})
        await session.commit()

    return RedirectResponse(url=f"/observations/{obs_id}", status_code=303)


@app.post("/observations/{obs_id}/promote")
async def observation_promote(request: Request, obs_id: str):
    """Promote an open observation to a POA&M item."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in _OBS_WRITE_ROLES:
            raise HTTPException(status_code=403)

        obs = (await session.execute(
            select(Observation).where(Observation.id == obs_id)
        )).scalar_one_or_none()
        if not obs:
            raise HTTPException(status_code=404)
        if obs.status != "open":
            raise HTTPException(status_code=400, detail="Only open observations can be promoted")

        # Scope check for non-admins
        if not _is_admin(request):
            sys_ids = await _user_system_ids(request, session)
            if not (obs.system_id in sys_ids or
                    (obs.system_id is None and role == "issm")):
                raise HTTPException(status_code=403)

        ctrl_list = json.loads(obs.control_ids or "[]")
        ctrl_id   = ctrl_list[0] if ctrl_list else None

        poam = PoamItem(
            system_id        = obs.system_id,
            control_id       = ctrl_id,
            weakness_name    = obs.title,
            weakness_description = obs.description,
            detection_source = obs.source,
            severity         = obs.severity,
            created_by       = user,
        )
        session.add(poam)
        await session.flush()  # get poam.id

        obs.promoted_to_poam = poam.id
        obs.status = "promoted"

        await _log_audit(session, user, "CREATE", "poam_item", poam.id,
                         {"from_observation": obs_id, "title": obs.title})
        await session.commit()

    return RedirectResponse(url=f"/poam/{poam.id}", status_code=303)


@app.get("/api/observations/summary")
async def observations_api_summary(request: Request):
    """JSON summary of observation counts for sidebar badge. Scoped to user's systems."""
    user = request.headers.get("Remote-User", "")
    if not user:
        return JSONResponse({"open": 0, "promoted": 0, "critical": 0, "high": 0})

    async with SessionLocal() as session:
        role    = await _get_user_role(request, session)
        is_adm  = _is_admin(request)
        sys_ids = await _user_system_ids(request, session)
        scope   = _obs_scope_filter(is_adm, role, sys_ids)

        def _apply_scope(q):
            return q if scope is None else q.where(scope)

        open_ct     = (await session.execute(
            _apply_scope(select(func.count(Observation.id)).where(Observation.status == "open"))
        )).scalar() or 0
        promoted_ct = (await session.execute(
            _apply_scope(select(func.count(Observation.id)).where(Observation.status == "promoted"))
        )).scalar() or 0
        critical_ct = (await session.execute(
            _apply_scope(select(func.count(Observation.id))
            .where(Observation.status == "open")
            .where(Observation.severity == "Critical"))
        )).scalar() or 0
        high_ct = (await session.execute(
            _apply_scope(select(func.count(Observation.id))
            .where(Observation.status == "open")
            .where(Observation.severity == "High"))
        )).scalar() or 0

    return JSONResponse({"open": open_ct, "promoted": promoted_ct,
                         "critical": critical_ct, "high": high_ct})


# ── Inventory ─────────────────────────────────────────────────────────────────

@app.get("/systems/{system_id}/inventory", response_class=HTMLResponse)
async def system_inventory(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404)

        items_res = await session.execute(
            select(InventoryItem)
            .where(InventoryItem.system_id == system_id)
            .order_by(InventoryItem.item_type, InventoryItem.name)
        )
        items = items_res.scalars().all()

        hw = [i for i in items if i.item_type == "hardware"]
        sw = [i for i in items if i.item_type == "software"]
        fw = [i for i in items if i.item_type == "firmware"]

        ctx = await _full_ctx(request, session,
                              system=system,
                              hw_items=hw, sw_items=sw, fw_items=fw,
                              total_items=len(items))
    return templates.TemplateResponse("inventory.html", ctx)


@app.post("/systems/{system_id}/inventory")
async def inventory_add(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        form = await request.form()
        item = InventoryItem(
            system_id     = system_id,
            item_type     = str(form.get("item_type", "hardware")).strip(),
            name          = str(form.get("name", "")).strip(),
            vendor        = str(form.get("vendor", "")).strip() or None,
            version       = str(form.get("version", "")).strip() or None,
            quantity      = int(form.get("quantity", 1) or 1),
            location      = str(form.get("location", "")).strip() or None,
            ip_address    = str(form.get("ip_address", "")).strip() or None,
            serial_number = str(form.get("serial_number", "")).strip() or None,
            notes         = str(form.get("notes", "")).strip() or None,
            added_by      = user,
        )
        if not item.name:
            raise HTTPException(status_code=400, detail="Name is required")

        session.add(item)
        await _log_audit(session, user, "CREATE", "inventory_item", str(system_id),
                         {"name": item.name, "type": item.item_type})
        await session.commit()

    tab = item.item_type
    return RedirectResponse(url=f"/systems/{system_id}/inventory?tab={tab}", status_code=303)


@app.post("/systems/{system_id}/inventory/{item_id}/delete")
async def inventory_delete(request: Request, system_id: str, item_id: int):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        item = (await session.execute(
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .where(InventoryItem.system_id == system_id)
        )).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404)

        item_type = item.item_type
        await session.delete(item)
        await _log_audit(session, user, "DELETE", "inventory_item", str(item_id),
                         {"system_id": system_id})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}/inventory?tab={item_type}", status_code=303)


# ── Connections ───────────────────────────────────────────────────────────────

@app.get("/systems/{system_id}/connections", response_class=HTMLResponse)
async def system_connections(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404)

        conns_res = await session.execute(
            select(SystemConnection)
            .where(SystemConnection.system_id == system_id)
            .order_by(SystemConnection.conn_type, SystemConnection.name)
        )
        conns = conns_res.scalars().all()
        internal = [c for c in conns if c.conn_type == "internal"]
        external = [c for c in conns if c.conn_type == "external"]

        ctx = await _full_ctx(request, session,
                              system=system,
                              internal_conns=internal,
                              external_conns=external,
                              total_conns=len(conns))
    return templates.TemplateResponse("connections.html", ctx)


@app.post("/systems/{system_id}/connections")
async def connection_add(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        form = await request.form()
        conn = SystemConnection(
            system_id     = system_id,
            conn_type     = str(form.get("conn_type", "external")).strip(),
            name          = str(form.get("name", "")).strip(),
            description   = str(form.get("description", "")).strip() or None,
            remote_system = str(form.get("remote_system", "")).strip() or None,
            data_types    = str(form.get("data_types", "")).strip() or None,
            protocol      = str(form.get("protocol", "")).strip() or None,
            port          = str(form.get("port", "")).strip() or None,
            direction     = str(form.get("direction", "bidirectional")).strip(),
            has_isa       = form.get("has_isa") in ("1", "true", "on"),
            isa_doc_id    = str(form.get("isa_doc_id", "")).strip() or None,
            added_by      = user,
        )
        if not conn.name:
            raise HTTPException(status_code=400, detail="Name is required")

        session.add(conn)
        await _log_audit(session, user, "CREATE", "system_connection", str(system_id),
                         {"name": conn.name, "type": conn.conn_type})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}/connections", status_code=303)


@app.post("/systems/{system_id}/connections/{conn_id}/delete")
async def connection_delete(request: Request, system_id: str, conn_id: int):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        conn = (await session.execute(
            select(SystemConnection)
            .where(SystemConnection.id == conn_id)
            .where(SystemConnection.system_id == system_id)
        )).scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404)

        await session.delete(conn)
        await _log_audit(session, user, "DELETE", "system_connection", str(conn_id),
                         {"system_id": system_id})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}/connections", status_code=303)


# ── Artifacts ─────────────────────────────────────────────────────────────────

@app.get("/systems/{system_id}/artifacts", response_class=HTMLResponse)
async def system_artifacts(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404)

        params = request.query_params
        q = select(Artifact).where(Artifact.system_id == system_id)
        if params.get("control_id"):
            q = q.where(Artifact.control_id == params["control_id"])
        if params.get("artifact_type"):
            q = q.where(Artifact.artifact_type == params["artifact_type"])
        if params.get("approval_status"):
            q = q.where(Artifact.approval_status == params["approval_status"])
        q = q.order_by(Artifact.created_at.desc())

        artifacts = (await session.execute(q)).scalars().all()
        today_dt = datetime.now(timezone.utc)

        ctx = await _full_ctx(request, session,
                              system=system,
                              artifacts=artifacts,
                              today_dt=today_dt,
                              filter_control_id=params.get("control_id", ""),
                              filter_type=params.get("artifact_type", ""),
                              filter_status=params.get("approval_status", ""))
    return templates.TemplateResponse("artifacts.html", ctx)


@app.post("/systems/{system_id}/artifacts")
async def artifact_create(request: Request, system_id: str,
                          file: UploadFile = File(None)):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        form = await request.form()

        integrity_hash = None
        saved_path = None

        if file and file.filename:
            art_dir = Path("uploads") / system_id / "artifacts"
            art_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(file.filename).suffix
            save_name = f"{uuid.uuid4()}{suffix}"
            save_path = art_dir / save_name

            file_bytes = await file.read()
            integrity_hash = hashlib.sha256(file_bytes).hexdigest()

            async with aiofiles.open(save_path, "wb") as out:
                await out.write(file_bytes)
            saved_path = str(save_path)

        art = Artifact(
            system_id       = system_id,
            control_id      = str(form.get("control_id", "")).strip() or None,
            artifact_type   = str(form.get("artifact_type", "other")).strip(),
            title           = str(form.get("title", "")).strip(),
            description     = str(form.get("description", "")).strip() or None,
            file_path       = saved_path,
            source          = str(form.get("source", "")).strip() or None,
            integrity_hash  = integrity_hash,
            collected_at    = datetime.now(timezone.utc),
            freshness_days  = int(form.get("freshness_days", 365) or 365),
            owner           = str(form.get("owner", "")).strip() or None,
            created_by      = user,
        )
        if not art.title:
            raise HTTPException(status_code=400, detail="Title is required")

        session.add(art)
        await _log_audit(session, user, "CREATE", "artifact", str(system_id),
                         {"title": art.title, "control_id": art.control_id})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}/artifacts", status_code=303)


@app.post("/systems/{system_id}/artifacts/{art_id}/approve")
async def artifact_approve(request: Request, system_id: str, art_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("issm", "auditor"):
            raise HTTPException(status_code=403)

        art = (await session.execute(
            select(Artifact)
            .where(Artifact.id == art_id)
            .where(Artifact.system_id == system_id)
        )).scalar_one_or_none()
        if not art:
            raise HTTPException(status_code=404)

        form = await request.form()
        decision = str(form.get("decision", "approved")).strip()
        if decision not in ("approved", "rejected"):
            decision = "approved"

        art.approval_status = decision
        art.approved_by     = user
        art.approved_at     = datetime.now(timezone.utc)

        await _log_audit(session, user, "UPDATE", "artifact", art_id,
                         {"approval_status": decision, "system_id": system_id})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}/artifacts", status_code=303)


@app.get("/systems/{system_id}/artifacts/{art_id}/download")
async def artifact_download(request: Request, system_id: str, art_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        art = (await session.execute(
            select(Artifact)
            .where(Artifact.id == art_id)
            .where(Artifact.system_id == system_id)
        )).scalar_one_or_none()
        if not art or not art.file_path:
            raise HTTPException(status_code=404)

    fp = Path(art.file_path)
    if not fp.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(str(fp), filename=fp.name)


# ── EIS Assessment ────────────────────────────────────────────────────────────

@app.get("/systems/{system_id}/eis-assessment", response_class=HTMLResponse)
async def eis_assessment_form(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("isso", "issm"):
            raise HTTPException(status_code=403)

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404)

        ctx = await _full_ctx(request, session, system=system, user_role=role)
    return templates.TemplateResponse("eis_assessment.html", ctx)


@app.post("/systems/{system_id}/eis-assessment")
async def eis_assessment_submit(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role not in ("isso", "issm"):
            raise HTTPException(status_code=403)

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404)

        form = await request.form()
        notes = str(form.get("notes", "")).strip()

        # Mark system as EIS
        system.is_eis = True
        system.updated_at = datetime.now(timezone.utc)

        # Create an RMF monitor step record for the EIS self-assessment
        rmf_rec = RmfRecord(
            system_id  = system_id,
            step       = "monitor",
            status     = "in_progress",
            owner      = user,
            evidence   = f"EIS self-assessment submitted by {user}. Notes: {notes}",
            created_by = user,
        )
        session.add(rmf_rec)

        await _log_audit(session, user, "UPDATE", "system", system_id,
                         {"action": "eis_assessment_submitted", "notes": notes[:200]})
        await session.commit()

    return RedirectResponse(url=f"/systems/{system_id}", status_code=303)
