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
    Request, UploadFile, WebSocket, WebSocketDisconnect
)
from fastapi.responses import (
    FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select, update, text, case as sa_case

from app.models import (
    Assessment, Candidate, ControlResult, ControlsMeta, DailyQuizActivity, QuizResponse,
    System, PoamItem, PoamEvidence, Risk, UserProfile, AuditLog, SystemAssignment, ControlEdit,
    SystemControl, Submission, RmfRecord,
    AtoDocument, AtoDocumentVersion, AtoWorkflowEvent,
    SystemTeam, TeamMembership, BcdrEvent, BcdrSignoff,
    Observation, InventoryItem, SystemConnection, Artifact,
    SecurityEvent,
    AdminChatMessage, AdminChatReceipt,
    ProgramRoleAssignment, DutyAssignment, Notification,
    SspReview, SystemSettings, UserFeedSubscription, IngestJob,
    NistPublication, NvdCve, ControlParameter, AutoFailEvent,
    RemovedUserReservation, FeedSource, FEED_ALLOWLIST,
    # Phase 25 — Daily Workflow Stack
    DailyLogbook, DeepWorkRotation, DeepWorkCompletion,
    ChangeReviewRecord, BackupCheckRecord, AccessSpotCheck,
    Vendor, InterconnectionRecord, DataFlowRecord,
    PrivacyAssessment, RestoreTestRecord, GeneratedReport,
    init_db, make_engine, make_session_factory
)
from app.updater    import load_catalog, update_if_needed
from app.parser     import parse_ssp, analyze_ssp
from app.assessor   import run_assessment, compute_combined_score, is_allstar
from app.quiz       import QUESTIONS, grade_quiz, grade_daily_quiz
from app.mailer     import send_report, forward_assessment, send_welcome_email, send_bundle
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

# ── Phase 16: Admin chat in-memory state ───────────────────────────────────────

_ADMIN_CONNECTIONS: dict[str, WebSocket] = {}   # username → active ws
_ADMIN_PRESENCE:    dict[str, dict]      = {}   # username → {status, away_msg}

# ── Phase 21: Session enforcement ──────────────────────────────────────────────

_LAST_ACTIVITY:  dict[str, datetime] = {}  # username → last-seen UTC timestamp
_SESSION_EXEMPT: set                 = set()  # populated from admin_users at startup
_SESSION_TIMEOUT: timedelta          = timedelta(minutes=15)  # override from config

# ── Phase 23: System settings cache ────────────────────────────────────────────
# In-process cache for system settings — refreshed on write.
_SYSTEM_SETTINGS_CACHE: dict[str, str] = {}

# ── Phase 6: Build stamp ──────────────────────────────────────────────────────
import subprocess as _sp_bld

_BUILD_TIME_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_sha(short: bool = True) -> str:
    try:
        args = ["git", "rev-parse", "--short", "HEAD"] if short else ["git", "rev-parse", "HEAD"]
        return _sp_bld.check_output(args, cwd=os.path.dirname(__file__),
                                    stderr=_sp_bld.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


_BUILD_SHA   = _git_sha(short=True)
_BUILD_SHA_L = _git_sha(short=False)


async def _get_setting(key: str, default: str = "") -> str:
    """Read a system setting, using in-process cache first."""
    if key in _SYSTEM_SETTINGS_CACHE:
        return _SYSTEM_SETTINGS_CACHE[key]
    try:
        async with SessionLocal() as s:
            row = await s.get(SystemSettings, key)
            val = row.value if row else default
            _SYSTEM_SETTINGS_CACHE[key] = val
            return val
    except Exception:
        return default


async def _set_setting(key: str, value: str, updated_by: str = "") -> None:
    """Write a system setting and update the cache."""
    async with SessionLocal() as s:
        row = await s.get(SystemSettings, key)
        if row:
            row.value      = value
            row.updated_by = updated_by
        else:
            s.add(SystemSettings(key=key, value=value, updated_by=updated_by))
        await s.commit()
    _SYSTEM_SETTINGS_CACHE[key] = value


async def _chat_enabled() -> bool:
    return (await _get_setting("chat_enabled", "true")) != "false"


def _is_admin_user(username: str) -> bool:
    return bool(username) and username in set(
        CONFIG.get("app", {}).get("admin_users", ["dan"])
    )


async def _chat_broadcast(data: dict, exclude: str | None = None) -> None:
    for uname, ws in list(_ADMIN_CONNECTIONS.items()):
        if uname == exclude:
            continue
        try:
            await ws.send_json(data)
        except Exception:
            pass


def _presence_payload() -> dict:
    return {
        "type": "presence",
        "users": [
            {"username": u, "status": p["status"], "away_msg": p["away_msg"]}
            for u, p in _ADMIN_PRESENCE.items()
        ],
    }


def _dm_room(a: str, b: str) -> str:
    return ":".join(sorted([a, b]))


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
templates.env.filters["b64decode"] = (
    lambda s: __import__("base64").b64decode(s).decode("utf-8", errors="replace") if s else ""
)

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


def _fmt_ctrl_inline(text: str, params: list = None) -> str:
    """Render control text with parameters substituted as plain inline italic text.
    Used for Control Definition display so the definition reads as natural prose.
    """
    if not text:
        return ""
    param_labels: dict = {}
    if params:
        for p in params:
            pid = p.get("id", "")
            if pid:
                param_labels[pid] = p.get("label", pid.replace("_", " "))

    escaped = _html.escape(text)

    def _param_inline(m: _re.Match) -> str:
        pid      = m.group(1).strip()
        label    = param_labels.get(pid, pid.replace("_", " "))
        odp_desc = _ODP_LABELS.get(pid, "")
        # If ODP description has explicit {choice1; choice2} selections, use those
        if odp_desc:
            cm = _ODP_CHOICE_RE.search(odp_desc)
            if cm:
                choices = [c.strip() for c in cm.group(1).split(";") if c.strip()]
                if 2 <= len(choices) <= 8:
                    label = " | ".join(choices)
        title = f' title="{_html.escape(odp_desc)}"' if odp_desc else ""
        return f'<em class="ctrl-param-inline"{title}>{_html.escape(label)}</em>'

    escaped = _CTRL_PARAM_RE.sub(_param_inline, escaped)

    # Linkify control references
    def _ref_sub(m: _re.Match) -> str:
        full = m.group(0)
        cid  = _re.sub(r'\s*\((\d+)\)', r'.\1', full).lower()
        return f'<a href="/controls/{cid}" class="ctrl-ref">{full}</a>'

    parts_out: list[str] = []
    last = 0
    for tag in _re.finditer(r'<[^>]+>', escaped):
        segment = escaped[last:tag.start()]
        parts_out.append(_CTRL_REF_RE.sub(_ref_sub, segment))
        parts_out.append(tag.group(0))
        last = tag.end()
    parts_out.append(_CTRL_REF_RE.sub(_ref_sub, escaped[last:]))
    return "".join(parts_out)


templates.env.filters["fmt_ctrl_inline"] = _fmt_ctrl_inline


def _first_sentence(text: str, max_len: int = 200) -> str:
    """Extract the first meaningful sentence from supplemental/guidance text."""
    if not text:
        return ""
    # Find sentence boundary (period + space or period at end of string)
    m = _re.search(r'\.\s', text[:400])
    if m and m.start() < 350:
        sent = text[:m.start() + 1]
    else:
        sent = text[:max_len]
    sent = sent.strip()
    if len(sent) > max_len:
        # Truncate at last word boundary
        sent = sent[:max_len].rsplit(' ', 1)[0] + '…'
    return sent


CATALOG:           dict = {}
_CTRL_META:        dict = {}  # lowercase ctrl_id → controls.json record
_ODP_LABELS:       dict = {}  # odp param id → assessment objective label
_ASSESSMENT_PROCS: dict = {}  # lowercase ctrl_id → {examine, interview, test}

# Overlay → authoritative URL (.gov/.mil/.org)
VALID_THEMES = {
    "midnight", "obsidian", "void", "ember", "pine", "steel", "arctic", "parchment"
}

# Regex to extract {choice1; choice2} from ODP descriptions
_ODP_CHOICE_RE = _re.compile(r'\{([^}]+)\}')

_OVERLAY_URLS: dict = {
    "CMMC":                                "https://www.acq.osd.mil/cmmc/",
    "Privacy (accountability)":            "https://www.nist.gov/privacy-framework",
    "Privacy (high)":                      "https://www.nist.gov/privacy-framework",
    "Privacy (low)":                       "https://www.nist.gov/privacy-framework",
    "Privacy (moderate)":                  "https://www.nist.gov/privacy-framework",
    "Privacy Control Baseline (CNSSI 1253)": "https://www.cnss.gov/CNSS/issuances/Instructions.cfm",
}
# All NIST CSF categories link to the NIST Cybersecurity Framework page
_CSF_BASE_URL = "https://www.nist.gov/cyberframework"


def _load_ctrl_meta() -> dict:
    """Load supplemental metadata from templates/controls.json (overlays, CSF categories, etc.)."""
    meta_path = Path("templates/controls.json")
    if not meta_path.exists():
        return {}
    try:
        records = json.loads(meta_path.read_text(encoding="utf-8"))
        return {r["control_id"].lower(): r for r in records if r.get("control_id")}
    except Exception as exc:
        log.warning("Could not load controls.json meta: %s", exc)
        return {}


def _load_odp_labels() -> dict:
    """Load ODP parameter labels extracted from NIST SP 800-53A r5 assessment procedures."""
    path = Path("templates/odp_labels.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Could not load odp_labels.json: %s", exc)
        return {}


def _load_assessment_procs() -> dict:
    """Load EXAMINE/INTERVIEW/TEST assessment procedures from NIST SP 800-53A r5."""
    path = Path("templates/assessment_procedures.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Could not load assessment_procedures.json: %s", exc)
        return {}


def _parse_select_from(text: str) -> list:
    """Parse '[SELECT FROM: item1; item2; ...]' strings into a clean item list.
    Capitalizes the first character of each item (preserving the rest of the case).
    """
    import re as _re2
    if not text:
        return []
    # Strip SELECT FROM wrapper
    m = _re2.match(r'^\[SELECT FROM:\s*(.*?)\]\.?\s*$', text.strip(), _re2.DOTALL)
    content = m.group(1) if m else text
    items = [i.strip().rstrip('.') for i in content.split(';')]
    # Capitalize first letter while preserving the rest (avoids lowercasing "FIPS", "SP 800", etc.)
    return [i[:1].upper() + i[1:] for i in items if i and len(i) > 3]


# ── Real-world interview label mapping ─────────────────────────────────────────
# Maps NIST 800-53A interview phrases (lowercase, partial match) → plain-English job titles
_INTERVIEW_LABEL_MAP: list[tuple[str, str]] = [
    ("account management",           "Account Administrators / IT Help Desk"),
    ("system/network administrator", "System & Network Administrators"),
    ("system administrator",         "System Administrators"),
    ("network administrator",        "Network Engineers"),
    ("database administrator",       "Database Administrators (DBAs)"),
    ("information security responsib","Information Security Officers (ISSO / CISO)"),
    ("security responsib",           "Security Team / ISSO"),
    ("incident response",            "Incident Response Team / SOC Analysts"),
    ("configuration management",     "Configuration Managers / Change Control Board"),
    ("contingency plan",             "Business Continuity / Contingency Plan Coordinator"),
    ("risk management",              "Risk Managers / ISSO"),
    ("audit responsib",              "Auditors / Security Analysts"),
    ("physical and environmental",   "Facilities Managers / Physical Security Officers"),
    ("media protection",             "IT Asset Managers / Media Control Officers"),
    ("developer",                    "Software Developers / DevOps Engineers"),
    ("system developer",             "Software Developers / DevOps Engineers"),
    ("authorizing official",         "Authorizing Official (AO) / Senior Executive"),
    ("key organizational personnel", "Senior Leadership / System Owner"),
    ("program management",           "Program Managers / PMO"),
    ("personnel with least privilege","IT Security / Access Control Manager"),
    ("supply chain",                 "Procurement / Supply Chain Manager"),
    ("training responsib",           "Security Awareness & Training Coordinator"),
    ("personnel security responsib", "HR Security / Personnel Vetting Officer"),
    ("planning responsib",           "Security Planning Officer / ISSO"),
]


def _humanize_interview_item(item: str) -> str:
    """Map a NIST interview phrase to a human-readable job title if a match exists."""
    low = item.lower()
    for fragment, label in _INTERVIEW_LABEL_MAP:
        if fragment in low:
            return label
    return item


def _build_assessment_ctx(ctrl_id: str) -> dict | None:
    """Return structured assessment guidance for a control, or None if unavailable."""
    proc = _ASSESSMENT_PROCS.get(ctrl_id.lower())
    if not proc:
        return None
    examine   = _parse_select_from(proc.get("examine", ""))
    interview = [_humanize_interview_item(i)
                 for i in _parse_select_from(proc.get("interview", ""))]
    # Deduplicate interview labels while preserving order
    seen: set = set()
    interview = [x for x in interview if not (x in seen or seen.add(x))]
    test      = _parse_select_from(proc.get("test", ""))
    if not examine and not interview and not test:
        return None
    return {"examine": examine, "interview": interview, "test": test}

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global CATALOG, _APP_SECRET, _CTRL_META, _ODP_LABELS, _ASSESSMENT_PROCS, _SESSION_EXEMPT, _SESSION_TIMEOUT
    await init_db(engine)
    _APP_SECRET       = _get_app_secret()
    _SESSION_EXEMPT   = set(CONFIG.get("app", {}).get("admin_users", ["dan"]))
    _SESSION_TIMEOUT  = timedelta(minutes=int(CONFIG.get("session", {}).get("timeout_minutes", 15)))
    _CTRL_META        = _load_ctrl_meta()
    _ODP_LABELS       = _load_odp_labels()
    _ASSESSMENT_PROCS = _load_assessment_procs()
    log.info("Control meta loaded: %d records.", len(_CTRL_META))
    log.info("ODP labels loaded: %d entries.", len(_ODP_LABELS))
    log.info("Assessment procedures loaded: %d controls.", len(_ASSESSMENT_PROCS))
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
    # Backfill inventory numbers for existing systems that don't have one
    try:
        async with SessionLocal() as s:
            no_inv = (await s.execute(
                select(System)
                .where(System.inventory_number.is_(None))
                .where(System.deleted_at.is_(None))
                .order_by(System.created_at)
            )).scalars().all()
            if no_inv:
                # Find max existing number
                all_inv = (await s.execute(
                    select(System.inventory_number).where(System.inventory_number.isnot(None))
                )).scalars().all()
                max_num = 199
                for inv in all_inv:
                    if inv and "-" in inv:
                        try:
                            n = int(inv.split("-", 1)[1])
                            if n > max_num:
                                max_num = n
                        except ValueError:
                            pass
                for sys_obj in no_inv:
                    abbr = (sys_obj.abbreviation or "XXXX")[:4].upper().ljust(4, 'X')
                    max_num += 1
                    sys_obj.inventory_number = f"{abbr}-{max_num:04d}"
                await s.commit()
                log.info("Backfilled inventory numbers for %d systems.", len(no_inv))
    except Exception as e:
        log.warning("Could not backfill inventory numbers: %s", e)
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


# ── Custom error page handlers ──────────────────────────────────────────────────

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    ctx = {**_tpl_ctx(request), "request": request, "now": datetime.now(timezone.utc)}
    tpl = {403: "errors/403.html", 404: "errors/404.html"}.get(exc.status_code)
    if tpl is None and exc.status_code >= 500:
        tpl = "errors/500.html"
    if tpl:
        return templates.TemplateResponse(tpl, ctx, status_code=exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

@app.exception_handler(Exception)
async def generic_exc_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception: %s", exc)
    ctx = {**_tpl_ctx(request), "request": request, "now": datetime.now(timezone.utc)}
    return templates.TemplateResponse("errors/500.html", ctx, status_code=500)


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


# ── Session Enforcement Middleware (Phase 21) ────────────────────────────────

_SESSION_SKIP_PREFIXES = ("/static", "/api/heartbeat", "/ws/", "/favicon")

@app.middleware("http")
async def session_timeout_middleware(request: Request, call_next):
    """Enforce idle session timeout for non-exempt users."""
    user = request.headers.get("Remote-User", "")
    path = request.url.path
    if user and user not in _SESSION_EXEMPT and not any(path.startswith(p) for p in _SESSION_SKIP_PREFIXES):
        last = _LAST_ACTIVITY.get(user)
        if last:
            age = datetime.now(timezone.utc) - last  # BLKS022826-1003AC03: use timezone-aware now()
            if age > _SESSION_TIMEOUT:
                logout_url = _cfg("app.authelia_logout_url", "/logout")
                _LAST_ACTIVITY.pop(user, None)
                r = RedirectResponse(logout_url, status_code=302)
                r.delete_cookie("bsv_role_shell")
                r.delete_cookie("bsv_mode")
                r.delete_cookie("bsv_user_view")
                return r
        _LAST_ACTIVITY[user] = datetime.now(timezone.utc)  # BLKS022826-1003AC03
    return await call_next(request)


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


def _effective_is_admin(request: Request) -> bool:
    """Like _is_admin but returns False when the admin has an active role shell.

    Use this on all admin WRITE routes so that an admin shelled into a lower
    role (e.g. ISSO) cannot perform admin-level mutations for the duration.
    Read-only admin routes may continue to use _is_admin if inspection is needed.
    """
    if not _is_admin(request):
        return False
    shell = _verify_shell(request.cookies.get("bsv_role_shell", "")) or ""
    return shell not in _VALID_SHELL_ROLES  # shell active → not effectively admin


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
    raw_theme = request.cookies.get("bsv_theme", "midnight")
    user_theme = raw_theme if raw_theme in VALID_THEMES else "midnight"
    # H6: UI preferences — read from cookies (PATCH /api/preferences sets both DB + cookie)
    _valid_font  = {"12px","14px","16px","18px","20px"}
    _valid_dens  = {"compact","comfortable","spacious"}
    _valid_rows  = {10, 25, 50, 100}
    _pref_font   = request.cookies.get("bsv_pref_font", "14px")
    _pref_font   = _pref_font if _pref_font in _valid_font else "14px"
    _pref_dens   = request.cookies.get("bsv_pref_density", "comfortable")
    _pref_dens   = _pref_dens if _pref_dens in _valid_dens else "comfortable"
    try:
        _pref_rows = int(request.cookies.get("bsv_pref_rows", "25"))
        _pref_rows = _pref_rows if _pref_rows in _valid_rows else 25
    except (ValueError, TypeError):
        _pref_rows = 25
    # View-as: manager/admin viewing a specific employee's workspace
    viewed_user_raw = _verify_shell(request.cookies.get("bsv_user_view", "")) or ""
    is_view_as      = bool(viewed_user_raw) and is_admin_user
    return {
        "app_name":           _cfg("app.name", "BLACKSITE"),
        "brand":              _cfg("app.brand", "TheKramerica"),
        "tagline":            _cfg("app.tagline", "Security Assessment Platform"),
        "authelia_logout_url": _cfg("app.authelia_logout_url", "/logout"),
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
        "user_theme":         user_theme,
        "is_view_as":         is_view_as,
        "viewed_user":        viewed_user_raw if is_view_as else "",
        # System settings (read from cache; default True/5 if not yet set)
        "chat_enabled":       _SYSTEM_SETTINGS_CACHE.get("chat_enabled", "true") != "false",
        "chat_visible_count": int(_SYSTEM_SETTINGS_CACHE.get("chat_visible_count", "5")),
        "chat_show_away_msg": _SYSTEM_SETTINGS_CACHE.get("chat_show_away_msg", "true") != "false",
        "build_sha":          _BUILD_SHA,
        "build_time":         _BUILD_TIME_UTC,
        # H6: UI preferences
        "pref_font_size":     _pref_font,
        "pref_density":       _pref_dens,
        "pref_rows_per_page": _pref_rows,
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


async def _notify_user(session, remote_user: str, notif_type: str, title: str,
                       body: str = "", action_url: str = "",
                       related_id: int = 0, related_type: str = ""):
    """Create an in-app Notification record for a user."""
    if not remote_user:
        return
    notif = Notification(
        remote_user  = remote_user,
        notif_type   = notif_type,
        title        = title,
        body         = body,
        action_url   = action_url,
        related_id   = related_id,
        related_type = related_type,
    )
    session.add(notif)


async def _notify_system_team(session, system_id: str, notif_type: str,
                               title: str, body: str = "", action_url: str = "",
                               exclude_user: str = ""):
    """Notify all users assigned to a system (except exclude_user)."""
    assigned = await session.execute(
        select(SystemAssignment.remote_user)
        .where(SystemAssignment.system_id == system_id)
    )
    for (ru,) in assigned.all():
        if ru != exclude_user:
            await _notify_user(session, ru, notif_type, title, body, action_url)


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

_READ_ONLY_ROLES: frozenset = frozenset({
    "pen_tester", "employee", "data_owner", "pmo", "incident_responder",
})

# Controls requiring formal evidence (artifact/assessment) before marking "implemented_complete".
# Based on NIST SP 800-53 rev5 high-impact baseline controls that are testable and
# require documented proof beyond a narrative statement. Adding these prevents
# self-attestation on controls where objective evidence is mandatory for assessors.
_EVIDENCE_REQUIRED_CONTROLS: frozenset = frozenset({
    "ac-2", "ac-3", "ac-5", "ac-6", "ac-17", "ac-18", "ac-19",
    "au-2", "au-3", "au-6", "au-9", "au-11", "au-12",
    "cm-6", "cm-7", "cm-8",
    "ia-2", "ia-3", "ia-5", "ia-8",
    "ir-6",
    "mp-6",
    "ra-5",
    "sa-11",
    "sc-7", "sc-8", "sc-13", "sc-28",
    "si-2", "si-3", "si-7",
})


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

    # Unread notification count for nav bell
    unread_notifications = 0
    if user:
        try:
            nc_res = await session.execute(
                select(func.count(Notification.id))
                .where(Notification.remote_user == user)
                .where(Notification.is_read == False)
            )
            unread_notifications = nc_res.scalar() or 0
        except Exception:
            pass

    return {
        "request":               request,
        **_tpl_ctx(request),
        "user_role":             display_role,
        "actual_role":           native_role,
        "is_role_view":          is_shell,
        "user_teams":            user_teams,
        "now":                   datetime.now(timezone.utc),
        "shell_allowed_roles":   shell_allowed_roles,
        "unread_notifications":  unread_notifications,
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

# Role-based push power: which roles can SET each status
POAM_PUSH_POWER: dict[str, set] = {
    "draft":            {"isso", "sca", "admin"},
    "open":             {"isso", "admin"},
    "in_progress":      {"isso", "admin"},
    "blocked":          {"isso", "admin"},
    "ready_for_review": {"isso", "admin"},
    "closed_verified":  {"issm", "admin"},
    "deferred_waiver":  {"isso", "admin"},   # requires SO→CISO→AO approval chain
    "accepted_risk":    {"isso", "admin"},   # requires SO→CISO→AO approval chain
    "false_positive":   {"issm", "admin"},   # requires SCA+SO concurrence
}

# Required fields per target status (must be non-empty before transition)
POAM_REQUIRED_FOR_STATUS: dict[str, list] = {
    "open":             ["responsible_party", "severity", "scheduled_completion"],
    "blocked":          ["blocker_category", "blocker_owner", "unblock_plan"],
    "ready_for_review": ["closure_evidence", "residual_risk"],
    "closed_verified":  ["closure_evidence", "verification_method", "verifier", "verification_date"],
    "deferred_waiver":  ["waiver_start", "waiver_end", "compensating_controls"],
    "accepted_risk":    ["risk_accept_review", "compensating_controls"],
    "false_positive":   ["non_applicability_rationale"],
}

# Approval chain: status → ordered list of approving roles
POAM_APPROVAL_CHAIN: dict[str, list] = {
    "open":            ["so"],
    "blocked":         ["so"],
    "closed_verified": ["so"],
    "deferred_waiver": ["so", "ciso", "ao"],
    "accepted_risk":   ["so", "ciso", "ao"],
    "false_positive":  ["sca", "so"],
}


def _poam_allowed_statuses(role: str, current_status: str) -> list:
    """Return the status values this role can push to from current_status."""
    allowed = []
    for st, roles in POAM_PUSH_POWER.items():
        if role in roles:
            allowed.append(st)
    return allowed


def _generate_poam_id(abbr: str, control_id: str, serial: int) -> str:
    """Generate human-readable POAM ID: ABVR022826-1001AC01"""
    abbr_clean = (abbr or "XXXX")[:4].upper().ljust(4, "X")
    date_str = date.today().strftime("%m%d%y")
    # Select lowest control from comma-separated list
    lowest = _lowest_control(control_id or "")
    ctrl_str = _fmt_ctrl_for_id(lowest) if lowest else ""
    return f"{abbr_clean}{date_str}-{serial}{ctrl_str}"


def _lowest_control(control_id: str) -> str:
    """From comma-separated control IDs return the lowest (family alpha, then num)."""
    if not control_id:
        return ""
    parts = [c.strip().lower() for c in control_id.replace(";", ",").split(",") if c.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    def _sort_key(c):
        bits = c.split("-")
        family = bits[0] if bits else ""
        try:
            num = int(bits[1]) if len(bits) > 1 else 0
        except ValueError:
            num = 0
        return (family, num)
    return sorted(parts, key=_sort_key)[0]


def _fmt_ctrl_for_id(ctrl: str) -> str:
    """Format control ID for POAM ID: 'ac-1' → 'AC01', 'si-12' → 'SI12'"""
    if not ctrl:
        return ""
    parts = ctrl.strip().lower().split("-")
    family = parts[0].upper() if parts else ""
    try:
        num = int(parts[1]) if len(parts) > 1 else 0
        return f"{family}{num:02d}"
    except ValueError:
        return family


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

# Doc types that can be auto-generated from existing system data
_GENERATABLE_DOCS: frozenset = frozenset({
    "FIPS199",        # from system FIPS impact levels
    "SSP",            # from SystemControl implementation records
    "POAM",           # from PoamItem records
    "HW_INV",         # from InventoryItem (hardware)
    "SW_INV",         # from InventoryItem (software)
    "SSP_APP_M",      # from InventoryItem (integrated inventory workbook)
    "CONMON_MONTHLY", # from POAMs + controls summary
    "ADD",            # auto-generated when AO records approval decision
})

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

_ROLE_DASHBOARD: dict = {
    "pen_tester":         "/pen-tester/dashboard",
    "sca":                "/sca/dashboard",
    "auditor":            "/auditor/dashboard",
    "incident_responder": "/incident-responder/dashboard",
    "data_owner":         "/data-owner/dashboard",
    "pmo":                "/pmo/dashboard",
    "bcdr":               "/bcdr/dashboard",
    "system_owner":       "/system-owner/dashboard",
    "issm":               "/issm/dashboard",
    "ciso":               "/ciso/dashboard",
    "ao":                 "/ao/decisions",
    "admin":              "/admin",
}

@app.get("/")
async def index(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized — Authelia authentication required")
    if _is_admin(request):
        if _view_mode(request) == "employee":
            return RedirectResponse(url="/dashboard", status_code=302)
        return RedirectResponse(url="/admin", status_code=302)
    # Route to role-specific dashboard if available
    async with SessionLocal() as _idx_session:
        _idx_role = await _get_user_role(request, _idx_session)
    dest = _ROLE_DASHBOARD.get(_idx_role, "/dashboard")
    return RedirectResponse(url=dest, status_code=302)


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
    response.set_cookie("bsv_mode", mode, max_age=86400 * 30, httponly=True, samesite="lax", secure=True)
    return response


@app.get("/switch-role-view")
async def switch_role_view(request: Request, role: str = ""):
    """Switch to a role shell view. Admins can shell into any role; others only into lower roles.

    Permission model:
    - Native role is always read from the DB (never from the shell cookie).
    - Allowed targets = ROLE_CAN_VIEW_DOWN[native_role].
    - Shelled users receive the "WORKING AS" banner and ONLY that role's permissions.
    """
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    ref = request.headers.get("Referer", "/systems")
    response = RedirectResponse(url=ref, status_code=303)

    async with SessionLocal() as session:
        # Always derive native role from the DB — never from the shell cookie.
        if _is_admin(request):
            native = "admin"
        else:
            native_row = (await session.execute(
                select(UserProfile.role).where(UserProfile.remote_user == user)
            )).scalar_one_or_none()
            native = native_row or "employee"

        allowed = ROLE_CAN_VIEW_DOWN.get(native, [])
        grant  = (role != "reset") and (role in allowed)

        if grant:
            await _log_audit(session, user, "UPDATE", "role_shell", user,
                             {"action": "set_shell", "target_role": role,
                              "_real_role": native})
            await session.commit()

    if grant:
        response.set_cookie("bsv_role_shell", _sign_shell(role), httponly=True, samesite="lax", secure=True)
    else:
        response.delete_cookie("bsv_role_shell")
    response.delete_cookie("bsv_role_view")  # cleanup legacy cookie
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
    if not _is_admin(request) and _chk_role not in ("sca", "isso"):
        raise HTTPException(status_code=403, detail="SSP upload is restricted to administrators, SCA, and ISSO users")
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
    if not _is_admin(request) and _chk_role not in ("sca", "isso"):
        raise HTTPException(status_code=403, detail="SSP upload is restricted to administrators, SCA, and ISSO users")
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
async def status_api(request: Request, assessment_id: str):
    if not request.headers.get("Remote-User", ""):
        raise HTTPException(status_code=401, detail="Authentication required")
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

    tpl = _tpl_ctx(request)
    view_as_mode = tpl.get("is_view_as", False)
    viewed_user  = tpl.get("viewed_user", "")
    # The user whose data we actually query
    dash_user = viewed_user if view_as_mode and viewed_user else user

    # Redirect non-employee roles to their specific dashboard (unless admin or view-as mode)
    if not _is_admin(request) and not view_as_mode:
        async with SessionLocal() as _dash_session:
            _dash_role = await _get_user_role(request, _dash_session)
        _dash_dest = _ROLE_DASHBOARD.get(_dash_role)
        if _dash_dest and _dash_dest != "/dashboard":
            return RedirectResponse(url=_dash_dest, status_code=302)

    today     = date.today().isoformat()
    past_30   = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]

    async with SessionLocal() as session:
        act_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == dash_user)
            .where(DailyQuizActivity.quiz_date.in_(past_30))
        )
        past_activities: Dict[str, DailyQuizActivity] = {
            a.quiz_date: a for a in act_result.scalars().all()
        }

        history_result = await session.execute(
            select(DailyQuizActivity)
            .where(DailyQuizActivity.remote_user == dash_user)
            .order_by(DailyQuizActivity.quiz_date.asc())
            .limit(30)
        )
        score_history = history_result.scalars().all()

        my_rows = await session.execute(
            select(Assessment, Candidate)
            .join(Candidate, Assessment.candidate_id == Candidate.id)
            .where(Assessment.submitted_by == dash_user)
            .order_by(Assessment.uploaded_at.desc())
            .limit(50)
        )
        my_entries = [{"assessment": a, "candidate": c} for a, c in my_rows.all()]

        # Assigned systems
        assigned_result = await session.execute(
            select(SystemAssignment, System)
            .join(System, SystemAssignment.system_id == System.id)
            .where(SystemAssignment.remote_user == dash_user)
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
        "view_as_mode":     view_as_mode,
        "viewing_as":       dash_user if view_as_mode else "",
        **tpl,
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

# ── RSS Feed Catalog (Phase 23) ───────────────────────────────────────────────
CURATED_FEEDS: list[dict] = [
    {"key": "krebs",        "name": "Krebs on Security",      "url": "https://krebsonsecurity.com/feed/",                        "desc": "Investigative journalism on cybercrime and security"},
    {"key": "schneier",     "name": "Schneier on Security",   "url": "https://www.schneier.com/feed/atom/",                       "desc": "Security analysis and commentary by Bruce Schneier"},
    {"key": "cisa_alerts",  "name": "CISA Alerts",            "url": "https://www.cisa.gov/uscert/ncas/alerts.xml",              "desc": "Official US-CERT alerts and advisories"},
    {"key": "cisa_adv",     "name": "CISA Advisories",        "url": "https://www.cisa.gov/uscert/ncas/advisories.xml",          "desc": "ICS and operational technology advisories"},
    {"key": "sans",         "name": "SANS Internet Storm Center", "url": "https://isc.sans.edu/rssfeed_full.xml",                "desc": "Daily handler diaries and threat intel"},
    {"key": "thn",          "name": "The Hacker News",         "url": "https://feeds.feedburner.com/TheHackersNews",             "desc": "Cybersecurity news and analysis"},
    {"key": "bleeping",     "name": "BleepingComputer",        "url": "https://www.bleepingcomputer.com/feed/",                  "desc": "Ransomware, malware, and breach reporting"},
    {"key": "secweek",      "name": "SecurityWeek",            "url": "https://feeds.feedburner.com/securityweek",               "desc": "Enterprise security news and insights"},
    {"key": "darkreading",  "name": "Dark Reading",            "url": "https://www.darkreading.com/rss.xml",                     "desc": "Enterprise security strategy and research"},
    {"key": "arstechsec",   "name": "Ars Technica Security",  "url": "https://feeds.arstechnica.com/arstechnica/security",       "desc": "Security coverage with technical depth"},
    {"key": "nvd",          "name": "NIST NVD — New CVEs",    "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",      "desc": "National Vulnerability Database — newly published CVEs"},
    {"key": "nakedsec",     "name": "Naked Security (Sophos)", "url": "https://nakedsecurity.sophos.com/feed/",                 "desc": "Consumer and SMB security news from Sophos"},
    {"key": "grahamcluley", "name": "Graham Cluley",           "url": "https://grahamcluley.com/feed/",                          "desc": "Independent security analyst commentary"},
    {"key": "trojanhunt",   "name": "Troy Hunt",               "url": "https://www.troyhunt.com/rss/",                           "desc": "Data breaches, HaveIBeenPwned author"},
    {"key": "recordedfuture","name": "Recorded Future News",   "url": "https://therecord.media/feed",                            "desc": "Nation-state threats and APT reporting"},
]
_FEED_KEY_SET = {f["key"] for f in CURATED_FEEDS}

# Default feeds enabled for new users
_DEFAULT_FEEDS = {"cisa_alerts", "thn", "bleeping", "krebs", "nvd"}


async def _get_user_feeds(user: str, session) -> set[str]:
    """Return set of feed keys enabled for this user."""
    rows = (await session.execute(
        select(UserFeedSubscription.feed_key, UserFeedSubscription.enabled)
        .where(UserFeedSubscription.remote_user == user)
    )).all()
    if not rows:
        return set(_DEFAULT_FEEDS)
    return {r[0] for r in rows if r[1]}


@app.get("/profile/feeds", response_class=HTMLResponse)
async def profile_feeds(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as s:
        enabled = await _get_user_feeds(user, s)
    return templates.TemplateResponse("profile_feeds.html", {
        "request": request,
        "feeds":   CURATED_FEEDS,
        "enabled": enabled,
        **_tpl_ctx(request),
    })


@app.post("/profile/feeds")
async def profile_feeds_save(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    form = await request.form()
    selected = {k for k in form if k in _FEED_KEY_SET}
    async with SessionLocal() as s:
        for feed in CURATED_FEEDS:
            key = feed["key"]
            enabled = key in selected
            row = (await s.execute(
                select(UserFeedSubscription).where(
                    UserFeedSubscription.remote_user == user,
                    UserFeedSubscription.feed_key == key,
                )
            )).scalar_one_or_none()
            if row:
                row.enabled = enabled
            else:
                s.add(UserFeedSubscription(remote_user=user, feed_key=key, enabled=enabled))
        await s.commit()
    return RedirectResponse("/profile/feeds?saved=1", status_code=303)


@app.get("/api/feeds/user")
async def api_user_feeds(request: Request):
    """Return the ticker feed items filtered to this user's subscriptions."""
    user = request.headers.get("Remote-User", "")
    async with SessionLocal() as s:
        enabled = await _get_user_feeds(user, s)
    # Pass enabled feed URLs to the existing feed fetcher
    from app.rss_feed import get_all_feed_items
    enabled_feeds = [f for f in CURATED_FEEDS if f["key"] in enabled]
    urls = [f["url"] for f in enabled_feeds]
    items = await get_all_feed_items(urls)
    return JSONResponse({"items": items[:40]})


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


# ── Profile avatar ──────────────────────────────────────────────────────────────

_AVATAR_DIR  = Path("data/avatars")
_AVATAR_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_AVATAR_MAX   = 5 * 1024 * 1024   # 5 MB

@app.post("/profile/avatar")
async def profile_avatar_upload(
    request: Request,
    file:    UploadFile = File(...),
):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _AVATAR_TYPES:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Use JPG, PNG, GIF, or WebP.")

    data = await file.read()
    if len(data) > _AVATAR_MAX:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5 MB.")

    _AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    # One file per user — replace any existing extension
    for old in _AVATAR_DIR.glob(f"{user}.*"):
        old.unlink(missing_ok=True)
    dest = _AVATAR_DIR / f"{user}{ext}"
    dest.write_bytes(data)

    # Store the canonical serving URL in UserProfile
    async with SessionLocal() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.remote_user == user)
        )).scalar_one_or_none()
        if not profile:
            profile = UserProfile(remote_user=user)
            session.add(profile)
        profile.avatar_url = f"/profile/avatar/{user}"
        await _log_audit(session, user, "UPDATE", "profile", user, {"action": "avatar_upload"})
        await session.commit()

    return JSONResponse({"ok": True, "url": f"/profile/avatar/{user}?t={int(datetime.now(timezone.utc).timestamp())}"})


@app.get("/profile/avatar/{username}")
async def serve_avatar(username: str):
    for ext in _AVATAR_TYPES:
        p = _AVATAR_DIR / f"{username}{ext}"
        if p.exists():
            import mimetypes as _mt
            mt = _mt.guess_type(str(p))[0] or "image/jpeg"
            return Response(content=p.read_bytes(), media_type=mt,
                            headers={"Cache-Control": "public, max-age=3600"})
    raise HTTPException(status_code=404)


# ── System Catalog ─────────────────────────────────────────────────────────────

@app.get("/systems", response_class=HTMLResponse)
async def systems_list(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        _list_role = await _get_user_role(request, session)
        if _is_admin(request) or _list_role in ("ao", "ciso"):
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

        # Build set of system_ids the current user is personally assigned to
        my_assigned_rows = await session.execute(
            select(SystemAssignment.system_id)
            .where(SystemAssignment.remote_user == user)
        )
        my_assigned_sys_ids = {r[0] for r in my_assigned_rows.all()}

        ctx = await _full_ctx(request, session,
            systems      = systems,
            authorized_ct  = sum(1 for s in systems if s.auth_status == "authorized"),
            in_progress_ct = sum(1 for s in systems if s.auth_status == "in_progress"),
            expired_ct     = sum(1 for s in systems if s.auth_status == "expired"),
            not_auth_ct    = sum(1 for s in systems if s.auth_status == "not_authorized"),
            assigned_sys_ids    = assigned_sys_ids,
            my_assigned_sys_ids = my_assigned_sys_ids,
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


async def _resolve_abbreviation(session, abbr_raw: str, exclude_id: str | None = None) -> str:
    """Normalize abbreviation to exactly 4 uppercase letters.
    If the abbreviation is already taken by another system, append/replace with '1'.
    If shorter than 4, pad with 'X'; if longer, truncate to 4.
    """
    abbr = _re.sub(r'[^A-Za-z]', '', abbr_raw).upper()[:4]
    abbr = abbr.ljust(4, 'X')  # pad if < 4 chars

    # Check uniqueness
    q = select(System.abbreviation).where(
        System.abbreviation == abbr,
        System.deleted_at.is_(None),
    )
    if exclude_id:
        q = q.where(System.id != exclude_id)
    existing = (await session.execute(q)).scalar_one_or_none()

    if existing:
        # Senior retains original abbr; this (junior) gets TTT1
        abbr = abbr[:3] + "1"
    return abbr


async def _next_inventory_number(session, abbr: str) -> str:
    """Generate the next inventory number in ABBR-0NNN format.
    Numbers start at 0200 and increment globally.
    """
    rows = (await session.execute(
        select(System.inventory_number).where(System.inventory_number.isnot(None))
    )).scalars().all()

    max_num = 199  # base — first assigned number will be 200
    for inv in rows:
        if inv and "-" in inv:
            try:
                num_part = int(inv.split("-", 1)[1])
                if num_part > max_num:
                    max_num = num_part
            except ValueError:
                pass

    return f"{abbr}-{max_num + 1:04d}"


@app.post("/systems")
async def system_create(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()

    ci = str(form.get("confidentiality_impact", "Low"))
    ii = str(form.get("integrity_impact", "Low"))
    ai = str(form.get("availability_impact", "Low"))

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso"])

        # Normalize and enforce unique 4-letter abbreviation
        abbr_raw = str(form.get("abbreviation", "")).strip()
        abbr = await _resolve_abbreviation(session, abbr_raw) if abbr_raw else "XXXX"

        # Auto-generate inventory number
        inv_num = await _next_inventory_number(session, abbr)

        sys = System(
            name                   = str(form.get("name", "")).strip(),
            abbreviation           = abbr,
            inventory_number       = inv_num,
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
            # Phase 17 — data sensitivity
            has_pii                = bool(form.get("has_pii")),
            has_phi                = bool(form.get("has_phi")),
            has_ephi               = bool(form.get("has_ephi")),
            has_financial_data     = bool(form.get("has_financial_data")),
            is_public_facing       = bool(form.get("is_public_facing")),
            has_cui                = bool(form.get("has_cui")),
            connects_to_federal    = bool(form.get("connects_to_federal")),
            categorization_status  = str(form.get("categorization_status", "draft")),
            categorization_note    = str(form.get("categorization_note", "")).strip() or None,
        )
        session.add(sys)
        await session.flush()
        sys_id = sys.id
        await _log_audit(session, user, "CREATE", "system", sys_id,
                         {"name": sys.name, "inventory_number": inv_num})
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

        # Linked assessments — cap at 5, track total
        asmt_total_ct = (await session.execute(
            select(func.count(Assessment.id)).where(Assessment.system_id == system_id)
        )).scalar() or 0
        asmt_rows = await session.execute(
            select(Assessment, Candidate)
            .join(Candidate, Assessment.candidate_id == Candidate.id)
            .where(Assessment.system_id == system_id)
            .order_by(Assessment.uploaded_at.desc())
            .limit(5)
        )
        assessments = [{"assessment": a, "candidate": c} for a, c in asmt_rows.all()]

        # Linked POA&Ms — cap at 10, ordered by severity, track total
        poam_total_ct = (await session.execute(
            select(func.count(PoamItem.id)).where(PoamItem.system_id == system_id)
        )).scalar() or 0
        poam_rows = await session.execute(
            select(PoamItem)
            .where(PoamItem.system_id == system_id)
            .order_by(PoamItem.severity, PoamItem.scheduled_completion)
            .limit(10)
        )
        poam_items = poam_rows.scalars().all()

        # Linked Risks — cap at 10, ordered by level, track total
        risk_total_ct = (await session.execute(
            select(func.count(Risk.id)).where(Risk.system_id == system_id)
        )).scalar() or 0
        risk_rows = await session.execute(
            select(Risk)
            .where(Risk.system_id == system_id)
            .order_by(Risk.risk_score.desc())
            .limit(10)
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

        _detail_role = await _get_user_role(request, session)
        can_edit = _detail_role in ("admin", "ao", "ciso")

        # Phase 25: today's logbook summary for Daily Ops tab badge
        _today_iso = date.today().isoformat()
        _detail_lb = (await session.execute(
            select(DailyLogbook)
            .where(DailyLogbook.remote_user == user)
            .where(DailyLogbook.system_id == system_id)
            .where(DailyLogbook.log_date == _today_iso)
        )).scalar_one_or_none()
        _detail_task_nums  = _p25_task_config(_detail_role)
        _detail_flags      = json.loads(_detail_lb.task_flags) if (_detail_lb and _detail_lb.task_flags) else {}
        _daily_tasks_done  = sum(1 for t in _detail_task_nums if _detail_flags.get(str(t)))
        _daily_tasks_total = len(_detail_task_nums)

    today_str = date.today().isoformat()
    poam_overdue  = [p for p in poam_items if p.scheduled_completion and p.scheduled_completion < today_str and p.status in ("open","in_progress")]
    poam_due_week = [p for p in poam_items if p.scheduled_completion and today_str <= p.scheduled_completion <= (date.today() + timedelta(days=7)).isoformat() and p.status in ("open","in_progress")]
    poam_open_ct  = sum(1 for p in poam_items if p.status in ("open","in_progress"))

    return templates.TemplateResponse("system_detail.html", {
        "request":                 request,
        "system":                  sys,
        "assessments":             assessments,
        "asmt_total_ct":           asmt_total_ct,
        "poam_items":              poam_items,
        "poam_total_ct":           poam_total_ct,
        "risks":                   risks,
        "risk_total_ct":           risk_total_ct,
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
        "can_edit":                can_edit,
        "daily_tasks_done":        _daily_tasks_done,
        "daily_tasks_total":       _daily_tasks_total,
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
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso"])

        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404)

        ctx = await _full_ctx(request, session,
                              system=sys,
                              action=f"/systems/{system_id}/edit")

    return templates.TemplateResponse("system_form.html", ctx)


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
        # Only AO, CISO, and admin may modify onboarded system fields
        _effective_role = await _get_user_role(request, session)
        _require_role(_effective_role, ["admin", "ao", "ciso"])

        sys_row = await session.execute(
            select(System).where(System.id == system_id)
        )
        sys = sys_row.scalar_one_or_none()
        if not sys:
            raise HTTPException(status_code=404)

        sys.name                   = str(form.get("name", "")).strip() or sys.name
        abbr_raw = str(form.get("abbreviation", "")).strip()
        sys.abbreviation = await _resolve_abbreviation(session, abbr_raw, exclude_id=system_id) if abbr_raw else sys.abbreviation
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
        # Authorization fields — AO/admin only; CISO cannot sign/change ATO status
        if _effective_role in ("admin", "ao"):
            sys.auth_status  = str(form.get("auth_status", "not_authorized"))
            sys.auth_date    = str(form.get("auth_date", "")).strip() or None
            sys.auth_expiry  = str(form.get("auth_expiry", "")).strip() or None
        sys.updated_at             = datetime.now(timezone.utc)
        # Phase 17 — data sensitivity
        sys.has_pii               = bool(form.get("has_pii"))
        sys.has_phi               = bool(form.get("has_phi"))
        sys.has_ephi              = bool(form.get("has_ephi"))
        sys.has_financial_data    = bool(form.get("has_financial_data"))
        sys.is_public_facing      = bool(form.get("is_public_facing"))
        sys.has_cui               = bool(form.get("has_cui"))
        sys.connects_to_federal   = bool(form.get("connects_to_federal"))
        cat_status = str(form.get("categorization_status", "draft"))
        sys.categorization_status = cat_status
        sys.categorization_note   = str(form.get("categorization_note", "")).strip() or None

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
    status_filter   = request.query_params.get("status", "open")   # open|in_progress|all|closed
    severity_filter = request.query_params.get("severity", "")
    system_filter   = request.query_params.get("system_id", "")
    crit_high_filter = request.query_params.get("crit_high", "")   # "1" → Critical+High only
    overdue_filter   = request.query_params.get("overdue", "")     # "1" → past due date
    due_soon_filter  = request.query_params.get("due_soon", "")    # "1" → due within 7 days
    try:
        PAGE_SIZE = max(10, min(int(request.query_params.get("per_page", 10)), 100))
    except ValueError:
        PAGE_SIZE = 10
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    async with SessionLocal() as session:
        # Scope to assigned systems for employees; AO and CISO see org-wide
        scoped_sys_ids: list | None = None
        _poam_role = await _get_user_role(request, session)
        if not (is_adm or _poam_role in ("ao", "ciso")):
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
            if crit_high_filter == "1":
                base_q = base_q.where(PoamItem.severity.in_(["Critical", "High"]))
            elif severity_filter:
                base_q = base_q.where(PoamItem.severity == severity_filter)
            if overdue_filter == "1":
                base_q = base_q.where(PoamItem.scheduled_completion < today_str) \
                               .where(PoamItem.scheduled_completion.isnot(None))
            if due_soon_filter == "1":
                base_q = base_q.where(PoamItem.scheduled_completion >= today_str) \
                               .where(PoamItem.scheduled_completion <= week_str)
            if system_filter:
                base_q = base_q.where(PoamItem.system_id == system_filter)
            return base_q

        # Stat counts (indexed queries, no full table scan for rendering)
        open_statuses = list(POAM_ACTIVE_STATUSES)
        base_open = select(func.count(PoamItem.id)).where(PoamItem.status.in_(open_statuses))
        if scoped_sys_ids is not None:
            base_open = base_open.where(PoamItem.system_id.in_(scoped_sys_ids))

        total_open   = (await session.execute(base_open)).scalar() or 0
        total_all_q = select(func.count(PoamItem.id))
        if scoped_sys_ids is not None:
            total_all_q = total_all_q.where(PoamItem.system_id.in_(scoped_sys_ids))
        total_all = (await session.execute(total_all_q)).scalar() or 0
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

        # Severity breakdown scoped to the STATUS filter only (not bottom-form filters).
        # This lets the top status buttons drive the breakdown; manual filters don't affect it.
        sev_base = select(func.count(PoamItem.id))
        if scoped_sys_ids is not None:
            sev_base = sev_base.where(PoamItem.system_id.in_(scoped_sys_ids))
        if status_filter == "all":
            pass  # all statuses
        elif status_filter == "open":
            sev_base = sev_base.where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
        elif status_filter == "closed":
            sev_base = sev_base.where(PoamItem.status.in_(list(POAM_CLOSED_STATUSES)))
        else:
            sev_base = sev_base.where(PoamItem.status == status_filter)
        sev_counts = {}
        for sev in ("Critical", "High", "Moderate", "Low"):
            ct = (await session.execute(
                sev_base.where(PoamItem.severity == sev)
            )).scalar() or 0
            sev_counts[sev] = ct
        sev_filter_label = {
            "open": "Active", "closed": "Closed", "all": "All"
        }.get(status_filter, POAM_STATUS_LABELS.get(status_filter, status_filter.replace("_", " ").title()))

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
        "request":           request,
        "page_items":        page_items,
        "total_all":         total_all,
        "total_open":        total_open,
        "crit_high_ct":      crit_high_ct,
        "overdue_ct":        overdue_ct,
        "due_soon_ct":       due_soon_ct,
        "closed_month_ct":   closed_month_ct,
        "sev_counts":        sev_counts,
        "sev_filter_label":  sev_filter_label,
        "aging":             aging,
        "systems_map":       systems_map,
        "all_sys":           all_sys,
        "status_filter":     status_filter,
        "severity_filter":   severity_filter,
        "system_filter":     system_filter,
        "crit_high_filter":  crit_high_filter,
        "overdue_filter":    overdue_filter,
        "due_soon_filter":   due_soon_filter,
        "page":              page,
        "total_pages":       total_pages,
        "total_filtered":    total_filtered,
        "today_str":         today_str,
        "week_str":          week_str,
        "poam_statuses":     POAM_STATUSES,
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

    async with SessionLocal() as _role_session:
        _import_role = await _get_user_role(request, _role_session)
        _require_role(_import_role, ["admin", "issm", "isso"])

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
                control_id=(row.get("control_id") or "").strip().upper() or None,
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
        role = await _get_user_role(request, session)

    catalog_ids = sorted(CATALOG.keys()) if CATALOG else []

    return templates.TemplateResponse("poam_item.html", {
        "request":            request,
        "item":               None,
        "systems":            systems,
        "evidence_files":     [],
        "assessment_id":      assessment_id,
        "control_id":         control_id,
        "action":             "/poam",
        "poam_statuses":      POAM_STATUSES,
        "poam_status_labels": POAM_STATUS_LABELS,
        "allowed_statuses":   list(POAM_PUSH_POWER.keys()),
        "catalog_ids":        catalog_ids,
        "user_role":          role,
        **_tpl_ctx(request),
    })


@app.post("/poam")
async def poam_create(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    form = await request.form()
    sys_id     = str(form.get("system_id", "")).strip() or None
    ctrl_id    = (str(form.get("control_id", "")).strip().upper() or None)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso", "sca"])

        # Resolve system abbreviation for POAM ID
        abbr = "XXXX"
        if sys_id:
            sys_row = await session.execute(select(System).where(System.id == sys_id))
            sys_obj = sys_row.scalar_one_or_none()
            if sys_obj:
                abbr = (sys_obj.abbreviation or sys_obj.name[:4] or "XXXX")
        # Serial = total count of existing items + 1000
        total_ct = (await session.execute(select(func.count(PoamItem.id)))).scalar() or 0
        serial = 1000 + total_ct
        poam_id_val = _generate_poam_id(abbr, ctrl_id, serial)

        item = PoamItem(
            poam_id              = poam_id_val,
            system_id            = sys_id,
            assessment_id        = str(form.get("assessment_id", "")).strip() or None,
            control_id           = ctrl_id,
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
        session.add(item)
        await session.flush()
        item_id = item.id
        await _log_audit(session, user, "CREATE", "poam", item_id,
                         {"poam_id": poam_id_val, "weakness": item.weakness_name, "severity": item.severity})
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

        # Evidence files
        ev_rows = await session.execute(
            select(PoamEvidence)
            .where(PoamEvidence.poam_item_id == item_id)
            .order_by(PoamEvidence.uploaded_at)
        )
        evidence_files = ev_rows.scalars().all()

        role = await _get_user_role(request, session)

    allowed_statuses = _poam_allowed_statuses(role, item.status if item else "open")
    catalog_ids = sorted(CATALOG.keys()) if CATALOG else []

    return templates.TemplateResponse("poam_item.html", {
        "request":            request,
        "item":               item,
        "systems":            systems,
        "linked_system":      linked_system,
        "evidence_files":     evidence_files,
        "action":             f"/poam/{item_id}/update",
        "poam_statuses":      POAM_STATUSES,
        "poam_status_labels": POAM_STATUS_LABELS,
        "allowed_statuses":   allowed_statuses,
        "poam_push_power":    POAM_PUSH_POWER,
        "catalog_ids":        catalog_ids,
        "user_role":          role,
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

        role = await _get_user_role(request, session)
        if role in _READ_ONLY_ROLES:
            raise HTTPException(status_code=403, detail="Your role cannot update POA&M items")
        new_status = str(form.get("status", item.status))
        old_status = item.status
        # Role-based push-power check — always verify, even for same-status submissions.
        # This prevents non-privileged roles from silently "reaffirming" terminal states
        # (e.g. sca resubmitting a form on a closed_verified POAM).
        if new_status not in POAM_STATUSES:
            new_status = item.status
        else:
            allowed = _poam_allowed_statuses(role, item.status)
            if new_status not in allowed:
                raise HTTPException(status_code=403,
                                    detail=f"Role '{role}' cannot set status to '{new_status}'")

        item.system_id            = str(form.get("system_id", "")).strip() or None
        item.control_id           = (str(form.get("control_id", "")).strip().upper() or None)
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
        item.residual_risk        = str(form.get("residual_risk", "")).strip() or None
        item.risk_accept_review   = str(form.get("risk_accept_review", "")).strip() or None
        item.completion_date      = str(form.get("completion_date", "")).strip() or None
        item.comments             = str(form.get("comments", "")).strip() or None
        # Blocked fields
        item.blocker_category     = str(form.get("blocker_category", "")).strip() or None
        item.blocker_owner        = str(form.get("blocker_owner", "")).strip() or None
        item.unblock_plan         = str(form.get("unblock_plan", "")).strip() or None
        # Verification fields
        item.verifier             = str(form.get("verifier", "")).strip() or None
        item.verification_date    = str(form.get("verification_date", "")).strip() or None
        item.verification_method  = str(form.get("verification_method", "")).strip() or None
        # Waiver fields
        item.waiver_start         = str(form.get("waiver_start", "")).strip() or None
        item.waiver_end           = str(form.get("waiver_end", "")).strip() or None
        item.monitoring_checkpoints = str(form.get("monitoring_checkpoints", "")).strip() or None
        item.compensating_controls  = str(form.get("compensating_controls", "")).strip() or None
        # False positive field
        item.non_applicability_rationale = str(form.get("non_applicability_rationale", "")).strip() or None
        item.updated_at           = datetime.now(timezone.utc)
        if new_status == "closed_verified" and not item.completion_date:
            item.completion_date = date.today().isoformat()
        # Accepted Risk flow: ISSO creates → pending AO; AO/Admin → approved directly
        if new_status == "accepted_risk" and old_status != "accepted_risk":
            item.approval_stage = "pending_ao" if role in ("isso", "sca", "system_owner") else "approved"
        elif new_status not in ("accepted_risk", "deferred_waiver"):
            item.approval_stage = None
        # Record approval event when status changes
        if new_status != old_status:
            import json as _json
            trail = []
            try:
                trail = _json.loads(item.signoff_trail or "[]")
            except Exception:
                trail = []
            trail.append({
                "role": role, "user": user, "date": date.today().isoformat(),
                "action": f"{old_status}→{new_status}", "notes": ""
            })
            item.signoff_trail = _json.dumps(trail)

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


@app.post("/poam/{item_id}/evidence")
async def poam_evidence_upload(request: Request, item_id: str,
                                file: UploadFile = File(...),
                                description: str = Form("")):
    """Upload a closure evidence file for a POA&M item."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        row = await session.execute(select(PoamItem).where(PoamItem.id == item_id))
        item = row.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404)

    # Validate file type
    _ALLOWED_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt",
                    ".png", ".jpg", ".jpeg", ".gif", ".webp"}
    _ext = Path(file.filename or "file").suffix.lower()
    if _ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"File type '{_ext}' not allowed")

    # Save file
    ev_dir = Path("data/uploads/poam_evidence")
    ev_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "file")
    dest = ev_dir / f"{item_id[:8]}_{safe_name}"
    content = await file.read()
    dest.write_bytes(content)

    async with SessionLocal() as session:
        ev = PoamEvidence(
            poam_item_id = item_id,
            filename     = safe_name,
            file_path    = str(dest),
            file_size    = len(content),
            uploaded_by  = user,
            description  = description.strip() or None,
        )
        session.add(ev)
        await session.commit()

    return RedirectResponse(url=f"/poam/{item_id}", status_code=303)


@app.get("/poam/{item_id}/evidence/{ev_id}")
async def poam_evidence_download(request: Request, item_id: str, ev_id: str):
    """Download a closure evidence file."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        row = await session.execute(
            select(PoamEvidence).where(PoamEvidence.id == ev_id,
                                       PoamEvidence.poam_item_id == item_id)
        )
        ev = row.scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=404)
    from fastapi.responses import FileResponse
    return FileResponse(ev.file_path, filename=ev.filename)


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
        # AO and CISO see org-wide risks; all others scoped to assigned systems
        scoped_sys_ids: list | None = None
        _risk_role = await _get_user_role(request, session)
        if not (is_adm or _risk_role in ("ao", "ciso")):
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
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso", "sca", "system_owner"])

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
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso", "sca", "system_owner"])

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

def _build_appendix_items(
    ato_docs: list,
    artifacts: list,
    mode: str,
) -> list[dict]:
    """Build appendix item list for SSP export.

    Each item has:
      label         — "Appendix A", "Appendix B", …
      doc_id        — short reference ID
      title         — human-readable title
      doc_type      — ATO doc_type or artifact_type
      version       — version string or "—"
      date          — ISO date or "—"
      owner         — assigned_to / owner / created_by
      storage_ref   — file_path basename or "—"
      content_b64   — base64-encoded file bytes (Full Report only, None otherwise)
      content_mime  — MIME type for embedding
      has_file      — True if a physical file exists on disk
    """
    import base64 as _b64, mimetypes as _mt

    _MIME_DEFAULTS = {
        ".pdf":  "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt":  "text/plain",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    _EMBEDDABLE = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}

    items: list[dict] = []
    # Label counter A-Z then AA, AB …
    def _label(n: int) -> str:
        if n < 26:
            return f"Appendix {chr(65 + n)}"
        return f"Appendix {chr(65 + n // 26 - 1)}{chr(65 + n % 26)}"

    idx = 0
    for doc in ato_docs:
        fpath   = doc.file_path
        has_f   = bool(fpath and Path(fpath).exists())
        suffix  = Path(fpath).suffix.lower() if fpath else ""
        mime    = _MIME_DEFAULTS.get(suffix, "application/octet-stream")
        b64     = None
        if mode == "full" and has_f and suffix in _EMBEDDABLE:
            try:
                b64 = _b64.b64encode(Path(fpath).read_bytes()).decode()
            except Exception:
                b64 = None
        items.append({
            "label":       _label(idx),
            "doc_id":      f"DOC-{doc.id[:6].upper()}",
            "title":       doc.title,
            "doc_type":    doc.doc_type,
            "version":     doc.version or "—",
            "date":        doc.updated_at.strftime("%Y-%m-%d") if doc.updated_at else "—",
            "owner":       doc.assigned_to or doc.created_by or "—",
            "storage_ref": Path(fpath).name if fpath else "—",
            "content_b64": b64,
            "content_mime": mime,
            "has_file":    has_f,
            "embeddable":  suffix in _EMBEDDABLE,
        })
        idx += 1

    for art in artifacts:
        fpath   = art.file_path
        has_f   = bool(fpath and Path(fpath).exists())
        suffix  = Path(fpath).suffix.lower() if fpath else ""
        mime    = _MIME_DEFAULTS.get(suffix, "application/octet-stream")
        b64     = None
        if mode == "full" and has_f and suffix in _EMBEDDABLE:
            try:
                b64 = _b64.b64encode(Path(fpath).read_bytes()).decode()
            except Exception:
                b64 = None
        items.append({
            "label":       _label(idx),
            "doc_id":      f"ART-{art.id[:6].upper()}",
            "title":       art.title,
            "doc_type":    art.artifact_type or "evidence",
            "version":     getattr(art, "version", "—") or "—",
            "date":        art.collected_at.strftime("%Y-%m-%d") if art.collected_at else
                           (art.created_at.strftime("%Y-%m-%d") if art.created_at else "—"),
            "owner":       art.owner or art.created_by or "—",
            "storage_ref": Path(fpath).name if fpath else "—",
            "content_b64": b64,
            "content_mime": mime,
            "has_file":    has_f,
            "embeddable":  suffix in _EMBEDDABLE,
        })
        idx += 1
    return items


@app.get("/ssp/{assessment_id}", response_class=HTMLResponse)
async def ssp_document(request: Request, assessment_id: str,
                       mode: Optional[str] = None):
    """SSP HTML export.

    mode=None      → mode selection screen
    mode=full      → Full Report (appendices embedded as base64 in-document)
    mode=controls  → Controls Only (appendix listing table, no file embedding)
    """
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        asmt      = await _get_assessment(assessment_id, session)
        candidate = await _get_candidate(asmt.candidate_id, session)

        # Mode selection screen — shown before loading heavy data
        if not mode or mode not in ("full", "controls"):
            return templates.TemplateResponse("ssp_mode_select.html", {
                "request":       request,
                "assessment_id": assessment_id,
                "assessment":    asmt,
                "candidate":     candidate,
                "brand":         _cfg("app.brand", "TheKramerica"),
                **_tpl_ctx(request),
            })

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

        # Load appendix sources: ATO documents + artifacts for the system
        ato_docs:  list = []
        artifacts: list = []
        if asmt.system_id:
            ato_rows = await session.execute(
                select(AtoDocument)
                .where(AtoDocument.system_id == asmt.system_id)
                .where(AtoDocument.status.in_(["approved", "finalized"]))
                .order_by(AtoDocument.doc_type, AtoDocument.title)
            )
            ato_docs = list(ato_rows.scalars().all())

            art_rows = await session.execute(
                select(Artifact)
                .where(Artifact.system_id == asmt.system_id)
                .where(Artifact.approval_status == "approved")
                .order_by(Artifact.artifact_type, Artifact.title)
            )
            artifacts = list(art_rows.scalars().all())

        appendix_items = _build_appendix_items(ato_docs, artifacts, mode)

        await _log_audit(session, user, "EXPORT", "assessment", assessment_id,
                         {"format": f"ssp_{mode}"})
        await session.commit()

    return templates.TemplateResponse("ssp_export.html", {
        "request":         request,
        "assessment_id":   assessment_id,
        "assessment":      asmt,
        "candidate":       candidate,
        "controls":        controls,
        "linked_system":   linked_system,
        "poam_items":      poam_items,
        "ssp_mode":        mode,               # "full" | "controls"
        "appendix_items":  appendix_items,
        "generated_at":    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "brand":           _cfg("app.brand", "TheKramerica"),
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


@app.get("/api/version")
async def api_version():
    """Build stamp / version info endpoint."""
    return {
        "app":      _cfg("app.name", "BLACKSITE"),
        "env":      _cfg("app.env", "production"),
        "sha":      _BUILD_SHA,
        "sha_long": _BUILD_SHA_L,
        "built":    _BUILD_TIME_UTC,
        "port":     int(_cfg("app.port", 8100)),
    }


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
        # System scope: admin/AO/CISO see org-wide; others scoped to assigned systems
        _posture_role = await _get_user_role(request, session)
        if is_adm or _posture_role in ("ao", "ciso"):
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

def _ctrl_sort_key(cid: str) -> tuple:
    """Natural numeric sort: ac-1 → ('ac',1,0), ac-2.1 → ('ac',2,1), ac-10 → ('ac',10,0)."""
    m = _re.match(r'^([a-z]+)-(\d+)(?:\.(\d+))?$', cid)
    if m:
        return (m.group(1), int(m.group(2)), int(m.group(3) or 0))
    return (cid, 0, 0)


def _catalog_list() -> list[dict]:
    """Flatten CATALOG dict to naturally-sorted list of control dicts."""
    items = []
    for ctrl_id, ctrl in CATALOG.items():
        meta        = _CTRL_META.get(ctrl_id, {})
        family_id   = ctrl.get("family_id", ctrl_id.split("-")[0].upper())
        family_title = ctrl.get("family_title", "")
        # Card summary: first sentence of supplemental guidance (readable prose)
        raw_guide   = meta.get("supplemental", "") or ctrl.get("guidance", "")
        summary     = _first_sentence(raw_guide, max_len=185) if raw_guide else ""
        # Enhancement marker: ac-2.1 is an enhancement of AC-2
        is_enhancement = "." in ctrl_id
        items.append({
            "id":            ctrl_id,
            "family":        family_id,
            "family_title":  family_title,
            "title":         ctrl.get("title", ""),
            "summary":       summary,
            "is_enhancement": is_enhancement,
            "statement":     ctrl.get("statement", ""),   # kept for full-text search
            "text":          summary,                      # template compat alias
        })
    items.sort(key=lambda x: _ctrl_sort_key(x["id"]))
    return items


def _ctrl_families() -> list[tuple[str, str]]:
    """Return sorted list of (family_id, family_title) tuples."""
    seen: dict[str, str] = {}
    for ctrl in CATALOG.values():
        fid   = ctrl.get("family_id", "")
        title = ctrl.get("family_title", "")
        if fid and fid not in seen:
            seen[fid] = title
    return sorted(seen.items())


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
                            page: int = 1, per_page: int = 20):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    all_items = _catalog_list()
    families  = _ctrl_families()

    family_upper = family.upper()
    if family_upper:
        all_items = [c for c in all_items if c["family"] == family_upper]
    if q:
        ql = q.lower()
        all_items = [c for c in all_items if
                     ql in c["id"].lower() or
                     ql in c["title"].lower() or
                     ql in c.get("summary", "").lower() or
                     ql in c.get("statement", "").lower()]

    per_page = max(10, min(per_page, 100))
    page     = max(1, page)
    total    = len(all_items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page     = min(page, total_pages)
    offset   = (page - 1) * per_page
    items    = all_items[offset : offset + per_page]

    return templates.TemplateResponse("controls.html", {
        "request":        request,
        "items":          items,
        "families":       families,      # list of (family_id, family_title) tuples
        "family":         family_upper,
        "q":              q,
        "total":          len(CATALOG),
        "filtered_total": total,
        "page":           page,
        "total_pages":    total_pages,
        "per_page":       per_page,
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

    meta         = _CTRL_META.get(ctrl_id.lower(), {})
    assess_ctx   = _build_assessment_ctx(ctrl_id.lower())

    # Prev/next navigation within the full sorted catalog
    all_ids = [c["id"] for c in _catalog_list()]
    try:
        idx = all_ids.index(ctrl_id.lower())
    except ValueError:
        idx = -1
    prev_ctrl_id = all_ids[idx - 1] if idx > 0 else None
    next_ctrl_id = all_ids[idx + 1] if 0 <= idx < len(all_ids) - 1 else None

    return templates.TemplateResponse("control_detail.html", {
        "request":       request,
        "ctrl_id":       ctrl_id.lower(),
        "ctrl":          ctrl,
        "meta":          meta,
        "assess_ctx":    assess_ctx,
        "overlay_urls":  _OVERLAY_URLS,
        "csf_base_url":  _CSF_BASE_URL,
        "prev_ctrl_id":  prev_ctrl_id,
        "next_ctrl_id":  next_ctrl_id,
        **_tpl_ctx(request),
    })


# ── System Control Plan ───────────────────────────────────────────────────────

@app.get("/systems/{system_id}/controls", response_class=HTMLResponse)
async def system_controls_page(request: Request, system_id: str, family: str = "", status_filter: str = "",
                                page: int = 1, per_page: int = 25):
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

    # Pagination — applied after filter
    per_page   = max(10, min(per_page, 200))
    page       = max(1, page)
    total_count = len(controls)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page        = min(page, total_pages)
    offset      = (page - 1) * per_page
    controls    = controls[offset:offset + per_page]

    return templates.TemplateResponse("system_controls.html", {
        "request":       request,
        "system":        system,
        "controls":      controls,
        "stats":         stats,
        "families":      _ctrl_families(),
        "family":        family.upper(),
        "status_filter": status_filter,
        "other_systems": other_systems,
        "page":          page,
        "per_page":      per_page,
        "total_pages":   total_pages,
        "total_count":   total_count,
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

        _ctrl_role = await _get_user_role(request, session)
        if not _is_admin(request) and _ctrl_role in _READ_ONLY_ROLES:
            raise HTTPException(status_code=403,
                                detail="Your role does not have permission to update controls")

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


# ── ISSO Control Workspace ─────────────────────────────────────────────────────

@app.get("/systems/{system_id}/workspace/{ctrl_id}", response_class=HTMLResponse)
async def isso_control_workspace_get(request: Request, system_id: str, ctrl_id: str):
    """ISSO per-control implementation workspace — view only for auditors/sca, editable for isso/ciso/ao/admin."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    ctrl_id = ctrl_id.lower()

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso", "sca", "auditor"])

        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403, detail="Not assigned to this system")

        sys_row = await session.execute(select(System).where(System.id == system_id))
        system = sys_row.scalar_one_or_none()
        if not system:
            raise HTTPException(status_code=404)

        sc_row = await session.execute(
            select(SystemControl)
            .where(SystemControl.system_id == system_id)
            .where(SystemControl.control_id == ctrl_id)
        )
        sc = sc_row.scalar_one_or_none()

        # Other systems for inheritance dropdown
        other_sys_rows = await session.execute(
            select(System).where(System.id != system_id).order_by(System.name).limit(100)
        )
        other_systems = list(other_sys_rows.scalars().all())

        await _log_audit(session, user, "VIEW", "system_control",
                         f"{system_id}:{ctrl_id}", {"page": "workspace"})
        await session.commit()

    # Catalog data for this control
    cat_ctrl = CATALOG.get(ctrl_id, {})
    if not cat_ctrl:
        raise HTTPException(status_code=404, detail=f"Control '{ctrl_id}' not found in catalog")

    # Prev / next controls in catalog for navigation
    all_ctrl_ids = list(CATALOG.keys())
    try:
        idx = all_ctrl_ids.index(ctrl_id)
    except ValueError:
        idx = -1
    prev_ctrl = all_ctrl_ids[idx - 1] if idx > 0 else None
    next_ctrl = all_ctrl_ids[idx + 1] if idx >= 0 and idx < len(all_ctrl_ids) - 1 else None

    can_edit = role in ("admin", "ao", "ciso", "isso")

    return templates.TemplateResponse("system_control_detail.html", {
        "request":       request,
        "system":        system,
        "ctrl_id":       ctrl_id,
        "cat_ctrl":      cat_ctrl,
        "sc":            sc,
        "prev_ctrl":     prev_ctrl,
        "next_ctrl":     next_ctrl,
        "can_edit":      can_edit,
        "other_systems": other_systems,
        **_tpl_ctx(request),
    })


@app.post("/systems/{system_id}/workspace/{ctrl_id}")
async def isso_control_workspace_post(request: Request, system_id: str, ctrl_id: str):
    """ISSO workspace — save/upsert SystemControl record."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    ctrl_id = ctrl_id.lower()

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "isso"])

        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        form = await request.form()
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
                system_id      = system_id,
                control_id     = ctrl_id,
                control_family = ctrl_id.split("-")[0].upper(),
                control_title  = cat_ctrl.get("title", ""),
                created_by     = user,
            )
            session.add(sc)

        # Evidence enforcement: block "implemented_complete" on evidence-required controls
        # when no formal artifact or assessment has been recorded for this system.
        if new_status == "implemented_complete" and ctrl_id in _EVIDENCE_REQUIRED_CONTROLS:
            artifact_count = (await session.execute(
                select(func.count(Artifact.id))
                .where(Artifact.system_id == system_id)
                .where(Artifact.status.in_(["approved", "finalized"]))
            )).scalar() or 0
            if artifact_count == 0:
                return templates.TemplateResponse(
                    "system_control_detail.html",
                    {
                        **(await _full_ctx(request, session)),
                        "error": (
                            f"Control {ctrl_id.upper()} requires formal evidence before marking "
                            f"'Implemented (Complete)'. Upload an approved artifact or assessment "
                            f"result for this system first."
                        ),
                        "system_id": system_id,
                        "ctrl_id": ctrl_id,
                    },
                    status_code=422,
                )

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
                         {"status": new_status, "via": "workspace"})
        await session.commit()

    return RedirectResponse(
        url=f"/systems/{system_id}/workspace/{ctrl_id}?saved=1",
        status_code=303
    )


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

        _sub_role = await _get_user_role(request, session)
        _require_role(_sub_role, ["admin", "ao", "ciso", "issm", "isso"])

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

from app.rss_feed import get_feed_items, get_all_feed_items, fetch_one_for_test, _get_cached

@app.get("/api/notifications")
async def api_notifications(request: Request, limit: int = 20, unread_only: bool = False):
    """Return in-app notifications for the current user."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        q = select(Notification).where(Notification.remote_user == user)
        if unread_only:
            q = q.where(Notification.is_read == False)
        q = q.order_by(Notification.created_at.desc()).limit(limit)
        rows = (await session.execute(q)).scalars().all()
        return [{"id": n.id, "type": n.notif_type, "title": n.title,
                 "body": n.body, "action_url": n.action_url,
                 "is_read": n.is_read, "created_at": n.created_at.isoformat() if n.created_at else None}
                for n in rows]


@app.post("/api/notifications/{notif_id}/read")
async def api_notification_read(request: Request, notif_id: int):
    """Mark a notification as read."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        n = await session.get(Notification, notif_id)
        if n and n.remote_user == user:
            n.is_read = True
            n.read_at = datetime.now(timezone.utc)
            await session.commit()
    return {"ok": True}


@app.post("/api/notifications/read-all")
async def api_notifications_read_all(request: Request):
    """Mark all notifications as read for current user."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE notifications SET is_read=1, read_at=:ts WHERE remote_user=:u AND is_read=0"),
            {"ts": datetime.now(timezone.utc), "u": user}
        )
        await session.commit()
    return {"ok": True}


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, unread: bool = False, limit: int = 40):
    """Full notifications inbox page."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    limit = max(10, min(limit, 200))
    async with SessionLocal() as session:
        base_q = select(Notification).where(Notification.remote_user == user)
        if unread:
            base_q = base_q.where(Notification.is_read == False)
        rows = (await session.execute(
            base_q.order_by(Notification.created_at.desc()).limit(limit)
        )).scalars().all()
        count_q = select(func.count()).select_from(Notification).where(Notification.remote_user == user)
        if unread:
            count_q = count_q.where(Notification.is_read == False)
        total_count = (await session.execute(count_q)).scalar() or 0
        unread_count = (await session.execute(
            select(func.count()).select_from(Notification)
            .where(Notification.remote_user == user)
            .where(Notification.is_read == False)
        )).scalar() or 0
        ctx = await _full_ctx(request, session,
                              notifications=rows,
                              unread_count=unread_count,
                              total_count=total_count,
                              unread_only=unread)
    return templates.TemplateResponse("notifications.html", {"request": request, **ctx})


@app.post("/api/heartbeat")
async def api_heartbeat(request: Request):
    """Reset idle session timer for the current user. Called every 5 min by client JS."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if user not in _SESSION_EXEMPT:
        _LAST_ACTIVITY[user] = datetime.now(timezone.utc)  # BLKS022826-1003AC03
    return {"ok": True, "next_in": 300}


@app.patch("/api/preferences")
async def api_preferences(request: Request):
    """H6: Save UI preferences to UserProfile and set long-lived cookies."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    form = await request.form()
    _valid_font = {"12px", "14px", "16px", "18px", "20px"}
    _valid_dens = {"compact", "comfortable", "spacious"}
    _valid_rows = {10, 25, 50, 100}

    font_size = str(form.get("font_size", "14px")).strip()
    density   = str(form.get("density", "comfortable")).strip()
    try:
        rows = int(form.get("rows_per_page", 25))
    except (ValueError, TypeError):
        rows = 25

    font_size = font_size if font_size in _valid_font else "14px"
    density   = density   if density   in _valid_dens else "comfortable"
    rows      = rows      if rows      in _valid_rows else 25

    async with SessionLocal() as session:
        profile = await session.get(UserProfile, user)
        if not profile:
            profile = UserProfile(remote_user=user)
            session.add(profile)
        profile.pref_font_size     = font_size
        profile.pref_density       = density
        profile.pref_rows_per_page = rows
        await session.commit()

    resp = JSONResponse({"ok": True, "font_size": font_size, "density": density,
                         "rows_per_page": rows})
    resp.set_cookie("bsv_pref_font",    font_size, max_age=365*24*3600, httponly=False, samesite="lax")
    resp.set_cookie("bsv_pref_density", density,   max_age=365*24*3600, httponly=False, samesite="lax")
    resp.set_cookie("bsv_pref_rows",    str(rows), max_age=365*24*3600, httponly=False, samesite="lax")
    return resp


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


# ── Scheduled alert endpoints (called by systemd timer scripts) ────────────────

def _telegram_send(message: str) -> bool:
    """Fire-and-forget Telegram notification via notify-telegram.sh."""
    import subprocess as _sub
    notify = "/home/graycat/scripts/notify-telegram.sh"
    try:
        _sub.run([notify, message], timeout=10, check=False,
                 capture_output=True)
        return True
    except Exception:
        return False


@app.get("/api/alerts/ato-expiry")
async def api_ato_expiry_alerts(request: Request):
    """
    Scheduled: check ATO expiry windows and send Telegram alerts.
    Thresholds: 90d, 60d, 30d before expiry + expired.
    Admin-only. Called daily by bsv-ato-alerts.timer.
    Dedupe: one alert per system per threshold window per day (via SystemSettings key).
    """
    user = request.headers.get("Remote-User", "")
    if not user or not _is_admin(request):
        raise HTTPException(status_code=403)

    today = date.today()
    today_str = today.isoformat()
    alerts_sent = 0
    alert_detail = []

    async with SessionLocal() as session:
        systems = (await session.execute(
            select(System)
            .where(System.deleted_at.is_(None))
            .where(System.auth_expiry.isnot(None))
            .where(System.auth_status.in_(["authorized", "expired"]))
        )).scalars().all()

        for sys in systems:
            try:
                exp = date.fromisoformat(sys.auth_expiry)
            except (ValueError, TypeError):
                continue

            days_left = (exp - today).days
            threshold = None
            tier = None
            if days_left < 0:
                threshold = "expired"
                tier = "🔴 EXPIRED"
            elif days_left <= 30:
                threshold = "30d"
                tier = "🟠 30-day warning"
            elif days_left <= 60:
                threshold = "60d"
                tier = "🟡 60-day warning"
            elif days_left <= 90:
                threshold = "90d"
                tier = "📋 90-day notice"

            if not threshold:
                continue

            # Dedupe: skip if alert already sent today for this system+threshold
            dedupe_key = f"ato_alert:{sys.id}:{threshold}:{today_str}"
            existing = await session.get(SystemSettings, dedupe_key)
            if existing:
                continue

            alerts_sent += 1
            alert_detail.append({"system": sys.name, "expiry": sys.auth_expiry,
                                  "days_left": days_left, "threshold": threshold,
                                  "tier": tier})

            # Record dedupe key (prevents re-alert today)
            session.add(SystemSettings(key=dedupe_key, value=today_str))

        await session.commit()

    # ── Send Telegram digest (batch to prevent alert flooding) ────────────────
    # ≤ 5 alerts: individual messages per system
    # > 5 alerts: one digest summary (prevents 100+ messages on first run with seed data)
    if alert_detail:
        if len(alert_detail) <= 5:
            for item in alert_detail:
                days_left = item["days_left"]
                _telegram_send(
                    f"{'🔴' if item['threshold']=='expired' else '⚠️'} "
                    f"*BLACKSITE ATO Alert — {item['tier']}*\n\n"
                    f"*System:* {item['system']}\n"
                    f"*ATO Expiry:* {item['expiry']}\n"
                    f"*Days:* {'EXPIRED ({} days ago)'.format(-days_left) if days_left < 0 else str(days_left)}\n"
                    f"*Action:* Begin reauthorization package.\n"
                    f"Review: https://blacksite.borisov.network/systems"
                )
        else:
            # Digest summary
            expired_ct = sum(1 for a in alert_detail if a["threshold"] == "expired")
            warn30_ct  = sum(1 for a in alert_detail if a["threshold"] == "30d")
            warn60_ct  = sum(1 for a in alert_detail if a["threshold"] == "60d")
            notice_ct  = sum(1 for a in alert_detail if a["threshold"] == "90d")
            lines = [
                f"🔴 *BLACKSITE ATO Alert Digest — {date.today().isoformat()}*\n",
                f"*{len(alert_detail)} systems need ATO attention:*",
            ]
            if expired_ct:  lines.append(f"🔴 Expired: {expired_ct}")
            if warn30_ct:   lines.append(f"🟠 ≤30 days: {warn30_ct}")
            if warn60_ct:   lines.append(f"🟡 ≤60 days: {warn60_ct}")
            if notice_ct:   lines.append(f"📋 ≤90 days: {notice_ct}")
            lines.append(f"\nReview: https://blacksite.borisov.network/systems")
            _telegram_send("\n".join(lines))

    return JSONResponse({"alerts_sent": alerts_sent, "detail": alert_detail})


@app.get("/api/alerts/poam-overdue")
async def api_poam_overdue_alerts(request: Request):
    """
    Scheduled: check overdue POA&M items and send tiered Telegram alerts.
    Escalation: 1d overdue → ISSO tier (operational), 7d → ISSM, 14d → AO (Tier 1).
    Dedupe: one alert per poam_id per escalation tier per day.
    Admin-only. Called daily by bsv-ato-alerts.timer.
    """
    user = request.headers.get("Remote-User", "")
    if not user or not _is_admin(request):
        raise HTTPException(status_code=403)

    today = date.today()
    today_str = today.isoformat()
    alerts_sent = 0

    async with SessionLocal() as session:
        overdue_items = (await session.execute(
            select(PoamItem)
            .where(PoamItem.status.in_(["open", "in_progress"]))
            .where(PoamItem.scheduled_completion.isnot(None))
            .where(PoamItem.scheduled_completion < today_str)
            .order_by(PoamItem.scheduled_completion.asc())
            .limit(50)
        )).scalars().all()

        for item in overdue_items:
            try:
                due = date.fromisoformat(item.scheduled_completion)
            except (ValueError, TypeError):
                continue
            days_overdue = (today - due).days
            if days_overdue < 1:
                continue

            # Determine escalation tier
            if days_overdue >= 14:
                tier_key = "tier1_ao"
                tier_label = "🔴 AO Tier 1 Escalation"
            elif days_overdue >= 7:
                tier_key = "tier2_issm"
                tier_label = "🟠 ISSM Tier 2 Escalation"
            else:
                tier_key = "tier3_isso"
                tier_label = "⚠️ ISSO Tier 3 Operational"

            item_id = item.poam_id or item.id[:8]
            dedupe_key = f"poam_overdue:{item.id}:{tier_key}:{today_str}"
            existing = await session.get(SystemSettings, dedupe_key)
            if existing:
                continue

            msg = (
                f"{tier_label}\n\n"
                f"*POA\\&M:* `{item_id}`\n"
                f"*Weakness:* {(item.weakness_name or 'Unknown')[:80]}\n"
                f"*Due:* {item.scheduled_completion} ({days_overdue}d overdue)\n"
                f"*Severity:* {item.severity or 'Unknown'}\n"
                f"*System:* {item.system_id or 'N/A'}\n"
                f"Review: https://blacksite.borisov.network/poam/{item.id}"
            )
            _telegram_send(msg)
            alerts_sent += 1
            session.add(SystemSettings(key=dedupe_key, value=today_str))

        await session.commit()

    return JSONResponse({"alerts_sent": alerts_sent, "overdue_count": len(overdue_items)})


@app.post("/api/alerts/audit-check")
async def api_audit_check(request: Request):
    """
    Scheduled: scan recent audit log for high-risk events and alert.
    Events: role_change, failed_login_spike (>5 in 5min), poam_waiver, risk_acceptance.
    Dedupe: alert_key = event_type + user + day, stored in SystemSettings.
    Admin-only. Called daily by bsv-ato-alerts.timer.
    """
    user = request.headers.get("Remote-User", "")
    if not user or not _is_admin(request):
        raise HTTPException(status_code=403)

    today_str = date.today().isoformat()
    window_start = datetime.now(timezone.utc) - timedelta(hours=25)
    alerts_sent = 0

    async with SessionLocal() as session:
        # Fetch recent audit events
        recent_logs = (await session.execute(
            select(AuditLog)
            .where(AuditLog.timestamp >= window_start)
            .order_by(AuditLog.timestamp.desc())
            .limit(500)
        )).scalars().all()

        # ── Role changes ───────────────────────────────────────────────────
        role_changes = [e for e in recent_logs
                        if e.action == "UPDATE" and e.resource_type == "role_shell"
                        and "set_shell" in (e.details or "")]
        for ev in role_changes:
            dedupe_key = f"audit_role_change:{ev.remote_user}:{today_str}"
            if await session.get(SystemSettings, dedupe_key):
                continue
            msg = (
                f"🔑 *BLACKSITE Audit Alert — Role Change*\n\n"
                f"*User:* `{ev.remote_user}`\n"
                f"*Time:* {ev.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ') if ev.timestamp else 'unknown'}\n"
                f"*Detail:* {(ev.details or '')[:200]}\n"
                f"Severity: HIGH"
            )
            _telegram_send(msg)
            alerts_sent += 1
            session.add(SystemSettings(key=dedupe_key, value=today_str))

        # ── POA&M waiver / risk acceptance events ─────────────────────────
        waiver_events = [e for e in recent_logs
                         if e.action == "UPDATE" and e.resource_type in ("poam", "risk")
                         and any(kw in (e.details or "")
                                 for kw in ("accepted_risk", "deferred_waiver", "waiver"))]
        for ev in waiver_events[:10]:
            dedupe_key = f"audit_waiver:{ev.resource_id}:{today_str}"
            if await session.get(SystemSettings, dedupe_key):
                continue
            msg = (
                f"⚠️ *BLACKSITE Audit Alert — Risk Waiver/Acceptance*\n\n"
                f"*User:* `{ev.remote_user}`\n"
                f"*Resource:* {ev.resource_type} `{ev.resource_id}`\n"
                f"*Time:* {ev.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ') if ev.timestamp else 'unknown'}\n"
                f"*Detail:* {(ev.details or '')[:200]}\n"
                f"Severity: HIGH — AO review may be required."
            )
            _telegram_send(msg)
            alerts_sent += 1
            session.add(SystemSettings(key=dedupe_key, value=today_str))

        # ── Failed login spike detection ──────────────────────────────────
        # Count VIEW events on login-adjacent routes to detect spikes
        from collections import Counter as _Counter
        auth_fails = [e for e in recent_logs
                      if e.action in ("AUTH_FAIL", "FORBIDDEN")
                      or (e.action == "VIEW" and e.resource_type == "auth_fail")]
        user_fail_counts = _Counter(e.remote_user for e in auth_fails)
        for fail_user, count in user_fail_counts.items():
            if count < 5:
                continue
            dedupe_key = f"audit_loginfail:{fail_user}:{today_str}"
            if await session.get(SystemSettings, dedupe_key):
                continue
            msg = (
                f"🚨 *BLACKSITE Audit Alert — Failed Login Spike*\n\n"
                f"*User/IP:* `{fail_user}`\n"
                f"*Count:* {count} failures in last 25h\n"
                f"Severity: CRITICAL — Possible credential stuffing."
            )
            _telegram_send(msg)
            alerts_sent += 1
            session.add(SystemSettings(key=dedupe_key, value=today_str))

        await session.commit()

    return JSONResponse({"alerts_sent": alerts_sent})


@app.get("/api/feeds")
async def api_feeds(request: Request):
    """Return merged advisory feed items as JSON. Sources loaded from DB. Filtered by user's systems."""
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
        # Load enabled feed sources from DB
        src_rows = (await session.execute(
            select(FeedSource).where(FeedSource.enabled == True).order_by(FeedSource.sort_order)
        )).scalars().all()
        sources = [{"key": s.key, "name": s.name, "url": s.url,
                    "enabled": True, "error_count": s.error_count or 0}
                   for s in src_rows]

    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(
        None, lambda: get_feed_items(sources=sources or None,
                                     systems=systems_list, max_items=25, min_score=0)
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
async def rmf_overview(request: Request, show_all: bool = False):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_ids = await _user_system_ids(request, session)
        all_systems = []
        if sys_ids:
            rows = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            all_systems = list(rows.scalars().all())

        total_systems = len(all_systems)
        _RMF_DEFAULT_CAP = 20
        systems = all_systems if show_all else all_systems[:_RMF_DEFAULT_CAP]
        capped_sys_ids = [s.id for s in systems]

        # Fetch RMF records only for displayed systems
        rmf_rows = {}
        if capped_sys_ids:
            rr = await session.execute(
                select(RmfRecord).where(RmfRecord.system_id.in_(capped_sys_ids))
            )
            for rec in rr.scalars().all():
                rmf_rows.setdefault(rec.system_id, {})[rec.step] = rec

        ctx = await _full_ctx(request, session,
                              systems=systems,
                              total_systems=total_systems,
                              show_all=show_all,
                              rmf_default_cap=_RMF_DEFAULT_CAP,
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

        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso", "sca", "system_owner"])

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
    if not _effective_is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    valid_roles = {
        "employee", "auditor", "bcdr", "system_owner", "isso", "issm", "sca", "ao",
        "ciso", "pen_tester", "data_owner", "pmo", "incident_responder",
    }
    if role not in valid_roles:
        role = "employee"

    async with SessionLocal() as session:
        # B2: Check for active re-use reservation
        _add_now = datetime.now(timezone.utc)
        _resv_q = await session.execute(
            select(RemovedUserReservation)
            .where(RemovedUserReservation.username == username)
            .where(RemovedUserReservation.hold_until > _add_now)
            .where(RemovedUserReservation.override_granted == False)
        )
        _resv = _resv_q.scalar_one_or_none()
        if _resv:
            raise HTTPException(status_code=400,
                detail=f"Username '{username}' is reserved until "
                       f"{_resv.hold_until.strftime('%Y-%m-%d')} after removal. "
                       f"Request an override at /admin/users/reservations.")
        if email:
            _resv_email_q = await session.execute(
                select(RemovedUserReservation)
                .where(RemovedUserReservation.email == email)
                .where(RemovedUserReservation.hold_until > _add_now)
                .where(RemovedUserReservation.override_granted == False)
            )
            _resv_email = _resv_email_q.scalar_one_or_none()
            if _resv_email:
                raise HTTPException(status_code=400,
                    detail=f"Email '{email}' is reserved until "
                           f"{_resv_email.hold_until.strftime('%Y-%m-%d')} after removal. "
                           f"Request an override at /admin/users/reservations.")
        _dname = display_name.strip() or username.replace(".", " ").replace("_", " ").title()
        existing = await session.get(UserProfile, username)
        if existing:
            existing.display_name = _dname or existing.display_name
            existing.email        = email or existing.email
            existing.role         = role
        else:
            profile = UserProfile(
                remote_user  = username,
                display_name = _dname or None,
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


_EXEC_PROVISION_ROLES = frozenset({"ao", "ciso"})  # non-admin exec roles that can provision


async def _can_provision(request: Request, session) -> bool:
    """True if the user may onboard new employees (provision).

    Allowed: effective admin (not in shell) OR native exec role (ao/ciso).
    Prevents shelled admins and non-exec roles from creating accounts.
    """
    if _effective_is_admin(request):
        return True
    role = await _get_user_role(request, session)
    return role in _EXEC_PROVISION_ROLES


@app.get("/admin/users/provision", response_class=HTMLResponse)
async def admin_provision_page(request: Request, provisioned: str = ""):
    """Executive function: onboard a new employee with a generated credential."""
    async with SessionLocal() as s:
        if not await _can_provision(request, s):
            raise HTTPException(status_code=403, detail="Provisioning requires Executive tier (AO, CISO) or Admin access.")
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
    Restricted to executive tier (AO, CISO) and admin.
    """
    async with SessionLocal() as _ps:
        if not await _can_provision(request, _ps):
            raise HTTPException(status_code=403, detail="Provisioning requires Executive tier or Admin.")

    admin      = request.headers.get("Remote-User", "")
    username   = username.strip().lower()
    role       = role if role in {"employee","auditor","bcdr","system_owner","isso","issm","sca","ao"} else "employee"
    email      = email.strip()
    dname      = display_name.strip() or username.replace(".", " ").replace("_", " ").title()

    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    # B2: Check for active re-use reservation
    async with SessionLocal() as _prov_resv_s:
        _prov_now = datetime.now(timezone.utc)
        _prov_resv_q = await _prov_resv_s.execute(
            select(RemovedUserReservation)
            .where(RemovedUserReservation.username == username)
            .where(RemovedUserReservation.hold_until > _prov_now)
            .where(RemovedUserReservation.override_granted == False)
        )
        _prov_resv = _prov_resv_q.scalar_one_or_none()
        if _prov_resv:
            raise HTTPException(status_code=400,
                detail=f"Username '{username}' is reserved until "
                       f"{_prov_resv.hold_until.strftime('%Y-%m-%d')} after removal. "
                       f"Request an override at /admin/users/reservations.")
        if email:
            _prov_resv_eq = await _prov_resv_s.execute(
                select(RemovedUserReservation)
                .where(RemovedUserReservation.email == email)
                .where(RemovedUserReservation.hold_until > _prov_now)
                .where(RemovedUserReservation.override_granted == False)
            )
            _prov_resv_e = _prov_resv_eq.scalar_one_or_none()
            if _prov_resv_e:
                raise HTTPException(status_code=400,
                    detail=f"Email '{email}' is reserved until "
                           f"{_prov_resv_e.hold_until.strftime('%Y-%m-%d')} after removal. "
                           f"Request an override at /admin/users/reservations.")

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
    if not _effective_is_admin(request):
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
    if not _effective_is_admin(request):
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
    if not _effective_is_admin(request):
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
    if not _effective_is_admin(request):
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
    if not _effective_is_admin(request):
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
    if not _effective_is_admin(request):
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
        # B2: Create 1-year re-use reservation for this username/email
        _now_utc = datetime.now(timezone.utc)
        reservation = RemovedUserReservation(
            username   = username,
            email      = profile.email or None,
            removed_at = _now_utc,
            hold_until = _now_utc + timedelta(days=365),
            removed_by = admin,
        )
        session.add(reservation)
        await _log_audit(session, admin, "CREATE", "removed_user_reservation", username,
                         {"action": "user_reservation_created",
                          "hold_until": (_now_utc + timedelta(days=365)).isoformat()})
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


@app.get("/admin/users/reservations", response_class=HTMLResponse)
async def admin_user_reservations(request: Request):
    """List active username/email re-use reservations (1-year hold after removal)."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as session:
        now_utc = datetime.now(timezone.utc)
        rows = await session.execute(
            select(RemovedUserReservation)
            .where(RemovedUserReservation.hold_until > now_utc)
            .order_by(RemovedUserReservation.hold_until.asc())
        )
        reservations = list(rows.scalars().all())
        role = await _get_user_role(request, session)
        ctx = await _full_ctx(request, session, reservations=reservations, now=now_utc)
    return templates.TemplateResponse("admin_user_reservations.html", ctx)


@app.post("/admin/users/reservations/{resv_id}/override")
async def admin_reservation_override(request: Request, resv_id: int):
    """Grant override on a reservation — allows re-use before hold expires. Principal tier only."""
    if not _effective_is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "")
    async with SessionLocal() as session:
        profile = await session.get(UserProfile, admin)
        if not profile or profile.company_tier != "principal":
            raise HTTPException(status_code=403,
                detail="Only principal-tier users may grant reservation overrides.")
        resv = await session.get(RemovedUserReservation, resv_id)
        if not resv:
            raise HTTPException(status_code=404, detail="Reservation not found.")
        form = await request.form()
        resv.override_granted = True
        resv.override_by      = admin
        resv.override_at      = datetime.now(timezone.utc)
        resv.override_reason  = str(form.get("reason", "")).strip() or "Override granted"
        await _log_audit(session, admin, "UPDATE", "removed_user_reservation", str(resv_id),
                         {"action": "override_granted", "username": resv.username,
                          "reason": resv.override_reason})
        await session.commit()
    return RedirectResponse(url="/admin/users/reservations", status_code=303)


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
        # issm and isso are also permitted to view SIEM logs
        async with SessionLocal() as _s:
            _siem_role = await _get_user_role(request, _s)
        if _siem_role not in {"issm", "isso"}:
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


# ── Admin SSP Analyzer ────────────────────────────────────────────────────────

_SSP_UPLOAD_DIR = Path("data/ssp_reviews")
_SSP_ALLOWED    = {".docx", ".pdf", ".txt", ".xlsx", ".csv"}


# ── System Management Settings ────────────────────────────────────────────────

@app.get("/admin/system-settings", response_class=HTMLResponse)
async def admin_system_settings(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    settings = {
        "chat_enabled":        await _get_setting("chat_enabled", "true"),
        "chat_visible_count":  await _get_setting("chat_visible_count", "5"),
        "chat_show_away_msg":  await _get_setting("chat_show_away_msg", "true"),
        "session_timeout_min": await _get_setting("session_timeout_min", "15"),
    }
    # M2: Pass config-managed admin users (moved from user management page)
    _admin_users_cfg = list(CONFIG.get("app", {}).get("admin_users", ["dan"]))
    return templates.TemplateResponse("admin_system_settings.html", {
        "request": request,
        "settings": settings,
        "admin_users_cfg": _admin_users_cfg,
        **_tpl_ctx(request),
    })


@app.post("/admin/system-settings")
async def admin_system_settings_save(
    request: Request,
    chat_enabled:        str = Form("true"),
    chat_visible_count:  str = Form("5"),
    chat_show_away_msg:  str = Form("true"),
    session_timeout_min: str = Form("15"),
):
    if not _effective_is_admin(request):
        raise HTTPException(status_code=403)
    admin = request.headers.get("Remote-User", "dan")
    for key, val in [
        ("chat_enabled",       chat_enabled),
        ("chat_visible_count", chat_visible_count),
        ("chat_show_away_msg", chat_show_away_msg),
        ("session_timeout_min", session_timeout_min),
    ]:
        await _set_setting(key, val, updated_by=admin)
    # Update in-memory session timeout if changed
    global _SESSION_TIMEOUT
    try:
        _SESSION_TIMEOUT = timedelta(minutes=int(session_timeout_min))
    except (ValueError, TypeError):
        pass
    return RedirectResponse("/admin/system-settings?saved=1", status_code=303)


# ── Admin: Feed Source Management (LIST4-ITEM3) ────────────────────────────────

@app.get("/admin/feeds", response_class=HTMLResponse)
async def admin_feeds_index(request: Request):
    """Admin feed source management — list all sources with health status."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as session:
        rows = (await session.execute(
            select(FeedSource).order_by(FeedSource.sort_order, FeedSource.key)
        )).scalars().all()
    return templates.TemplateResponse("admin_feeds.html", {
        "request": request,
        "sources": rows,
        "allowlist": FEED_ALLOWLIST,
        **_tpl_ctx(request),
    })


@app.post("/admin/feeds/{key}/toggle")
async def admin_feeds_toggle(request: Request, key: str):
    """Toggle a feed source enabled/disabled."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    if key not in FEED_ALLOWLIST:
        raise HTTPException(status_code=404, detail="Feed key not in allowlist")
    async with SessionLocal() as session:
        src = await session.get(FeedSource, key)
        if not src:
            raise HTTPException(status_code=404, detail="Feed source not found")
        src.enabled = not src.enabled
        src.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return JSONResponse({"key": key, "enabled": src.enabled})


@app.post("/admin/feeds/{key}/test")
async def admin_feeds_test(request: Request, key: str):
    """Test-fetch a single feed source. Does not update cache or DB health."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    if key not in FEED_ALLOWLIST:
        raise HTTPException(status_code=404, detail="Feed key not in allowlist")
    url = FEED_ALLOWLIST[key]["url"]
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: fetch_one_for_test(url))
    # Update health stats in DB
    async with SessionLocal() as session:
        src = await session.get(FeedSource, key)
        if src:
            now_utc = datetime.now(timezone.utc)
            if result["ok"]:
                src.last_fetched = now_utc
                src.item_count   = result.get("item_count", 0)
                src.last_error   = None
                src.error_count  = 0
            else:
                src.last_error  = result.get("error", "unknown error")[:300]
                src.error_count = (src.error_count or 0) + 1
            src.updated_at = now_utc
            await session.commit()
    return JSONResponse(result)


@app.post("/admin/feeds/reorder")
async def admin_feeds_reorder(request: Request):
    """Update sort_order for all feed sources. Body: {key: new_order}."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    body = await request.json()
    async with SessionLocal() as session:
        for key, order in body.items():
            if key in FEED_ALLOWLIST:
                src = await session.get(FeedSource, key)
                if src:
                    src.sort_order = int(order)
        await session.commit()
    return JSONResponse({"ok": True})


@app.get("/admin/ssp", response_class=HTMLResponse)
async def admin_ssp_index(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as s:
        rows = (await s.execute(
            select(SspReview).order_by(SspReview.uploaded_at.desc()).limit(30)
        )).scalars().all()
    return templates.TemplateResponse("admin_ssp_upload.html", {
        "request": request,
        "reviews": rows,
        **_tpl_ctx(request),
    })


@app.post("/admin/ssp/upload")
async def admin_ssp_upload(
    request:    Request,
    background: BackgroundTasks,
    file:       UploadFile = File(...),
):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    user = request.headers.get("Remote-User", "dan")
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in _SSP_ALLOWED:
        raise HTTPException(400, f"File type '{suffix}' not allowed. Use: {', '.join(_SSP_ALLOWED)}")

    _SSP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    review_id  = str(uuid.uuid4())
    safe_name  = f"{review_id}{suffix}"
    dest       = _SSP_UPLOAD_DIR / safe_name

    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1024 * 256):
            await f.write(chunk)

    review = SspReview(
        id          = review_id,
        filename    = file.filename or "upload",
        file_path   = str(dest),
        uploaded_by = user,
        status      = "processing",
    )
    async with SessionLocal() as s:
        s.add(review)
        await s.commit()

    background.add_task(_run_ssp_analysis, review_id, dest)
    return RedirectResponse(f"/admin/ssp/review/{review_id}", status_code=303)


async def _run_ssp_analysis(review_id: str, path: Path):
    """Background task: run analyze_ssp and persist results."""
    try:
        result = analyze_ssp(path)
        counts = result["counts"]
        async with SessionLocal() as s:
            rev = await s.get(SspReview, review_id)
            if rev:
                rev.status        = "complete"
                rev.system_name   = result.get("system_name")
                rev.impact_level  = result.get("impact_level")
                rev.overall_score = result.get("overall_score", 0.0)
                rev.total_controls = result.get("total", 0)
                rev.adequate      = counts.get("ADEQUATE", 0)
                rev.medium_gap    = counts.get("MEDIUM_GAP", 0)
                rev.high_gap      = counts.get("HIGH_GAP", 0)
                rev.critical_gap  = counts.get("CRITICAL_GAP", 0)
                rev.not_found     = counts.get("NOT_FOUND", 0)
                rev.analysis_json = json.dumps(result["findings"])
                await s.commit()
    except Exception as exc:
        log.exception("SSP analysis failed for %s: %s", review_id, exc)
        async with SessionLocal() as s:
            rev = await s.get(SspReview, review_id)
            if rev:
                rev.status        = "error"
                rev.error_message = str(exc)
                await s.commit()


@app.get("/admin/ssp/review/{review_id}", response_class=HTMLResponse)
async def admin_ssp_review(request: Request, review_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    async with SessionLocal() as s:
        rev = await s.get(SspReview, review_id)
    if not rev:
        raise HTTPException(404)
    findings = json.loads(rev.analysis_json) if rev.analysis_json else []
    return templates.TemplateResponse("admin_ssp_review.html", {
        "request":  request,
        "rev":      rev,
        "findings": findings,
        **_tpl_ctx(request),
    })


@app.get("/admin/ssp/review/{review_id}/pdf")
async def admin_ssp_pdf(request: Request, review_id: str):
    """Generate and stream a PDF report for an SSP review."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as s:
        rev = await s.get(SspReview, review_id)
    if not rev or rev.status != "complete":
        raise HTTPException(404)

    findings = json.loads(rev.analysis_json) if rev.analysis_json else []
    try:
        pdf_bytes = _generate_ssp_pdf(rev, findings)
    except Exception as _pdf_exc:
        req_id = str(uuid.uuid4())[:8]
        _analysis_size = len(rev.analysis_json or "")
        log.exception(
            "SSP PDF [%s] FAILED | review_id=%s | user=%s | system=%r | "
            "findings=%d | analysis_json_bytes=%d | exc=%s",
            req_id, review_id, request.headers.get("Remote-User", ""),
            rev.system_name, len(findings), _analysis_size, _pdf_exc,
        )
        ctx = {
            **_tpl_ctx(request),
            "request":  request,
            "now":      datetime.now(timezone.utc),
            "req_id":   req_id,
            "error":    str(_pdf_exc),
        }
        return templates.TemplateResponse("error_pdf.html", ctx, status_code=500)

    safe_name = _re.sub(r'[^\w\-]', '_', rev.system_name or "SSP_Review")
    uploaded_ts = rev.uploaded_at or datetime.now(timezone.utc)
    filename  = f"{safe_name}_SSP_Review_{uploaded_ts.strftime('%Y%m%d')}.pdf"

    return Response(
        content     = pdf_bytes,
        media_type  = "application/pdf",
        headers     = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _generate_ssp_pdf(rev: SspReview, findings: list) -> bytes:
    """Build PDF report using reportlab."""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    # Guard None findings
    if findings is None:
        findings = []

    buf    = BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=letter,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle("bsv_title", parent=styles["Title"],
                                 fontSize=22, textColor=colors.HexColor("#00ffcc"),
                                 spaceAfter=6)
    h1 = ParagraphStyle("bsv_h1", parent=styles["Heading1"],
                         fontSize=14, textColor=colors.HexColor("#00ffcc"),
                         spaceBefore=16, spaceAfter=4)
    h2 = ParagraphStyle("bsv_h2", parent=styles["Heading2"],
                         fontSize=11, textColor=colors.HexColor("#ffd700"),
                         spaceBefore=12, spaceAfter=3)
    body = ParagraphStyle("bsv_body", parent=styles["Normal"],
                          fontSize=9, leading=14, spaceAfter=4)
    muted = ParagraphStyle("bsv_muted", parent=body,
                           textColor=colors.HexColor("#888888"), fontSize=8)
    fix_style = ParagraphStyle("bsv_fix", parent=body,
                               leftIndent=12, textColor=colors.HexColor("#333333"),
                               borderPad=4)

    _GRADE_COLOR = {
        "CRITICAL_GAP": colors.HexColor("#f44336"),
        "HIGH_GAP":     colors.HexColor("#ff7043"),
        "MEDIUM_GAP":   colors.HexColor("#ffb300"),
        "ADEQUATE":     colors.HexColor("#00c853"),
        "NA":           colors.HexColor("#888888"),
        "NOT_FOUND":    colors.HexColor("#9e9e9e"),
    }

    story = []

    # ── Cover page ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph("BLACKSITE", ParagraphStyle("brand", parent=styles["Normal"],
                            fontSize=10, textColor=colors.HexColor("#888888"),
                            spaceAfter=2)))
    story.append(Paragraph("SSP Quality Review Report", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#00ffcc")))
    story.append(Spacer(1, 0.2*inch))

    meta_data = [
        ["System", rev.system_name or "Unknown"],
        ["Impact Level", rev.impact_level or "Unknown"],
        ["File", str(rev.filename or "")],
        ["Reviewed", (rev.uploaded_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")],
        ["Reviewer", rev.uploaded_by],
        ["Overall Score", f"{rev.overall_score or 0:.1f} / 100"],
    ]
    meta_table = Table(meta_data, colWidths=[1.5*inch, 5*inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#00ffcc")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
        ("GRID",      (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3*inch))

    # ── Executive Summary ────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.1*inch))

    score_color = (colors.HexColor("#f44336") if rev.overall_score < 40
                   else colors.HexColor("#ffb300") if rev.overall_score < 65
                   else colors.HexColor("#00c853"))

    summary_text = (
        f"This SSP review analyzed <b>{rev.total_controls or 0}</b> control references extracted from "
        f"<i>{str(rev.filename or '')}</i>. The document scored <b>{rev.overall_score or 0:.1f}/100</b> overall, "
        f"reflecting the depth, specificity, and completeness of implementation statements. "
        f"A score below 60 indicates significant gaps that may delay ATO or result in findings during assessment."
    )
    story.append(Paragraph(summary_text, body))
    story.append(Spacer(1, 0.15*inch))

    # Counts table
    counts = rev.critical_gap + rev.high_gap + rev.medium_gap + rev.adequate
    summary_rows = [
        ["Finding Grade", "Count", "Description"],
        ["Critical Gap", str(rev.critical_gap), "Control missing or narrative essentially absent"],
        ["High Gap", str(rev.high_gap), "Major implementation detail missing"],
        ["Medium Gap", str(rev.medium_gap), "Partial — insufficient specificity or missing elements"],
        ["Adequate", str(rev.adequate), "Meets minimum documentation standards"],
        ["Not Applicable", str(findings.count({'grade': 'NA'})), "Marked N/A in the SSP"],
    ]
    # Fix NA count
    na_count = sum(1 for f in findings if f.get("grade") == "NA")
    summary_rows[5][1] = str(na_count)

    sum_table = Table(summary_rows, colWidths=[1.5*inch, 0.8*inch, 4.2*inch])
    sum_table.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#2a2a3a")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#fff5f5"), colors.white]),
        ("TEXTCOLOR",    (0, 1), (0, 1),   colors.HexColor("#f44336")),
        ("TEXTCOLOR",    (0, 2), (0, 2),   colors.HexColor("#ff7043")),
        ("TEXTCOLOR",    (0, 3), (0, 3),   colors.HexColor("#ffb300")),
        ("TEXTCOLOR",    (0, 4), (0, 4),   colors.HexColor("#00c853")),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(sum_table)
    story.append(PageBreak())

    # ── Detailed Findings ────────────────────────────────────────────────────
    story.append(Paragraph("Detailed Findings & Remediation Guidance", h1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "Each finding below lists identified gaps and specific remediation actions. "
        "Controls graded ADEQUATE are omitted unless they contain advisory notes.",
        muted,
    ))
    story.append(Spacer(1, 0.2*inch))

    actionable = [f for f in findings if f.get("grade") not in ("ADEQUATE", "NA")]

    for f in actionable:
        grade_color = _GRADE_COLOR.get(f.get("grade", ""), colors.grey)
        ctrl_id     = str(f.get("control_id") or "??")
        fam_name    = str(f.get("family_name") or "")
        label       = str(f.get("label") or "")
        score_val   = f.get("score") or 0
        issues_list = f.get("issues") or []
        fix_text    = str(f.get("fix") or "")
        risk_text   = str(f.get("risk") or "")

        header_data = [[
            Paragraph(f"<b>{ctrl_id}</b> — {fam_name}", ParagraphStyle(
                "ctrl_hdr", parent=body, fontSize=10, textColor=colors.white, spaceAfter=0)),
            Paragraph(f"<b>{label}</b>  ({score_val}/100)", ParagraphStyle(
                "ctrl_grade", parent=body, fontSize=9, textColor=grade_color,
                alignment=1, spaceAfter=0)),
        ]]
        hdr_tbl = Table(header_data, colWidths=[4.5*inch, 2*inch])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",(0, 0), (-1, -1), 10),
            ("TOPPADDING",  (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
            ("LINEBELOW",   (0, 0), (-1, -1), 1.5, grade_color),
        ]))

        block = [hdr_tbl]

        if issues_list:
            block.append(Spacer(1, 0.06*inch))
            block.append(Paragraph("Issues Identified:", ParagraphStyle(
                "issues_hdr", parent=body, fontSize=8.5, textColor=colors.HexColor("#ffb300"),
                spaceAfter=2)))
            for issue in issues_list:
                block.append(Paragraph(f"• {issue}", body))

        if fix_text:
            block.append(Spacer(1, 0.06*inch))
            block.append(Paragraph("Remediation:", ParagraphStyle(
                "rem_hdr", parent=body, fontSize=8.5, textColor=colors.HexColor("#00c853"),
                spaceAfter=2)))
            block.append(Paragraph(fix_text, fix_style))

        if risk_text:
            block.append(Paragraph(
                f"<i>Risk if unresolved: {risk_text}</i>",
                ParagraphStyle("risk_txt", parent=muted, fontSize=7.5, spaceBefore=3),
            ))

        block.append(Spacer(1, 0.18*inch))
        story.append(KeepTogether(block))

    # ── Adequate controls appendix ────────────────────────────────────────────
    adequate = [f for f in findings if f.get("grade") == "ADEQUATE"]
    if adequate:
        story.append(PageBreak())
        story.append(Paragraph("Appendix — Controls Meeting Documentation Standards", h1))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 0.1*inch))
        adeq_rows = [["Control", "Family", "Score", "Status"]]
        for f in adequate:
            adeq_rows.append([
                f.get("control_id", ""),
                f.get("family_name", ""),
                str(f.get("score", 0)),
                f.get("status", ""),
            ])
        adeq_tbl = Table(adeq_rows, colWidths=[1.2*inch, 2.2*inch, 0.8*inch, 2.3*inch])
        adeq_tbl.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#e8f5e9")),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(adeq_tbl)

    doc.build(story)
    return buf.getvalue()


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


# ── Daily work-product bundle ──────────────────────────────────────────────────

_BUNDLE_SCAN_DIRS: list = [
    # (directory, description, speed-up idea)
    ("results",              "Assessment result files",        "Automate via nightly cron + /api/bundle"),
    ("data/ssp_reviews",     "SSP Analyzer review reports",    "Schedule SSP uploads for batch processing"),
    ("data/uploads/poam_evidence", "POA&M evidence attachments", "Use bulk evidence upload script"),
    ("data/ato_generated",   "ATO-generated documents",        "Pre-generate docs at ATO lifecycle stages"),
    ("data/rbac-runs",       "RBAC regression run reports",    "Gate CI pipeline on rbac_run exit code"),
]

@app.post("/admin/bundle/daily")
async def admin_bundle_daily(request: Request):
    """Build a zip of today's work products and email it to the requesting user."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin only")

    import zipfile, hashlib

    today = date.today()
    date_label = today.strftime("%m-%d-%Y")
    zip_name   = today.strftime("%m%d%y") + "_workproducts.zip"
    bundle_dir = Path("data/bundles")
    bundle_dir.mkdir(parents=True, exist_ok=True)
    zip_path   = bundle_dir / zip_name

    collected: list[dict] = []   # {name, rel_path, abs_path, size, dir_label, speedup}

    for rel_dir, dir_label, speedup in _BUNDLE_SCAN_DIRS:
        p = Path(rel_dir)
        if not p.exists():
            continue
        for f in p.iterdir():
            if not f.is_file():
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime.date() != today:
                continue
            collected.append({
                "name":      f.name,
                "rel_path":  str(f),
                "abs_path":  f,
                "size":      f.stat().st_size,
                "mtime":     mtime.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "dir_label": dir_label,
                "speedup":   speedup,
            })

    # Build index content
    index_lines = [
        f"# BLACKSITE Daily Work Bundle",
        f"**Date:** {date_label}",
        f"**Generated by:** {user}",
        f"**Generated at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total items:** {len(collected)}",
        "",
        "---",
        "",
        "## Items",
        "",
    ]
    for i, item in enumerate(collected, 1):
        index_lines += [
            f"### {i}. `{item['name']}`",
            f"- **Type:** {item['dir_label']}",
            f"- **Path:** `{item['rel_path']}`",
            f"- **Size:** {item['size']:,} bytes",
            f"- **Timestamp:** {item['mtime']}",
            f"- **Speed-up:** {item['speedup']}",
            "",
        ]
    index_content = "\n".join(index_lines)

    # Write zip
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("INDEX.md", index_content)
        for item in collected:
            zf.write(item["abs_path"], arcname=item["rel_path"])

    # Compute file hash
    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    # Get requester email
    async with SessionLocal() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.remote_user == user)
        )).scalar_one_or_none()
        recipient_email = (profile.email if profile and profile.email
                           else CONFIG.get("email", {}).get("to_address", ""))
        recipient_name  = (profile.display_name if profile and profile.display_name else user)

        sent = await asyncio.get_event_loop().run_in_executor(
            None, send_bundle, CONFIG, zip_path,
            recipient_email, recipient_name, date_label, len(collected)
        )

        await _log_audit(session, user, "EXPORT", "bundle", zip_name, {
            "date": date_label,
            "items": len(collected),
            "sha256": sha256[:16],
            "recipient": recipient_email,
            "sent": sent,
        })
        await session.commit()

    return JSONResponse({
        "ok":      True,
        "zip":     zip_name,
        "items":   len(collected),
        "sha256":  sha256[:16],
        "sent":    sent,
        "email":   recipient_email,
    })


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
async def ato_dashboard(request: Request, show_all: bool = False):
    """ATO Package dashboard — matrix of all systems x all doc types."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        sys_ids = await _user_system_ids(request, session)
        all_systems = []
        if sys_ids:
            rows = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            all_systems = list(rows.scalars().all())

        total_systems = len(all_systems)
        _ATO_DEFAULT_CAP = 20
        systems = all_systems if show_all else all_systems[:_ATO_DEFAULT_CAP]

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
            total     = len(_ATO_DOC_KEYS)
            finalized = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "finalized")
            approved  = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "approved")
            in_review = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "in_review")
            draft     = sum(1 for k in _ATO_DOC_KEYS if ato_map.get((sys.id, k)) and ato_map[(sys.id, k)].status == "draft")
            missing   = total - finalized - approved - in_review - draft
            pct       = round((finalized / total) * 100) if total else 0
            sys_summary[sys.id] = {
                "total": total, "finalized": finalized, "approved": approved,
                "in_review": in_review, "draft": draft, "missing": missing, "pct": pct,
            }

        # Overall totals for the dashboard summary strip
        ato_overall = {
            "total":     len(systems) * len(_ATO_DOC_KEYS),
            "finalized": sum(s["finalized"] for s in sys_summary.values()),
            "approved":  sum(s["approved"]  for s in sys_summary.values()),
            "in_review": sum(s["in_review"] for s in sys_summary.values()),
            "draft":     sum(s["draft"]     for s in sys_summary.values()),
            "missing":   sum(s["missing"]   for s in sys_summary.values()),
        }
        ato_overall["pct"] = (
            round((ato_overall["finalized"] / ato_overall["total"]) * 100)
            if ato_overall["total"] else 0
        )

        ctx = await _full_ctx(request, session,
                              systems=systems,
                              total_systems=total_systems,
                              show_all=show_all,
                              ato_default_cap=_ATO_DEFAULT_CAP,
                              ato_map=ato_map,
                              ato_doc_types=ATO_DOC_TYPES,
                              ato_doc_keys=_ATO_DOC_KEYS,
                              generatable_docs=_GENERATABLE_DOCS,
                              sys_summary=sys_summary,
                              ato_overall=ato_overall,
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

        # In-app pipeline notifications
        try:
            sys_obj = await session.get(System, system_id)
            sys_name = sys_obj.name if sys_obj else system_id
            doc_name = ATO_DOC_TYPES[doc_type]["name"]

            if action == "submit":
                # Notify reviewers (admins + AO) that a doc is ready for review
                ao_res = await session.execute(
                    select(UserProfile.remote_user)
                    .where(UserProfile.role.in_(["admin", "ao", "issm"]))
                    .where(UserProfile.status == "active")
                )
                for (ru,) in ao_res.all():
                    if ru != user:
                        await _notify_user(session, ru, "doc_needs_review",
                                           f"Review needed: {doc_name} — {sys_name}",
                                           body=f"Submitted by {user}",
                                           action_url=f"/ato/{system_id}/{doc_type}")
            elif action == "approve":
                # Notify the document owner/creator
                if doc.created_by and doc.created_by != user:
                    await _notify_user(session, doc.created_by, "doc_approved",
                                       f"Approved: {doc_name} — {sys_name}",
                                       action_url=f"/ato/{system_id}/{doc_type}")
            elif action == "reject":
                if doc.created_by and doc.created_by != user:
                    await _notify_user(session, doc.created_by, "doc_rejected",
                                       f"Returned to draft: {doc_name} — {sys_name}",
                                       body=comment or "Rejected by reviewer",
                                       action_url=f"/ato/{system_id}/{doc_type}")
            elif action == "finalize":
                # Notify whole system team that a doc is finalized
                await _notify_system_team(
                    session, system_id, "doc_finalized",
                    f"Finalized: {doc_name} — {sys_name}",
                    action_url=f"/ato/{system_id}/{doc_type}",
                    exclude_user=user,
                )
                # Check if ALL docs for this system are now finalized → notify AO
                all_docs_res = await session.execute(
                    select(AtoDocument).where(AtoDocument.system_id == system_id)
                )
                all_docs = {d.doc_type: d for d in all_docs_res.scalars().all()}
                core_types = [k for k, v in ATO_DOC_TYPES.items()
                              if v.get("category") == "core" and not v.get("guidance_only")]
                all_core_done = all(
                    all_docs.get(k) and all_docs[k].status == "finalized"
                    for k in core_types
                )
                if all_core_done:
                    ao_res2 = await session.execute(
                        select(UserProfile.remote_user)
                        .where(UserProfile.role.in_(["admin", "ao"]))
                        .where(UserProfile.status == "active")
                    )
                    for (ru,) in ao_res2.all():
                        if ru != user:
                            await _notify_user(session, ru, "package_ready_for_ao",
                                               f"ATO Package Ready for Decision — {sys_name}",
                                               body="All core documents finalized. Ready for AO authorization.",
                                               action_url=f"/ao/decisions")

            log.info("ATO workflow: %s %s [%s] by %s (%s)",
                     action, doc_name, sys_name, user, ato_role)
        except Exception as _e:
            log.warning("ATO pipeline notification failed: %s", _e)

    return RedirectResponse(url=f"/ato/{system_id}/{doc_type}", status_code=303)


@app.post("/ato/{system_id}/{doc_type}/generate")
async def ato_generate(request: Request, system_id: str, doc_type: str):
    """Generate an ATO document from existing system data and save as draft."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if doc_type not in _GENERATABLE_DOCS:
        raise HTTPException(status_code=400, detail=f"{doc_type} cannot be auto-generated")
    if doc_type not in ATO_DOC_TYPES:
        raise HTTPException(status_code=404, detail="Unknown document type")

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_obj = await session.get(System, system_id)
        if not sys_obj:
            raise HTTPException(status_code=404)

        # ── Gather source data ──
        generated: dict = {"aegis_doc_type": doc_type, "system": sys_obj.name,
                           "generated_at": datetime.now(timezone.utc).isoformat(),
                           "generated_by": user}

        if doc_type == "FIPS199":
            generated["categorization"] = {
                "system_name":       sys_obj.name,
                "abbreviation":      sys_obj.abbreviation,
                "system_type":       sys_obj.system_type,
                "environment":       sys_obj.environment,
                "confidentiality":   sys_obj.confidentiality_impact,
                "integrity":         sys_obj.integrity_impact,
                "availability":      sys_obj.availability_impact,
                "overall_impact":    sys_obj.overall_impact,
                "has_pii":           sys_obj.has_pii,
                "has_phi":           sys_obj.has_phi,
                "has_ephi":          sys_obj.has_ephi,
                "has_financial_data":sys_obj.has_financial_data,
                "has_cui":           sys_obj.has_cui,
                "is_public_facing":  sys_obj.is_public_facing,
                "connects_to_federal":sys_obj.connects_to_federal,
                "status":            sys_obj.categorization_status,
                "approved_by":       sys_obj.categorization_approved_by,
            }

        elif doc_type in ("SSP", "SSP_APP_M"):
            ctrl_rows = await session.execute(
                select(SystemControl).where(SystemControl.system_id == system_id)
                .order_by(SystemControl.control_family, SystemControl.control_id)
            )
            controls = ctrl_rows.scalars().all()
            if doc_type == "SSP":
                generated["system_info"] = {
                    "name": sys_obj.name, "description": sys_obj.description,
                    "purpose": sys_obj.purpose, "boundary": sys_obj.boundary,
                    "environment": sys_obj.environment, "owner": sys_obj.owner_name,
                }
                generated["controls"] = [
                    {"control_id": c.control_id, "title": c.control_title,
                     "status": c.status, "implementation_type": c.implementation_type,
                     "narrative": c.narrative, "responsible_role": c.responsible_role}
                    for c in controls
                ]
            else:  # SSP_APP_M — integrated inventory
                inv_rows = await session.execute(
                    select(InventoryItem).where(InventoryItem.system_id == system_id)
                    .order_by(InventoryItem.item_type, InventoryItem.name)
                )
                generated["inventory"] = [
                    {"type": i.item_type, "name": i.name, "vendor": i.vendor,
                     "version": i.version, "quantity": i.quantity,
                     "ip_address": i.ip_address, "location": i.location}
                    for i in inv_rows.scalars().all()
                ]

        elif doc_type == "POAM":
            poam_rows = await session.execute(
                select(PoamItem).where(PoamItem.system_id == system_id)
                .order_by(PoamItem.severity, PoamItem.created_at)
            )
            generated["poam_items"] = [
                {"poam_id": p.poam_id, "weakness": p.weakness_name,
                 "severity": p.severity, "status": p.status,
                 "control_id": p.control_id, "scheduled_completion": p.scheduled_completion,
                 "responsible_party": p.responsible_party}
                for p in poam_rows.scalars().all()
            ]

        elif doc_type in ("HW_INV", "SW_INV"):
            item_type = "hardware" if doc_type == "HW_INV" else "software"
            inv_rows = await session.execute(
                select(InventoryItem)
                .where(InventoryItem.system_id == system_id)
                .where(InventoryItem.item_type == item_type)
                .order_by(InventoryItem.name)
            )
            generated["inventory"] = [
                {"name": i.name, "vendor": i.vendor, "version": i.version,
                 "quantity": i.quantity, "ip_address": i.ip_address,
                 "serial_number": i.serial_number, "location": i.location}
                for i in inv_rows.scalars().all()
            ]

        elif doc_type == "CONMON_MONTHLY":
            open_poam_res = await session.execute(
                select(func.count(PoamItem.id))
                .where(PoamItem.system_id == system_id)
                .where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
            )
            ctrl_impl_res = await session.execute(
                select(func.count(SystemControl.id))
                .where(SystemControl.system_id == system_id)
                .where(SystemControl.status == "implemented")
            )
            ctrl_total_res = await session.execute(
                select(func.count(SystemControl.id)).where(SystemControl.system_id == system_id)
            )
            generated["summary"] = {
                "report_month": date.today().strftime("%B %Y"),
                "open_poams":   open_poam_res.scalar() or 0,
                "controls_implemented": ctrl_impl_res.scalar() or 0,
                "controls_total": ctrl_total_res.scalar() or 0,
                "auth_status": sys_obj.auth_status,
                "auth_expiry": sys_obj.auth_expiry,
            }

        elif doc_type == "ADD":
            generated["authorization_decision"] = {
                "system_name":    sys_obj.name,
                "system_id":      sys_obj.id,
                "decision":       sys_obj.ato_decision or "pending",
                "auth_status":    sys_obj.auth_status,
                "auth_date":      sys_obj.auth_date,
                "auth_expiry":    sys_obj.auth_expiry,
                "duration":       sys_obj.ato_duration,
                "signed_by":      sys_obj.ato_signed_by,
                "signed_at":      sys_obj.ato_signed_at.isoformat() if sys_obj.ato_signed_at else None,
                "notes":          sys_obj.ato_notes,
            }

        # ── Store generated file ──
        gen_dir = Path("data/ato_generated") / system_id
        gen_dir.mkdir(parents=True, exist_ok=True)
        gen_file = gen_dir / f"{doc_type}.json"
        gen_content = json.dumps(generated, indent=2, default=str)
        gen_file.write_text(gen_content)

        # ── Upsert AtoDocument ──
        doc = (await session.execute(
            select(AtoDocument)
            .where(AtoDocument.system_id == system_id)
            .where(AtoDocument.doc_type == doc_type)
        )).scalar_one_or_none()

        doc_title = ATO_DOC_TYPES[doc_type]["name"]
        if doc:
            doc.content     = gen_content
            doc.file_path   = str(gen_file)
            doc.file_size   = len(gen_content.encode())
            doc.source_type = "generated"
            doc.status      = "draft" if doc.status not in ("in_review", "approved", "finalized") else doc.status
            doc.updated_at  = datetime.now(timezone.utc)
        else:
            doc = AtoDocument(
                system_id   = system_id,
                doc_type    = doc_type,
                title       = doc_title,
                content     = gen_content,
                file_path   = str(gen_file),
                file_size   = len(gen_content.encode()),
                source_type = "generated",
                created_by  = user,
            )
            session.add(doc)

        await _log_audit(session, user, "GENERATE", "ato_document", f"{system_id}/{doc_type}",
                         {"doc_type": doc_type, "file": str(gen_file)})
        await session.commit()

    return RedirectResponse(url=f"/ato/{system_id}/{doc_type}", status_code=303)


@app.post("/ato/{system_id}/{doc_type}/upload")
async def ato_upload(request: Request, system_id: str, doc_type: str,
                     file: UploadFile = File(...)):
    """Upload an external file for an ATO document (signed letters, 3PAO reports, etc.)."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if doc_type not in ATO_DOC_TYPES:
        raise HTTPException(status_code=404, detail="Unknown document type")

    _ALLOWED_ATO_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".json", ".xml"}
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in _ALLOWED_ATO_EXT:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Use: PDF, DOCX, XLSX, PPTX, TXT, JSON, XML")

    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(status_code=403)

        sys_obj = await session.get(System, system_id)
        if not sys_obj:
            raise HTTPException(status_code=404)

        upload_dir = Path("data/ato_uploads") / system_id / doc_type
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{doc_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}{ext}"
        dest = upload_dir / safe_name
        contents = await file.read()
        dest.write_bytes(contents)

        doc = (await session.execute(
            select(AtoDocument)
            .where(AtoDocument.system_id == system_id)
            .where(AtoDocument.doc_type == doc_type)
        )).scalar_one_or_none()

        doc_title = ATO_DOC_TYPES[doc_type]["name"]
        if doc:
            doc.file_path   = str(dest)
            doc.file_size   = len(contents)
            doc.source_type = "uploaded"
            doc.updated_at  = datetime.now(timezone.utc)
        else:
            doc = AtoDocument(
                system_id   = system_id,
                doc_type    = doc_type,
                title       = doc_title,
                file_path   = str(dest),
                file_size   = len(contents),
                source_type = "uploaded",
                created_by  = user,
            )
            session.add(doc)

        await _log_audit(session, user, "UPLOAD", "ato_document", f"{system_id}/{doc_type}",
                         {"filename": file.filename, "size": len(contents)})

        # Notify system team that a document was uploaded
        await _notify_system_team(
            session, system_id, "doc_uploaded",
            f"Document uploaded: {doc_title}",
            body=f"{user} uploaded {file.filename} for {sys_obj.name}",
            action_url=f"/ato/{system_id}/{doc_type}",
            exclude_user=user,
        )
        await session.commit()

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


# ── CISO Dashboard ─────────────────────────────────────────────────────────────

@app.get("/ciso/dashboard", response_class=HTMLResponse)
async def ciso_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso"])

        today_str = date.today().isoformat()

        # All active systems
        systems = list((await session.execute(
            select(System)
            .where(System.deleted_at.is_(None))
            .order_by(System.name)
        )).scalars().all())

        # Auth status breakdown
        auth_counts: dict[str, int] = {"authorized": 0, "in_progress": 0,
                                        "expired": 0, "not_authorized": 0}
        for s in systems:
            k = s.auth_status or "not_authorized"
            auth_counts[k] = auth_counts.get(k, 0) + 1

        # FIPS 199 classification breakdown
        impact_counts: dict[str, int] = {"High": 0, "Moderate": 0, "Low": 0}
        for s in systems:
            lvl = s.overall_impact or "Low"
            impact_counts[lvl] = impact_counts.get(lvl, 0) + 1

        # POAM totals
        total_open_poams = (await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open", "in_progress"]))
        )).scalar() or 0

        total_overdue_poams = (await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(["open", "in_progress"]))
            .where(PoamItem.scheduled_completion.isnot(None))
            .where(PoamItem.scheduled_completion < today_str)
        )).scalar() or 0

        # Open risks
        total_open_risks = (await session.execute(
            select(func.count(Risk.id))
            .where(Risk.status == "open")
        )).scalar() or 0

        # Per-system summary rows (limited to essentials)
        sys_summaries = []
        for s in systems:
            open_p = (await session.execute(
                select(func.count(PoamItem.id))
                .where(PoamItem.system_id == s.id)
                .where(PoamItem.status.in_(["open", "in_progress"]))
            )).scalar() or 0
            overdue_p = (await session.execute(
                select(func.count(PoamItem.id))
                .where(PoamItem.system_id == s.id)
                .where(PoamItem.status.in_(["open", "in_progress"]))
                .where(PoamItem.scheduled_completion.isnot(None))
                .where(PoamItem.scheduled_completion < today_str)
            )).scalar() or 0
            sys_summaries.append({
                "id":            s.id,
                "name":          s.name,
                "abbreviation":  s.abbreviation or "",
                "auth_status":   s.auth_status or "not_authorized",
                "auth_expiry":   s.auth_expiry or "",
                "overall_impact": s.overall_impact or "Low",
                "open_poams":    open_p,
                "overdue_poams": overdue_p,
            })

        ctx = await _full_ctx(request, session,
                              systems=sys_summaries,
                              auth_counts=auth_counts,
                              impact_counts=impact_counts,
                              total_open_poams=total_open_poams,
                              total_overdue_poams=total_overdue_poams,
                              total_open_risks=total_open_risks,
                              system_count=len(systems))

    return templates.TemplateResponse("ciso_dashboard.html", ctx)


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
        if not _is_admin(request) and role not in ("sca", "isso"):
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

        # POA&Ms with pending AO risk acceptance approval
        pending_risk_q = await session.execute(
            select(PoamItem)
            .where(PoamItem.approval_stage == "pending_ao")
            .order_by(PoamItem.updated_at.desc())
        )
        pending_risk_acceptances = pending_risk_q.scalars().all()

        ctx = await _full_ctx(request, session,
                              pending_systems=pending_systems,
                              decided_systems=decided_systems,
                              expiring_systems=expiring_systems,
                              poam_counts=poam_counts,
                              risk_counts=risk_counts,
                              pending_risk_acceptances=pending_risk_acceptances)

    return templates.TemplateResponse("ao_decisions.html", ctx)


@app.post("/ao/decisions/{system_id}")
async def ao_record_decision(request: Request, system_id: str):
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not _is_admin(request) and role != "ao":
            raise HTTPException(status_code=403)

        form = await request.form()
        decision    = form.get("decision", "")
        duration    = form.get("duration", "")       # 1_year|3_year|5_year|ongoing|custom
        custom_days = form.get("custom_days", "")
        notes       = form.get("notes", "").strip()

        if decision not in ("approved", "denied"):
            raise HTTPException(status_code=400, detail="decision must be 'approved' or 'denied'")

        system = await session.get(System, system_id)
        if not system:
            raise HTTPException(status_code=404, detail="System not found")

        ao = request.headers.get("Remote-User", "")
        now_utc = datetime.now(timezone.utc)

        system.ato_decision  = decision
        system.ato_notes     = notes or None
        system.ato_signed_by = ao
        system.ato_signed_at = now_utc
        system.ato_duration  = duration or None
        system.auth_date     = date.today().isoformat()

        if decision == "approved":
            system.auth_status = "authorized"
            # Calculate expiry
            if duration == "ongoing":
                system.auth_expiry = None
            elif duration == "custom" and custom_days.isdigit():
                system.auth_expiry = (date.today() + timedelta(days=int(custom_days))).isoformat()
            elif duration == "1_year":
                system.auth_expiry = (date.today() + timedelta(days=365)).isoformat()
            elif duration == "3_year":
                system.auth_expiry = (date.today() + timedelta(days=1095)).isoformat()
            elif duration == "5_year":
                system.auth_expiry = (date.today() + timedelta(days=1825)).isoformat()

            # Auto-generate ADD (Authorization Decision Document)
            add_content = json.dumps({
                "aegis_doc_type":       "ADD",
                "title":                "Authorization Decision Document",
                "system_name":          system.name,
                "system_id":            system.id,
                "decision":             "approved",
                "authorizing_official": ao,
                "auth_date":            system.auth_date,
                "auth_expiry":          system.auth_expiry,
                "duration":             duration,
                "rationale":            notes or "",
                "generated_at":         now_utc.isoformat(),
            }, indent=2, default=str)

            add_dir = Path("data/ato_generated") / system_id
            add_dir.mkdir(parents=True, exist_ok=True)
            add_file = add_dir / "ADD.json"
            add_file.write_text(add_content)

            add_doc = (await session.execute(
                select(AtoDocument)
                .where(AtoDocument.system_id == system_id)
                .where(AtoDocument.doc_type == "ADD")
            )).scalar_one_or_none()
            if add_doc:
                add_doc.content     = add_content
                add_doc.file_path   = str(add_file)
                add_doc.file_size   = len(add_content.encode())
                add_doc.source_type = "generated"
                add_doc.status      = "finalized"
                add_doc.updated_at  = now_utc
            else:
                add_doc = AtoDocument(
                    system_id   = system_id,
                    doc_type    = "ADD",
                    title       = "Authorization Decision Document",
                    content     = add_content,
                    file_path   = str(add_file),
                    file_size   = len(add_content.encode()),
                    source_type = "generated",
                    status      = "finalized",
                    created_by  = ao,
                )
                session.add(add_doc)
        else:
            system.auth_status = "not_authorized"

        await _log_audit(session, ao, "ATO_DECISION", "system", system_id,
                         {"decision": decision, "duration": duration, "notes": notes,
                          "auth_expiry": system.auth_expiry})

        # Notify all users assigned to this system
        expiry_str = f" · Expires {system.auth_expiry}" if system.auth_expiry else (" · Ongoing" if duration == "ongoing" else "")
        notif_title = (
            f"✓ ATO Approved — {system.name}{expiry_str}"
            if decision == "approved"
            else f"✕ ATO Denied — {system.name}"
        )
        notif_body = notes or f"AO decision recorded by {ao}"
        await _notify_system_team(
            session, system_id, "ato_decision",
            notif_title, body=notif_body,
            action_url=f"/systems/{system_id}",
            exclude_user=ao,
        )
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

_OBS_WRITE_ROLES = {"issm", "isso", "sca", "auditor", "system_owner", "admin",
                    "ao", "ciso", "pen_tester"}  # ao/ciso/pen_tester can file observations
_OBS_READ_ROLES  = _OBS_WRITE_ROLES | {"pmo", "bcdr_coordinator"}  # read-only viewers


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

        _inv_role = await _get_user_role(request, session)
        _require_role(_inv_role, ["admin", "ao", "ciso", "issm", "isso"])

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

        _conn_role = await _get_user_role(request, session)
        _require_role(_conn_role, ["admin", "ao", "ciso", "issm", "isso"])

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

        _art_role = await _get_user_role(request, session)
        _require_role(_art_role, ["admin", "ao", "ciso", "issm", "isso"])

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


# ── Phase 16: Admin Chat ────────────────────────────────────────────────────────

@app.websocket("/ws/admin-chat")
async def ws_admin_chat(websocket: WebSocket):
    user = websocket.headers.get("Remote-User", "")
    if not _is_admin_user(user):
        await websocket.close(code=4003)
        return
    if not await _chat_enabled():
        await websocket.close(code=4004)
        return

    await websocket.accept()
    _ADMIN_CONNECTIONS[user] = websocket
    _ADMIN_PRESENCE[user] = {"status": "online", "away_msg": ""}

    # Send full presence snapshot to the new connection
    await websocket.send_json(_presence_payload())

    # Fetch unread counts for the joining user
    async with SessionLocal() as session:
        receipts = await session.execute(
            select(AdminChatReceipt).where(AdminChatReceipt.username == user)
        )
        receipt_map = {r.room: r.last_read_id for r in receipts.scalars().all()}

        rooms_result = await session.execute(
            select(AdminChatMessage.room).distinct()
        )
        all_rooms = [r[0] for r in rooms_result.fetchall()]

        unread: dict[str, int] = {}
        for room in all_rooms:
            if not (room == "@group" or user in room.split(":")):
                continue
            last_id = receipt_map.get(room, 0)
            count_result = await session.execute(
                select(func.count()).where(
                    AdminChatMessage.room == room,
                    AdminChatMessage.id > last_id,
                    AdminChatMessage.from_user != user,
                )
            )
            cnt = count_result.scalar() or 0
            if cnt:
                unread[room] = cnt

    await websocket.send_json({"type": "unread", "counts": unread})

    # Broadcast arrival to other admins
    await _chat_broadcast(_presence_payload(), exclude=user)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "message":
                room = data.get("room", "@group")
                body = str(data.get("body", "")).strip()
                if not body:
                    continue
                # Validate DM room: must contain user
                if room != "@group" and user not in room.split(":"):
                    continue

                async with SessionLocal() as session:
                    msg = AdminChatMessage(room=room, from_user=user, body=body)
                    session.add(msg)
                    await session.flush()
                    msg_id = msg.id
                    await session.commit()

                payload = {
                    "type":      "message",
                    "id":        msg_id,
                    "room":      room,
                    "from_user": user,
                    "body":      body,
                    "sent_at":   datetime.now(timezone.utc).isoformat(),
                }
                await _chat_broadcast(payload)

            elif msg_type == "status":
                status   = data.get("status", "online")
                away_msg = str(data.get("away_msg", ""))[:200]
                if status not in ("online", "away"):
                    status = "online"
                _ADMIN_PRESENCE[user] = {"status": status, "away_msg": away_msg}
                await _chat_broadcast(_presence_payload())

            elif msg_type == "typing":
                room = data.get("room", "@group")
                await _chat_broadcast(
                    {"type": "typing", "room": room, "from_user": user},
                    exclude=user,
                )

            elif msg_type == "read":
                room    = data.get("room", "@group")
                last_id = int(data.get("last_id", 0))
                async with SessionLocal() as session:
                    existing = await session.execute(
                        select(AdminChatReceipt).where(
                            AdminChatReceipt.room == room,
                            AdminChatReceipt.username == user,
                        )
                    )
                    receipt = existing.scalar_one_or_none()
                    if receipt:
                        receipt.last_read_id = max(receipt.last_read_id, last_id)
                    else:
                        session.add(AdminChatReceipt(
                            room=room, username=user, last_read_id=last_id
                        ))
                    await session.commit()

    except WebSocketDisconnect:
        pass
    finally:
        _ADMIN_CONNECTIONS.pop(user, None)
        _ADMIN_PRESENCE.pop(user, None)
        await _chat_broadcast(_presence_payload())


@app.get("/api/admin-chat/history/{room:path}")
async def api_chat_history(request: Request, room: str, before: int = 0):
    user = request.headers.get("Remote-User", "")
    if not _is_admin_user(user):
        raise HTTPException(status_code=403)
    if room != "@group" and user not in room.split(":"):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        q = select(AdminChatMessage).where(AdminChatMessage.room == room)
        if before:
            q = q.where(AdminChatMessage.id < before)
        q = q.order_by(AdminChatMessage.id.desc()).limit(50)
        result = await session.execute(q)
        msgs = result.scalars().all()

    return JSONResponse([
        {
            "id":        m.id,
            "room":      m.room,
            "from_user": m.from_user,
            "body":      m.body,
            "sent_at":   m.sent_at.isoformat() if m.sent_at else "",
        }
        for m in reversed(msgs)
    ])


@app.get("/api/admin-chat/unread")
async def api_chat_unread(request: Request):
    user = request.headers.get("Remote-User", "")
    if not _is_admin_user(user):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        receipts = await session.execute(
            select(AdminChatReceipt).where(AdminChatReceipt.username == user)
        )
        receipt_map = {r.room: r.last_read_id for r in receipts.scalars().all()}

        rooms_result = await session.execute(
            select(AdminChatMessage.room).distinct()
        )
        all_rooms = [r[0] for r in rooms_result.fetchall()]

        unread: dict[str, int] = {}
        for room in all_rooms:
            if not (room == "@group" or user in room.split(":")):
                continue
            last_id = receipt_map.get(room, 0)
            count_result = await session.execute(
                select(func.count()).where(
                    AdminChatMessage.room == room,
                    AdminChatMessage.id > last_id,
                    AdminChatMessage.from_user != user,
                )
            )
            cnt = count_result.scalar() or 0
            if cnt:
                unread[room] = cnt

    return JSONResponse(unread)


@app.post("/api/profile/theme")
async def api_set_theme(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    body  = await request.json()
    theme = body.get("theme", "midnight")
    if theme not in VALID_THEMES:
        raise HTTPException(status_code=400, detail="Unknown theme")
    resp = JSONResponse({"ok": True, "theme": theme})
    resp.set_cookie("bsv_theme", theme, max_age=365 * 24 * 3600,
                    httponly=False, samesite="lax", secure=True, path="/")  # BLKS022826-1009AC09
    return resp


@app.post("/api/admin-chat/status")
async def api_chat_status(request: Request):
    user = request.headers.get("Remote-User", "")
    if not _is_admin_user(user):
        raise HTTPException(status_code=403)
    body     = await request.json()
    status   = body.get("status", "online")
    away_msg = str(body.get("away_msg", ""))[:200]
    if status not in ("online", "away"):
        status = "online"
    _ADMIN_PRESENCE[user] = {"status": status, "away_msg": away_msg}
    await _chat_broadcast(_presence_payload())
    return JSONResponse({"ok": True})


@app.get("/api/admin-chat/users")
async def api_chat_users(request: Request):
    """Return all configured admin users with their live presence status."""
    user = request.headers.get("Remote-User", "")
    if not _is_admin_user(user):
        raise HTTPException(status_code=403)
    admin_usernames = list(CONFIG.get("app", {}).get("admin_users", ["dan"]))
    # Merge with DB display names
    async with SessionLocal() as session:
        profiles = (await session.execute(
            select(UserProfile).where(UserProfile.remote_user.in_(admin_usernames))
        )).scalars().all()
    name_map = {p.remote_user: p.display_name for p in profiles}
    result = []
    for u in admin_usernames:
        p = _ADMIN_PRESENCE.get(u, {"status": "offline", "away_msg": ""})
        result.append({
            "username":     u,
            "display_name": name_map.get(u) or u.replace(".", " ").title(),
            "status":       p.get("status", "offline"),
            "away_msg":     p.get("away_msg", ""),
        })
    return result


@app.get("/view-as/{username}", response_class=RedirectResponse)
async def view_as_user(request: Request, username: str):
    """Admin/manager enters a specific employee's workspace view."""
    if not _is_admin(request):
        raise HTTPException(status_code=403)
    # Validate that the target user exists
    async with SessionLocal() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.remote_user == username)
        )).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    ref = request.headers.get("Referer", "/dashboard")
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie("bsv_user_view", _sign_shell(username), httponly=True, samesite="lax", secure=True, max_age=3600)
    return resp


@app.get("/exit-view-as", response_class=RedirectResponse)
async def exit_view_as(request: Request):
    """Exit the user workspace view and return to previous page."""
    ref = request.headers.get("Referer", "/")
    resp = RedirectResponse(url=ref, status_code=303)
    resp.delete_cookie("bsv_user_view")
    return resp


@app.get("/chat/popup/{room:path}", response_class=HTMLResponse)
async def chat_popup(request: Request, room: str):
    """Standalone pop-out chat window for a specific room."""
    user = request.headers.get("Remote-User", "")
    if not _is_admin_user(user):
        raise HTTPException(status_code=403)
    if room == "@group":
        room_title = "# group"
    else:
        other = next((p for p in room.split(":") if p != user), room)
        room_title = "@ " + other
    ctx = {
        "request":    request,
        "room_json":  json.dumps(room),
        "me_json":    json.dumps(user),
        "room_title": room_title,
    }
    return templates.TemplateResponse("chat_popup.html", ctx)


# ── Role-Specific Dashboards (Phase 19) ────────────────────────────────────────

@app.get("/pen-tester/dashboard", response_class=HTMLResponse)
async def pen_tester_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not (_is_admin(request) or role in ("pen_tester", "ao", "ciso", "issm", "isso")):
            raise HTTPException(status_code=403)

        sys_ids = await _user_system_ids(request, session)
        assigned_systems = []
        if sys_ids:
            res = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            assigned_systems = res.scalars().all()

        obs_res = await session.execute(
            select(Observation)
            .where(Observation.created_by == user)
            .order_by(Observation.created_at.desc())
            .limit(20)
        )
        my_observations = obs_res.scalars().all()

        recent_assessments = []
        if sys_ids:
            asmt_res = await session.execute(
                select(Assessment)
                .where(Assessment.system_id.in_(sys_ids))
                .order_by(Assessment.uploaded_at.desc())
                .limit(10)
            )
            recent_assessments = asmt_res.scalars().all()

        ctx = await _full_ctx(request, session,
                              assigned_systems=assigned_systems,
                              my_observations=my_observations,
                              recent_assessments=recent_assessments)
    return templates.TemplateResponse("pen_tester_dashboard.html", ctx)


@app.get("/sca/dashboard", response_class=HTMLResponse)
async def sca_role_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not (_is_admin(request) or role in ("sca", "ao", "ciso", "issm", "isso")):
            raise HTTPException(status_code=403)

        sys_ids = await _user_system_ids(request, session)
        assigned_systems = []
        ctrl_stats: dict = {}
        if sys_ids:
            res = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            assigned_systems = list(res.scalars().all())
            for s in assigned_systems:
                total_q = await session.execute(
                    select(func.count(SystemControl.id))
                    .where(SystemControl.system_id == s.id)
                )
                total = total_q.scalar() or 0
                impl_q = await session.execute(
                    select(func.count(SystemControl.id))
                    .where(SystemControl.system_id == s.id)
                    .where(SystemControl.status.in_(
                        ["implemented", "in_progress", "planned"]))
                )
                tested = impl_q.scalar() or 0
                ctrl_stats[s.id] = {"total": total, "tested": tested}

        recent_assessments = []
        if sys_ids:
            asmt_res = await session.execute(
                select(Assessment)
                .where(Assessment.system_id.in_(sys_ids))
                .order_by(Assessment.uploaded_at.desc())
                .limit(10)
            )
            recent_assessments = asmt_res.scalars().all()

        open_poams = []
        if sys_ids:
            poam_res = await session.execute(
                select(PoamItem)
                .where(PoamItem.system_id.in_(sys_ids))
                .where(PoamItem.status.in_(["open", "in_progress", "ready_for_review"]))
                .order_by(PoamItem.severity, PoamItem.scheduled_completion)
                .limit(20)
            )
            open_poams = poam_res.scalars().all()

        ctx = await _full_ctx(request, session,
                              assigned_systems=assigned_systems,
                              ctrl_stats=ctrl_stats,
                              recent_assessments=recent_assessments,
                              open_poams=open_poams)
    return templates.TemplateResponse("sca_dashboard.html", ctx)


@app.get("/auditor/dashboard", response_class=HTMLResponse)
async def auditor_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not (_is_admin(request) or role in ("auditor", "ao", "ciso", "issm")):
            raise HTTPException(status_code=403)

        sys_ids = await _user_system_ids(request, session)

        asmt_q = select(Assessment).order_by(Assessment.uploaded_at.desc()).limit(20)
        if sys_ids:
            asmt_q = asmt_q.where(Assessment.system_id.in_(sys_ids))
        recent_assessments = (await session.execute(asmt_q)).scalars().all()

        doc_res = await session.execute(
            select(AtoDocument)
            .where(AtoDocument.status == "in_review")
            .order_by(AtoDocument.updated_at.desc())
            .limit(20)
        )
        docs_in_review = doc_res.scalars().all()

        accessible_systems = []
        gap_stats: dict = {}
        if sys_ids:
            sres = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            accessible_systems = list(sres.scalars().all())
            for s in accessible_systems:
                total_q = await session.execute(
                    select(func.count(SystemControl.id))
                    .where(SystemControl.system_id == s.id)
                )
                total = total_q.scalar() or 0
                impl_q = await session.execute(
                    select(func.count(SystemControl.id))
                    .where(SystemControl.system_id == s.id)
                    .where(SystemControl.status == "implemented")
                )
                impl = impl_q.scalar() or 0
                gap_stats[s.id] = {
                    "total": total, "implemented": impl,
                    "gap_pct": round((total - impl) / total * 100) if total else 0,
                }

        ctx = await _full_ctx(request, session,
                              recent_assessments=recent_assessments,
                              docs_in_review=docs_in_review,
                              accessible_systems=accessible_systems,
                              gap_stats=gap_stats)
    return templates.TemplateResponse("auditor_dashboard.html", ctx)


@app.get("/incident-responder/dashboard", response_class=HTMLResponse)
async def incident_responder_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not (_is_admin(request) or role in ("incident_responder", "ao", "ciso", "issm", "isso")):
            raise HTTPException(status_code=403)

        sys_ids = await _user_system_ids(request, session)

        risk_q = select(Risk).where(
            Risk.status == "open",
            Risk.risk_level.in_(["High", "Critical"])
        ).order_by(Risk.risk_score.desc()).limit(25)
        if sys_ids:
            risk_q = risk_q.where(Risk.system_id.in_(sys_ids))
        high_risks = (await session.execute(risk_q)).scalars().all()

        bcdr_res = await session.execute(
            select(BcdrEvent).order_by(BcdrEvent.triggered_at.desc()).limit(10)
        )
        recent_bcdr = bcdr_res.scalars().all()

        assigned_systems = []
        if sys_ids:
            res = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            assigned_systems = res.scalars().all()

        ctx = await _full_ctx(request, session,
                              high_risks=high_risks,
                              recent_bcdr=recent_bcdr,
                              assigned_systems=assigned_systems)
    return templates.TemplateResponse("incident_responder_dashboard.html", ctx)


@app.get("/data-owner/dashboard", response_class=HTMLResponse)
async def data_owner_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not (_is_admin(request) or role in ("data_owner", "ao", "ciso", "issm", "isso")):
            raise HTTPException(status_code=403)

        sys_ids = await _user_system_ids(request, session)
        owned_systems = []
        poam_counts: dict = {}
        if sys_ids:
            res = await session.execute(
                select(System).where(System.id.in_(sys_ids)).order_by(System.name)
            )
            owned_systems = list(res.scalars().all())
            pc_res = await session.execute(
                select(PoamItem.system_id, func.count(PoamItem.id))
                .where(PoamItem.system_id.in_(sys_ids))
                .where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
                .group_by(PoamItem.system_id)
            )
            poam_counts = dict(pc_res.all())

        ctx = await _full_ctx(request, session,
                              owned_systems=owned_systems,
                              poam_counts=poam_counts)
    return templates.TemplateResponse("data_owner_dashboard.html", ctx)


@app.get("/pmo/dashboard", response_class=HTMLResponse)
async def pmo_dashboard(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if not (_is_admin(request) or role in ("pmo", "ao", "ciso", "issm")):
            raise HTTPException(status_code=403)

        today_str = date.today().isoformat()

        sys_res = await session.execute(
            select(System).order_by(System.auth_expiry.asc().nullslast())
        )
        all_systems = list(sys_res.scalars().all())

        ato_breakdown: dict = {"authorized": 0, "in_progress": 0,
                               "expired": 0, "not_authorized": 0}
        for s in all_systems:
            st = s.auth_status or "not_authorized"
            if st in ato_breakdown:
                ato_breakdown[st] += 1
            else:
                ato_breakdown["not_authorized"] += 1

        overdue_q = await session.execute(
            select(func.count(PoamItem.id))
            .where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
            .where(PoamItem.scheduled_completion < today_str)
            .where(PoamItem.scheduled_completion.isnot(None))
        )
        overdue_count = overdue_q.scalar() or 0

        sev_breakdown: dict = {}
        for sev in ("Critical", "High", "Moderate", "Low"):
            ct = (await session.execute(
                select(func.count(PoamItem.id))
                .where(PoamItem.status.in_(list(POAM_ACTIVE_STATUSES)))
                .where(PoamItem.severity == sev)
            )).scalar() or 0
            sev_breakdown[sev] = ct

        ctx = await _full_ctx(request, session,
                              all_systems=all_systems,
                              ato_breakdown=ato_breakdown,
                              overdue_count=overdue_count,
                              sev_breakdown=sev_breakdown,
                              today=today_str)
    return templates.TemplateResponse("pmo_dashboard.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# DATA INGESTION ENGINE
# Exec-only (ao/ciso) + admin.  Supports JSON, CSV, XLSX for bulk user/system
# imports.  Two-step: upload → preview → confirm/commit.
# ─────────────────────────────────────────────────────────────────────────────

# Field maps: raw column → canonical DB field name
_USER_FIELD_MAP: dict[str, str] = {
    "username": "remote_user", "user": "remote_user", "login": "remote_user",
    "name": "display_name", "full_name": "display_name", "fullname": "display_name",
    "dept": "department", "division": "department",
    "tier": "company_tier", "platform_tier": "company_tier",
}
_USER_KNOWN: set[str] = {
    "remote_user", "display_name", "email", "department",
    "role", "company_tier", "status",
}

_SYS_FIELD_MAP: dict[str, str] = {
    "system_name": "name", "abbr": "abbreviation", "short_name": "abbreviation",
    "type": "system_type", "env": "environment",
    "owner": "owner_name", "desc": "description",
    "confidentiality": "confidentiality_impact", "c_impact": "confidentiality_impact",
    "integrity": "integrity_impact", "i_impact": "integrity_impact",
    "availability": "availability_impact", "a_impact": "availability_impact",
    "inv_number": "inventory_number", "inv_no": "inventory_number",
}
_SYS_KNOWN: set[str] = {
    "name", "abbreviation", "system_type", "environment",
    "owner_name", "owner_email", "description", "purpose",
    "confidentiality_impact", "integrity_impact", "availability_impact",
    "inventory_number", "has_pii", "has_phi", "has_ephi",
    "has_financial_data", "is_public_facing", "has_cui", "connects_to_federal",
}

_VALID_ROLES       = {"employee","isso","issm","sca","ao","aodr","ciso","system_owner",
                      "pmo","incident_responder","bcdr_coordinator","data_owner",
                      "pen_tester","auditor","admin"}
_VALID_TIERS       = {"principal","executive","manager","analyst"}
_VALID_STATUSES    = {"active","frozen"}
_VALID_IMPACTS     = {"Low","Moderate","High",""}
_VALID_SYS_TYPES   = {"major_application","general_support_system","minor_application",""}
_VALID_ENVS        = {"on_prem","cloud","hybrid","saas","paas","iaas",""}


def _parse_ingest_file(data: bytes, filename: str) -> list[dict]:
    """Parse uploaded bytes (JSON / XLSX / CSV) → list of raw row dicts."""
    import io, csv as _csv, json as _json, openpyxl
    ext = Path(filename).suffix.lower()
    if ext == ".json":
        rows = _json.loads(data.decode("utf-8", errors="replace"))
        if isinstance(rows, dict):
            rows = [rows]
        return [dict(r) for r in rows if isinstance(r, dict)]
    elif ext in (".xlsx", ".xlsm"):
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        row_iter = ws.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower().replace(" ", "_").replace("-", "_")
                   for h in next(row_iter, [])]
        result = []
        for row in row_iter:
            if any(v is not None and str(v).strip() for v in row):
                result.append({headers[i]: (str(v).strip() if v is not None else "")
                                for i, v in enumerate(row) if i < len(headers)})
        return result
    elif ext == ".csv":
        text = data.decode("utf-8-sig", errors="replace")
        reader = _csv.DictReader(io.StringIO(text))
        return [dict(r) for r in reader]
    else:
        raise ValueError(f"Unsupported file type '{ext}'. Use JSON, XLSX, or CSV.")


def _normalize_user_rows(raw_rows: list[dict]) -> tuple[list[dict], list[str], list[dict]]:
    """Normalize raw rows → (normalized_rows, unknown_fields, error_rows).
    unknown_fields: headers not recognized. error_rows: rows missing remote_user."""
    all_unknown: set[str] = set()
    normalized: list[dict] = []
    errors: list[dict] = []

    for raw in raw_rows:
        row: dict[str, str] = {}
        for k, v in raw.items():
            canon = k.strip().lower().replace(" ", "_").replace("-", "_")
            mapped = _USER_FIELD_MAP.get(canon, canon)
            if mapped in _USER_KNOWN:
                row[mapped] = str(v).strip() if v else ""
            else:
                all_unknown.add(canon)
        if not row.get("remote_user"):
            errors.append({"_raw": raw, "_reason": "Missing remote_user / username"})
            continue
        # Coerce enumerations to valid values (default if invalid)
        if row.get("role") and row["role"] not in _VALID_ROLES:
            row["_warn_role"] = row.pop("role")
        if row.get("company_tier") and row["company_tier"] not in _VALID_TIERS:
            row["_warn_tier"] = row.pop("company_tier")
        if row.get("status") and row["status"] not in _VALID_STATUSES:
            row["_warn_status"] = row.pop("status")
        normalized.append(row)

    return normalized, sorted(all_unknown), errors


def _normalize_sys_rows(raw_rows: list[dict]) -> tuple[list[dict], list[str], list[dict]]:
    """Normalize raw rows → (normalized_rows, unknown_fields, error_rows)."""
    all_unknown: set[str] = set()
    normalized: list[dict] = []
    errors: list[dict] = []

    for raw in raw_rows:
        row: dict[str, str] = {}
        for k, v in raw.items():
            canon = k.strip().lower().replace(" ", "_").replace("-", "_")
            mapped = _SYS_FIELD_MAP.get(canon, canon)
            if mapped in _SYS_KNOWN:
                row[mapped] = str(v).strip() if v else ""
            else:
                all_unknown.add(canon)
        if not row.get("name"):
            errors.append({"_raw": raw, "_reason": "Missing name / system_name"})
            continue
        # Coerce enum fields
        for fld, valid in [("confidentiality_impact", _VALID_IMPACTS),
                           ("integrity_impact", _VALID_IMPACTS),
                           ("availability_impact", _VALID_IMPACTS),
                           ("system_type", _VALID_SYS_TYPES),
                           ("environment", _VALID_ENVS)]:
            if row.get(fld) and row[fld] not in valid:
                row[f"_warn_{fld}"] = row.pop(fld)
        normalized.append(row)

    return normalized, sorted(all_unknown), errors


@app.get("/admin/ingest", response_class=HTMLResponse)
async def admin_ingest_home(request: Request, committed: str = ""):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        if not await _can_provision(request, session):
            raise HTTPException(status_code=403,
                detail="Data Ingestion requires Executive tier (AO/CISO) or Admin access.")
        # Recent jobs
        jobs_res = await session.execute(
            select(IngestJob).order_by(IngestJob.created_at.desc()).limit(20)
        )
        recent_jobs = list(jobs_res.scalars().all())
        ctx = await _full_ctx(request, session,
                              recent_jobs=recent_jobs,
                              committed=committed)
    return templates.TemplateResponse("admin_ingest.html", ctx)


@app.post("/admin/ingest/upload")
async def admin_ingest_upload(
    request: Request,
    ingest_type: str = Form(...),
    file: UploadFile = File(...),
):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        if not await _can_provision(request, session):
            raise HTTPException(status_code=403)

    if ingest_type not in ("users", "systems"):
        raise HTTPException(status_code=400, detail="ingest_type must be 'users' or 'systems'")

    _ALLOWED_INGEST_EXT = {".json", ".csv", ".xlsx", ".xlsm"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_INGEST_EXT:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported. Use JSON, CSV, or XLSX.")

    data = await file.read()
    try:
        raw_rows = _parse_ingest_file(data, file.filename or "upload")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Parse error: {exc}")

    if not raw_rows:
        raise HTTPException(status_code=400, detail="File contains no data rows.")

    if ingest_type == "users":
        normalized, unknown, errors = _normalize_user_rows(raw_rows)
    else:
        normalized, unknown, errors = _normalize_sys_rows(raw_rows)

    job = IngestJob(
        ingest_type=ingest_type,
        status="preview",
        filename=file.filename or "upload",
        row_count=len(normalized),
        error_count=len(errors),
        unknown_fields=json.dumps(unknown),
        data_json=json.dumps(normalized),
        created_by=user,
    )
    async with SessionLocal() as session:
        session.add(job)
        await session.commit()
        await session.refresh(job)

    return RedirectResponse(f"/admin/ingest/preview/{job.id}", status_code=303)


@app.get("/admin/ingest/preview/{job_id}", response_class=HTMLResponse)
async def admin_ingest_preview(request: Request, job_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        if not await _can_provision(request, session):
            raise HTTPException(status_code=403)
        job = await session.get(IngestJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Ingest job not found.")
        rows    = json.loads(job.data_json or "[]")
        unknown = json.loads(job.unknown_fields or "[]")
        ctx = await _full_ctx(request, session,
                              job=job,
                              rows=rows,
                              unknown_fields=unknown)
    return templates.TemplateResponse("admin_ingest_preview.html", ctx)


@app.post("/admin/ingest/commit/{job_id}")
async def admin_ingest_commit(request: Request, job_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        if not await _can_provision(request, session):
            raise HTTPException(status_code=403)
        job = await session.get(IngestJob, job_id)
        if not job:
            raise HTTPException(status_code=404)
        if job.status == "committed":
            return RedirectResponse(f"/admin/ingest?committed=already", status_code=303)

        rows = json.loads(job.data_json or "[]")
        created = 0
        updated = 0
        skipped = 0

        if job.ingest_type == "users":
            for row in rows:
                # Strip warning-only keys before DB write
                clean = {k: v for k, v in row.items() if not k.startswith("_")}
                ru = clean.get("remote_user", "").strip()
                if not ru:
                    skipped += 1
                    continue
                existing = await session.get(UserProfile, ru)
                if existing:
                    for k, v in clean.items():
                        if k != "remote_user" and v:
                            setattr(existing, k, v)
                    updated += 1
                else:
                    prof = UserProfile(
                        remote_user=ru,
                        display_name=clean.get("display_name", ""),
                        email=clean.get("email", ""),
                        department=clean.get("department", ""),
                        role=clean.get("role", "employee") or "employee",
                        company_tier=clean.get("company_tier", "analyst") or "analyst",
                        status=clean.get("status", "active") or "active",
                    )
                    session.add(prof)
                    created += 1

        elif job.ingest_type == "systems":
            for row in rows:
                clean = {k: v for k, v in row.items() if not k.startswith("_")}
                sname = clean.get("name", "").strip()
                if not sname:
                    skipped += 1
                    continue

                def _bool_val(v: str) -> bool:
                    return str(v).lower() in ("1", "true", "yes", "y")

                # Field aliases for common column name variations
                _fld = lambda *keys, default=None: next(
                    (clean[k] for k in keys if clean.get(k)), default
                )
                # Parse optional auth_date (ISO date string)
                _auth_date_raw = _fld("auth_date", "authorization_date", default="")
                try:
                    _auth_date = datetime.fromisoformat(_auth_date_raw).date() if _auth_date_raw else None
                except (ValueError, TypeError):
                    _auth_date = None

                sys_obj = System(
                    name=sname,
                    abbreviation=_fld("abbreviation", "abbr") or None,
                    system_type=_fld("system_type", "type") or None,
                    environment=_fld("environment", "env") or None,
                    owner_name=_fld("owner_name", "owner") or None,
                    owner_email=_fld("owner_email") or None,
                    description=_fld("description", "desc") or None,
                    purpose=_fld("purpose") or None,
                    confidentiality_impact=_fld("confidentiality_impact", "confidentiality") or None,
                    integrity_impact=_fld("integrity_impact", "integrity") or None,
                    availability_impact=_fld("availability_impact", "availability") or None,
                    inventory_number=_fld("inventory_number", "inv_number") or None,
                    has_pii=_bool_val(_fld("has_pii", default="")),
                    has_phi=_bool_val(_fld("has_phi", default="")),
                    has_ephi=_bool_val(_fld("has_ephi", default="")),
                    has_financial_data=_bool_val(_fld("has_financial_data", default="")),
                    is_public_facing=_bool_val(_fld("is_public_facing", default="")),
                    has_cui=_bool_val(_fld("has_cui", default="")),
                    connects_to_federal=_bool_val(_fld("connects_to_federal", default="")),
                    boundary=_fld("boundary", "boundary_description") or None,
                    overall_impact=_fld("overall_impact", "impact") or None,
                    auth_date=_auth_date,
                    categorization_status=_fld("categorization_status") or "draft",
                    categorization_note=_fld("categorization_note") or None,
                    is_eis=_bool_val(_fld("is_eis", default="")),
                    ato_notes=_fld("ato_notes") or None,
                    auth_status="not_authorized",   # always forced on import
                    created_by=user,
                )
                session.add(sys_obj)
                created += 1

        results = {"created": created, "updated": updated, "skipped": skipped}
        job.status = "committed"
        job.committed_by = user
        job.committed_at = datetime.now(timezone.utc)
        job.commit_results = json.dumps(results)
        await session.commit()

    summary = f"{created}c/{updated}u/{skipped}s"
    return RedirectResponse(f"/admin/ingest?committed={summary}", status_code=303)


@app.get("/admin/ingest/template/{ingest_type}")
async def admin_ingest_template_download(request: Request, ingest_type: str):
    """Download a blank CSV template for users or systems ingestion."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if ingest_type == "users":
        headers = ["remote_user", "display_name", "email", "department",
                   "role", "company_tier", "status"]
    elif ingest_type == "systems":
        headers = ["name", "abbreviation", "system_type", "environment",
                   "owner_name", "owner_email", "description", "purpose",
                   "confidentiality_impact", "integrity_impact", "availability_impact",
                   "inventory_number", "has_pii", "has_phi", "has_ephi",
                   "has_financial_data", "is_public_facing", "has_cui", "connects_to_federal"]
    else:
        raise HTTPException(status_code=400)

    import io, csv as _csv
    buf = io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow(headers)
    writer.writerow(["" for _ in headers])  # blank example row
    content = buf.getvalue().encode("utf-8")
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{ingest_type}_template.csv"'},
    )


# ════════════════════════════════════════════════════════════════════════════════
# PHASE 5 — STANDARDS FEEDS + AUTO-FAIL ENGINE
# ════════════════════════════════════════════════════════════════════════════════

# ── 5.9 NIST Publications Feed Ingest ─────────────────────────────────────────

_NIST_CSRC_FEED_URL = "https://csrc.nist.gov/CSRC/media/feeds/csrc/publications/atom.xml"
_NVD_CVE_API_URL    = "https://services.nvd.nist.gov/rest/json/cves/2.0/"

# Mapping: canonical publication IDs → series prefix for easy lookup
_KNOWN_NIST_PUBS: dict = {
    "SP800-53r5": "sp",
    "SP800-53Ar5": "sp",
    "SP800-37r2":  "sp",
    "SP800-137A":  "sp",
    "SP800-137":   "sp",
    "SP800-30r1":  "sp",
    "SP800-171r3": "sp",
    "SP800-218":   "sp",
    "FIPS199":     "fips",
    "FIPS200":     "fips",
}


def _parse_nist_atom_entry(entry_text: str) -> Optional[dict]:
    """Extract fields from a single Atom <entry> block."""
    import re
    def _tag(tag: str) -> str:
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", entry_text, re.DOTALL)
        return m.group(1).strip() if m else ""

    title = _tag("title")
    pub_date = _tag("published") or _tag("updated")
    link_m = re.search(r'<link[^>]+href=["\']([^"\']+)["\']', entry_text)
    url = link_m.group(1) if link_m else ""
    # Derive doc_id from title (best-effort normalization)
    doc_id_raw = re.sub(r'[^a-zA-Z0-9\-\.]', '', title.replace(" ", ""))[:40]
    if not doc_id_raw:
        return None
    return {
        "doc_id":   doc_id_raw,
        "title":    title,
        "pub_date": pub_date[:10] if pub_date else None,
        "url":      url,
        "status":   "draft" if "draft" in title.lower() else "active",
    }


@app.post("/admin/feeds/nist/ingest")
async def admin_nist_ingest(request: Request):
    """Fetch and store NIST CSRC publications Atom feed."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    import httpx, re

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(_NIST_CSRC_FEED_URL,
                                    headers={"User-Agent": "BLACKSITE-GRC/1.0"})
            resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NIST feed fetch failed: {exc}")

    xml = resp.text
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)

    now = datetime.now(timezone.utc)
    created_ct = 0
    updated_ct = 0

    async with SessionLocal() as session:
        for raw in entries:
            parsed = _parse_nist_atom_entry(raw)
            if not parsed:
                continue
            existing = (await session.execute(
                select(NistPublication).where(NistPublication.doc_id == parsed["doc_id"])
            )).scalar_one_or_none()

            if existing:
                existing.title        = parsed["title"]
                existing.pub_date     = parsed["pub_date"]
                existing.url          = parsed["url"]
                existing.status       = parsed["status"]
                existing.raw_json     = json.dumps(parsed)
                existing.last_fetched = now
                updated_ct += 1
            else:
                session.add(NistPublication(
                    doc_id       = parsed["doc_id"],
                    title        = parsed["title"],
                    pub_date     = parsed["pub_date"],
                    url          = parsed["url"],
                    status       = parsed["status"],
                    raw_json     = json.dumps(parsed),
                    last_fetched = now,
                ))
                created_ct += 1

        await _log_audit(session, user, "INGEST", "nist_feed", "publications",
                         {"entries": len(entries), "created": created_ct, "updated": updated_ct})
        await session.commit()

    return JSONResponse({
        "ok": True,
        "entries_parsed": len(entries),
        "created": created_ct,
        "updated": updated_ct,
    })


@app.post("/admin/feeds/nvd/ingest")
async def admin_nvd_ingest(request: Request, days: int = 30):
    """Fetch NVD CVEs from the last N days and store them locally.
    Uses the NVD CVE 2.0 REST API. Admin only."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    days = max(1, min(days, 120))  # Cap at 120 days to avoid huge payloads
    import httpx
    from datetime import timedelta

    end_dt   = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    pub_start = start_dt.strftime("%Y-%m-%dT%H:%M:%S.000")
    pub_end   = end_dt.strftime("%Y-%m-%dT%H:%M:%S.000")

    params = {
        "pubStartDate": pub_start,
        "pubEndDate":   pub_end,
        "resultsPerPage": 2000,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(_NVD_CVE_API_URL, params=params,
                                    headers={"User-Agent": "BLACKSITE-GRC/1.0"})
            resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NVD feed fetch failed: {exc}")

    data       = resp.json()
    vulns      = data.get("vulnerabilities", [])
    now        = datetime.now(timezone.utc)
    created_ct = 0
    updated_ct = 0

    async with SessionLocal() as session:
        for v in vulns:
            cve_obj = v.get("cve", {})
            cve_id  = cve_obj.get("id", "")
            if not cve_id:
                continue

            desc    = next((d["value"] for d in cve_obj.get("descriptions", [])
                            if d.get("lang") == "en"), "")
            pub_d   = (cve_obj.get("published", "") or "")[:10]
            mod_d   = (cve_obj.get("lastModified", "") or "")[:10]

            # CVSS — prefer v3.1, fall back to v3.0 then v2
            metrics = cve_obj.get("metrics", {})
            cvss_score = cvss_vector = cvss_sev = None
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                m_list = metrics.get(key, [])
                if m_list:
                    m = m_list[0].get("cvssData", {})
                    cvss_score  = str(m.get("baseScore", ""))
                    cvss_vector = m.get("vectorString", "")
                    cvss_sev    = m.get("baseSeverity", m_list[0].get("baseSeverity", ""))
                    break

            # CPE affected products
            cpes: list = []
            for cfg in cve_obj.get("configurations", []):
                for node in cfg.get("nodes", []):
                    cpes += [c.get("criteria", "") for c in node.get("cpeMatch", []) if c.get("criteria")]

            existing = (await session.execute(
                select(NvdCve).where(NvdCve.cve_id == cve_id)
            )).scalar_one_or_none()

            if existing:
                existing.description       = desc
                existing.cvss_score        = cvss_score
                existing.cvss_vector       = cvss_vector
                existing.cvss_severity     = cvss_sev
                existing.affected_products = json.dumps(cpes[:20])
                existing.published_date    = pub_d
                existing.modified_date     = mod_d
                existing.raw_json          = json.dumps(cve_obj, default=str)[:4000]
                existing.last_fetched      = now
                updated_ct += 1
            else:
                session.add(NvdCve(
                    cve_id            = cve_id,
                    description       = desc,
                    cvss_score        = cvss_score,
                    cvss_vector       = cvss_vector,
                    cvss_severity     = cvss_sev,
                    affected_products = json.dumps(cpes[:20]),
                    published_date    = pub_d,
                    modified_date     = mod_d,
                    raw_json          = json.dumps(cve_obj, default=str)[:4000],
                    last_fetched      = now,
                ))
                created_ct += 1

        await _log_audit(session, user, "INGEST", "nvd_feed", "cves",
                         {"days": days, "total": len(vulns), "created": created_ct, "updated": updated_ct})
        await session.commit()

    return JSONResponse({
        "ok": True,
        "days": days,
        "total_fetched": len(vulns),
        "created": created_ct,
        "updated": updated_ct,
    })


# ── 5.9 Control Parameter Store ──────────────────────────────────────────────

@app.get("/systems/{system_id}/parameters", response_class=HTMLResponse)
async def system_parameters(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        if not await _can_access_system(request, system_id, session):
            raise HTTPException(status_code=403)
        system = (await session.execute(
            select(System).where(System.id == system_id)
        )).scalar_one_or_none()
        if not system:
            raise HTTPException(status_code=404)

        params_rows = await session.execute(
            select(ControlParameter)
            .where(ControlParameter.system_id == system_id)
            .order_by(ControlParameter.control_id, ControlParameter.parameter_key)
        )
        params = params_rows.scalars().all()
        ctx = await _full_ctx(request, session,
            system=system,
            params=params,
        )

    return templates.TemplateResponse("system_parameters.html", ctx)


@app.post("/systems/{system_id}/parameters")
async def system_parameter_upsert(
    request: Request,
    system_id:       str,
    control_id:      str = Form(""),
    parameter_key:   str = Form(""),
    required_value:  str = Form(""),
    current_value:   str = Form(""),
    source:          str = Form("org_policy"),
    notes:           str = Form(""),
):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    if not control_id.strip() or not parameter_key.strip():
        raise HTTPException(status_code=400, detail="control_id and parameter_key are required")

    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        _require_role(role, ["admin", "ao", "ciso", "issm", "isso", "sca", "system_owner"])

        existing = (await session.execute(
            select(ControlParameter).where(
                ControlParameter.system_id     == system_id,
                ControlParameter.control_id    == control_id.strip().lower(),
                ControlParameter.parameter_key == parameter_key.strip(),
            )
        )).scalar_one_or_none()

        drift = bool(required_value.strip() and current_value.strip()
                     and required_value.strip() != current_value.strip())

        if existing:
            existing.required_value = required_value.strip()
            existing.current_value  = current_value.strip()
            existing.source         = source
            existing.notes          = notes.strip()
            existing.drift_detected = drift
            existing.last_checked   = datetime.now(timezone.utc)
        else:
            session.add(ControlParameter(
                system_id      = system_id,
                control_id     = control_id.strip().lower(),
                parameter_key  = parameter_key.strip(),
                required_value = required_value.strip(),
                current_value  = current_value.strip(),
                source         = source,
                notes          = notes.strip(),
                drift_detected = drift,
                last_checked   = datetime.now(timezone.utc),
                created_by     = user,
            ))

        await _log_audit(session, user, "UPSERT", "control_parameter", f"{system_id}/{control_id}",
                         {"parameter_key": parameter_key, "drift": drift})
        await session.commit()

    return RedirectResponse(f"/systems/{system_id}/parameters", status_code=303)


# ── 5.10 Auto-Fail Trigger Engine ─────────────────────────────────────────────

_PATCH_SLA_DAYS: dict = {
    "CRITICAL": 15,
    "HIGH":     30,
    "MEDIUM":   90,
    "LOW":      180,
}


async def _run_auto_fail_checks(session, system_id: Optional[str] = None) -> list[dict]:
    """
    Evaluate all auto-fail trigger types.
    If system_id is given, check only that system; otherwise check all active systems.
    Returns list of event dicts (may overlap with existing DB events — dedup handled below).
    """
    now = datetime.now(timezone.utc)
    events_created: list[dict] = []

    # Get target systems
    if system_id:
        sys_q = await session.execute(
            select(System).where(System.id == system_id, System.deleted_at.is_(None))
        )
        systems = sys_q.scalars().all()
    else:
        sys_q = await session.execute(
            select(System).where(System.deleted_at.is_(None))
        )
        systems = sys_q.scalars().all()

    for sys in systems:
        sid = sys.id

        # ── 1. Parameter Drift ───────────────────────────────────────────────
        drift_rows = await session.execute(
            select(ControlParameter).where(
                ControlParameter.system_id == sid,
                ControlParameter.drift_detected == True,
            )
        )
        for p in drift_rows.scalars().all():
            title = f"Parameter drift: {p.control_id} / {p.parameter_key}"
            details = {
                "required": p.required_value,
                "current":  p.current_value,
                "source":   p.source,
            }
            await _upsert_auto_fail_event(session, events_created, sid,
                "parameter_drift", p.control_id, "parameter",
                str(p.id), title, details, "Moderate")

        # ── 2. Review Overdue ────────────────────────────────────────────────
        rmf_rows = await session.execute(
            select(RmfRecord).where(
                RmfRecord.system_id  == sid,
                RmfRecord.status.in_(["not_started", "in_progress"]),
                RmfRecord.target_date.isnot(None),
            )
        )
        for rmf in rmf_rows.scalars().all():
            if not rmf.target_date:
                continue
            try:
                td = datetime.fromisoformat(str(rmf.target_date))
                if td < now:
                    title = f"RMF step {rmf.step} review overdue (target: {rmf.target_date})"
                    sev = "High" if (now - td).days > 30 else "Moderate"
                    await _upsert_auto_fail_event(session, events_created, sid,
                        "review_overdue", None, "rmf_record",
                        rmf.id, title, {"step": rmf.step, "target": str(rmf.target_date)}, sev)
            except (ValueError, TypeError):
                pass

        # ── 3. Document Expired ───────────────────────────────────────────────
        doc_rows = await session.execute(
            select(AtoDocument).where(
                AtoDocument.system_id == sid,
                AtoDocument.status.in_(["approved", "finalized"]),
            )
        )
        for doc in doc_rows.scalars().all():
            # If updated_at > 1 year ago, flag as potentially stale
            if doc.updated_at and (now - doc.updated_at).days > 365:
                title = f"ATO document possibly expired: {doc.doc_type} (last updated {doc.updated_at.strftime('%Y-%m-%d')})"
                await _upsert_auto_fail_event(session, events_created, sid,
                    "document_expired", None, "ato_document",
                    doc.id, title, {"doc_type": doc.doc_type, "last_updated": str(doc.updated_at)}, "Moderate")

        # ── 4. Evidence Stale ─────────────────────────────────────────────────
        sc_rows = await session.execute(
            select(SystemControl).where(
                SystemControl.system_id  == sid,
                SystemControl.last_updated_at.isnot(None),
            )
        )
        for sc in sc_rows.scalars().all():
            if sc.last_updated_at and (now - sc.last_updated_at).days > 365:
                title = f"Control evidence stale: {sc.control_id} (last updated {sc.last_updated_at.strftime('%Y-%m-%d')})"
                await _upsert_auto_fail_event(session, events_created, sid,
                    "evidence_stale", sc.control_id, "system_control",
                    sc.id, title, {"last_updated": str(sc.last_updated_at)}, "Low")

        # ── 5. Config Drift (reuse ControlParameter drift_detected) ──────────
        # Already covered by parameter_drift above (same underlying data).

        # ── 6. Patch SLA Breach ───────────────────────────────────────────────
        # Check NVD CVEs that are unpatched beyond SLA for their severity
        for severity, sla_days in _PATCH_SLA_DAYS.items():
            if severity not in ("CRITICAL", "HIGH"):
                continue   # Only Critical and High auto-fail
            cutoff = (now - timedelta(days=sla_days)).strftime("%Y-%m-%d")
            cve_rows = await session.execute(
                select(NvdCve).where(
                    NvdCve.cvss_severity  == severity,
                    NvdCve.published_date <= cutoff,
                    NvdCve.patched_date.is_(None),
                )
            )
            for cve in cve_rows.scalars().all():
                title = f"Patch SLA breach: {cve.cve_id} ({severity}, published {cve.published_date}, SLA: {sla_days}d)"
                await _upsert_auto_fail_event(session, events_created, sid,
                    "patch_sla_breach", "si-2", "nvd_cve",
                    str(cve.id), title,
                    {"cve_id": cve.cve_id, "score": cve.cvss_score, "sla_days": sla_days}, severity.capitalize())

        # ── 7. Governance Drift ──────────────────────────────────────────────
        # New SystemConnections without ATO review flag
        conn_rows = await session.execute(
            select(SystemConnection).where(
                SystemConnection.system_id == sid,
                SystemConnection.created_at >= (now - timedelta(days=30)),
            )
        )
        new_conns = conn_rows.scalars().all()
        if new_conns:
            for conn in new_conns:
                # Check if there's a ControlParameter for CA-3 tracking this connection
                existing_review = (await session.execute(
                    select(ControlParameter).where(
                        ControlParameter.system_id    == sid,
                        ControlParameter.control_id   == "ca-3",
                        ControlParameter.parameter_key == f"connection_{conn.id}",
                    )
                )).scalar_one_or_none()
                if not existing_review:
                    title = f"Governance drift: new system connection ({getattr(conn, 'name', conn.id)}) lacks CA-3 review"
                    await _upsert_auto_fail_event(session, events_created, sid,
                        "governance_drift", "ca-3", "system_connection",
                        conn.id, title,
                        {"connection_id": conn.id, "created": str(conn.created_at)}, "High")

    return events_created


async def _upsert_auto_fail_event(
    session,
    events_list: list,
    system_id: str,
    trigger_type: str,
    control_id: Optional[str],
    resource_type: str,
    resource_id: str,
    title: str,
    details: dict,
    severity: str,
):
    """
    Create or update an AutoFailEvent and optionally create/re-open a POA&M item.
    Deduplication: match on (system_id, trigger_type, resource_type, resource_id).
    """
    existing_event = (await session.execute(
        select(AutoFailEvent).where(
            AutoFailEvent.system_id     == system_id,
            AutoFailEvent.trigger_type  == trigger_type,
            AutoFailEvent.resource_type == resource_type,
            AutoFailEvent.resource_id   == str(resource_id),
            AutoFailEvent.status        != "suppressed",
        )
    )).scalar_one_or_none()

    if existing_event:
        existing_event.title      = title
        existing_event.details    = json.dumps(details, default=str)
        existing_event.severity   = severity
        existing_event.updated_at = datetime.now(timezone.utc)
        if existing_event.status == "resolved":
            existing_event.status = "open"   # re-open
        events_list.append({"action": "updated", "id": existing_event.id, "title": title})
        poam_id = existing_event.poam_id
    else:
        event = AutoFailEvent(
            system_id     = system_id,
            trigger_type  = trigger_type,
            control_id    = control_id,
            resource_type = resource_type,
            resource_id   = str(resource_id),
            title         = title,
            details       = json.dumps(details, default=str),
            severity      = severity,
            status        = "open",
        )
        session.add(event)
        await session.flush()   # populate event.id
        poam_id = None
        events_list.append({"action": "created", "id": event.id, "title": title})

    # ── 5.11 Auto-create POA&M ──────────────────────────────────────────────
    if not poam_id:
        import hashlib as _hashlib
        # Generate deterministic POA&M ID suffix from trigger provenance
        seed = f"{system_id[:6]}{trigger_type}{resource_id}"
        sfx  = _hashlib.sha256(seed.encode()).hexdigest()[:4].upper()
        today = date.today()
        poam_human_id = f"AUTF{today.strftime('%m%d%y')}-{sfx}SG"

        # Check for existing system-generated POA&M for this trigger
        existing_poam = (await session.execute(
            select(PoamItem).where(
                PoamItem.system_id        == system_id,
                PoamItem.system_generated == True,
                PoamItem.created_by       == f"auto_fail:{trigger_type}:{resource_id}",
                PoamItem.status.notin_(["closed_verified", "false_positive"]),
            )
        )).scalar_one_or_none()

        if existing_poam:
            # Re-open if resolved
            if existing_poam.status == "deferred_waiver":
                pass   # Keep waived
            elif existing_poam.status not in ("open", "in_progress", "blocked", "ready_for_review"):
                existing_poam.status = "open"
                existing_poam.updated_at = datetime.now(timezone.utc)
            poam_id = existing_poam.id
        else:
            due_date = (date.today() + timedelta(days=30)).isoformat()
            new_poam = PoamItem(
                system_id        = system_id,
                control_id       = control_id or "",
                weakness_name    = title,
                weakness_description = (
                    f"Auto-detected by BLACKSITE auto-fail engine.\n"
                    f"Trigger: {trigger_type}\n"
                    f"Resource: {resource_type}/{resource_id}\n"
                    f"Details: {json.dumps(details, indent=2)}"
                ),
                detection_source  = "self_report",
                severity          = severity,
                status            = "open",
                system_generated  = True,
                auto_fail_event_id = None,   # set after flush
                created_by        = f"auto_fail:{trigger_type}:{resource_id}",
                scheduled_completion = due_date,
                poam_id           = poam_human_id,
            )
            session.add(new_poam)
            await session.flush()
            poam_id = new_poam.id

        # Link event → POA&M
        if existing_event:
            existing_event.poam_id = poam_id
        else:
            event.poam_id = poam_id  # type: ignore[possibly-undefined]


@app.post("/admin/autofail/evaluate")
async def admin_autofail_evaluate(request: Request, system_id: str = ""):
    """Run auto-fail checks for one system (or all). Admin only."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        results = await _run_auto_fail_checks(session, system_id or None)
        await _log_audit(session, user, "RUN", "auto_fail_engine",
                         system_id or "all", {"events": len(results)})
        await session.commit()

    return JSONResponse({
        "ok":     True,
        "target": system_id or "all",
        "events": len(results),
        "detail": results[:50],
    })


@app.get("/admin/autofail", response_class=HTMLResponse)
async def admin_autofail_view(request: Request, system_id: str = ""):
    """View recent auto-fail events. Admin only."""
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        q = select(AutoFailEvent).order_by(AutoFailEvent.created_at.desc()).limit(200)
        if system_id:
            q = q.where(AutoFailEvent.system_id == system_id)
        events_rows = await session.execute(q)
        events = events_rows.scalars().all()

        systems_rows = await session.execute(
            select(System).where(System.deleted_at.is_(None)).order_by(System.name)
        )
        systems = systems_rows.scalars().all()

        ctx = await _full_ctx(request, session,
            events=events,
            systems=systems,
            filter_system=system_id,
        )

    return templates.TemplateResponse("admin_autofail.html", ctx)


# ── Phase 25 — Daily Workflow Stack ───────────────────────────────────────────

from datetime import date as _date

# Task labels per role (role → {task_num: label})
_TASK_LABELS: dict = {
    1: "Security log review",
    2: "Change control review",
    3: "Control health check",
    4: "Backup health check",
    5: "Access spot-check (HIPAA)",
    6: "Threat intel + advisory scan",
    7: "Vendor / BAA status",
    8: "Logbook entry + status notes",
}

ROLE_TASK_CONFIGS: dict = {
    "isso":               [1, 2, 3, 4, 5, 6, 7, 8],
    "issm":               [1, 2, 6, 8],
    "sca":                [3, 6, 8],
    "system_owner":       [2, 6, 8],
    "pmo":                [6, 7, 8],
    "pen_tester":         [1, 3, 8],
    "auditor":            [3, 6, 8],
    "incident_responder": [1, 4, 8],
    "bcdr_coordinator":   [4, 8],
    "bcdr":               [4, 8],          # alias — matches _VALID_SHELL_ROLES key
    "data_owner":         [5, 7, 8],
}

FEDERAL_HOLIDAYS_2026: set = {
    _date(2026, 1, 1), _date(2026, 1, 19), _date(2026, 2, 16),
    _date(2026, 5, 25), _date(2026, 6, 19), _date(2026, 7, 4),
    _date(2026, 9, 7), _date(2026, 10, 12), _date(2026, 11, 11),
    _date(2026, 11, 26), _date(2026, 12, 25),
}

QUARTERLY_OVERRIDES: dict = {
    "isso": {"q_tabletop_1": 13, "q_tabletop_2": 14, "q_after_action": 24,
             "q_risk_review": 16, "q_privacy_rev": 22},
    "issm": {"q_portfolio_review": 10, "q_risk_board": 20},
    "sca":  {"q_reassessment": 15, "q_sat_review": 22},
}

_ROTATION_CONTENT: dict = {
    "isso": {
        1:  {"title": "Access lifecycle review", "duration_min": 90,
             "instructions": "Review all user provisioning/deprovisioning events from the past cycle. Verify approvals exist for each account change. Flag anomalies for follow-up observation.",
             "evidence_label": "User change report + approval screenshots", "report_type": None},
        2:  {"title": "POA&M status and milestone tracking", "duration_min": 90,
             "instructions": "Review all open POA&M items. Update milestone dates, identify items approaching scheduled completion. Flag overdue items to the ISSM.",
             "evidence_label": "Updated POA&M export", "report_type": None},
        3:  {"title": "Control implementation spot-check", "duration_min": 90,
             "instructions": "Select 3-5 controls from the current baseline. Verify implementation is current and evidence is fresh. Document findings.",
             "evidence_label": "Control check notes with evidence references", "report_type": None},
        4:  {"title": "Incident log review + triage", "duration_min": 90,
             "instructions": "Review all open security incidents and events from prior week. Ensure each has an assigned owner and resolution timeline. Escalate as needed.",
             "evidence_label": "Incident review notes", "report_type": None},
        5:  {"title": "Artifact freshness audit", "duration_min": 90,
             "instructions": "Check all system artifacts for staleness. Flag any artifact older than its defined freshness window. Create observations for stale evidence.",
             "evidence_label": "Artifact freshness report with flagged items", "report_type": None},
        6:  {"title": "Risk register review", "duration_min": 90,
             "instructions": "Review all open risks. Update likelihood/impact if changed. Ensure each risk has a current mitigation plan and owner.",
             "evidence_label": "Risk register snapshot", "report_type": None},
        7:  {"title": "System boundary + scope verification", "duration_min": 90,
             "instructions": "Confirm system boundary documentation is current. Verify all components within scope are inventoried. Check for undocumented additions.",
             "evidence_label": "Boundary verification notes", "report_type": None},
        8:  {"title": "Inventory reconciliation", "duration_min": 90,
             "instructions": "Reconcile hardware and software inventory against current system components. Identify discrepancies. Update inventory records.",
             "evidence_label": "Reconciliation log", "report_type": None},
        9:  {"title": "Backup restore test", "duration_min": 90,
             "instructions": "Execute a restore test for critical system data or a representative subset. Record time-to-restore and validate data integrity post-restore.",
             "evidence_label": "Restore test record with results", "report_type": None},
        10: {"title": "Security training compliance check", "duration_min": 90,
             "instructions": "Verify all system personnel have completed required annual security awareness training. Follow up with overdue users.",
             "evidence_label": "Training completion report", "report_type": None},
        11: {"title": "Patch and vulnerability status review", "duration_min": 90,
             "instructions": "Review current patch status across all system components. Identify critical unpatched CVEs. Update tracking records.",
             "evidence_label": "Patch status report", "report_type": None},
        12: {"title": "Vendor and BAA review", "duration_min": 90,
             "instructions": "Review all active vendors. Confirm BAA status for ePHI-handling vendors. Flag expiring BAAs (within 90 days). Update vendor records.",
             "evidence_label": "Vendor review notes + BAA status", "report_type": None},
        13: {"title": "Tabletop exercise #1 — Ransomware scenario", "duration_min": 90,
             "instructions": "Conduct tabletop exercise: ransomware hits primary system. Walk through detection, containment, eradication, recovery. Document participant responses and gaps.",
             "evidence_label": "Tabletop exercise summary notes", "report_type": None},
        14: {"title": "Tabletop exercise #2 — Insider threat scenario", "duration_min": 90,
             "instructions": "Conduct tabletop exercise: suspected insider data exfiltration. Walk through detection workflow, HR coordination, preservation of evidence, escalation.",
             "evidence_label": "Tabletop exercise summary notes", "report_type": None},
        15: {"title": "Configuration baseline review", "duration_min": 90,
             "instructions": "Review system configuration against approved baseline. Identify drift items. Create or update POA&M entries for unresolved drift.",
             "evidence_label": "Configuration drift report", "report_type": None},
        16: {"title": "Risk acceptance and quarterly risk review", "duration_min": 90,
             "instructions": "Review all accepted risks for the quarter. Confirm acceptance rationale is still valid. Escalate any that have materially changed.",
             "evidence_label": "Risk acceptance review memo", "report_type": None},
        17: {"title": "POA&M milestone execution", "duration_min": 90,
             "instructions": "Execute scheduled POA&M milestones due this cycle. Upload closure evidence where applicable. Update milestone completion dates.",
             "evidence_label": "Closure evidence or milestone update log", "report_type": None},
        18: {"title": "Control evidence pack build", "duration_min": 90,
             "instructions": "Compile current evidence pack for all implemented controls. Validate evidence is within freshness window. Generate evidence pack report.",
             "evidence_label": "Evidence pack index", "report_type": "evidence_pack_controls"},
        19: {"title": "Observation review and disposition", "duration_min": 90,
             "instructions": "Review all open observations. Disposition each: promote to POA&M, close as resolved, or continue monitoring. Document rationale.",
             "evidence_label": "Observation disposition log", "report_type": None},
        20: {"title": "Data flow and integration mapping", "duration_min": 90,
             "instructions": "Review all documented data flows and integrations. Verify encryption in transit, auth methods, and logging status. Update data flow records.",
             "evidence_label": "Data flow review notes", "report_type": None},
        21: {"title": "Security control assessment prep", "duration_min": 90,
             "instructions": "Prepare for upcoming SCA assessment. Review last assessment findings. Ensure all remediated controls have fresh evidence.",
             "evidence_label": "Assessment prep checklist", "report_type": None},
        22: {"title": "PTA / PIA quarterly review", "duration_min": 90,
             "instructions": "Review privacy threshold analysis and privacy impact assessment. Verify data elements, disclosures, and retention policies are current.",
             "evidence_label": "PTA/PIA review notes", "report_type": None},
        23: {"title": "Interconnection and ISA review", "duration_min": 90,
             "instructions": "Review all system interconnections. Verify ISAs are current and not expired. Confirm monitoring is in place for each connection.",
             "evidence_label": "Interconnection review log", "report_type": None},
        24: {"title": "BCDR evidence pack build", "duration_min": 90,
             "instructions": "Compile BCDR evidence package: backup logs, restore test results, tabletop records, BCP/DRP review notes. Generate evidence pack report.",
             "evidence_label": "BCDR evidence pack index", "report_type": "bcdr_evidence_pack"},
        25: {"title": "Executive summary draft", "duration_min": 90,
             "instructions": "Draft executive summary of system security posture: control health, POA&M aging, risk posture, key actions since last cycle. Generate PDF report.",
             "evidence_label": "Executive summary notes", "report_type": "executive_summary"},
    },
    "issm": {
        1:  {"title": "Portfolio ISSO status review", "duration_min": 90,
             "instructions": "Review daily logbook completion status across all assigned ISSOs. Identify any system that missed yesterday's tasks. Follow up as needed.",
             "evidence_label": "Portfolio status notes", "report_type": None},
        2:  {"title": "Cross-system POA&M aging review", "duration_min": 90,
             "instructions": "Review POA&M items approaching 180-day mark across all portfolio systems. Flag items needing ISSM escalation or AO risk acceptance.",
             "evidence_label": "POA&M aging report", "report_type": None},
        3:  {"title": "Authorization boundary coordination", "duration_min": 90,
             "instructions": "Review any proposed boundary changes across portfolio. Coordinate with system owners and ISSOs on impact to authorization status.",
             "evidence_label": "Boundary coordination notes", "report_type": None},
        4:  {"title": "Incident escalation review", "duration_min": 90,
             "instructions": "Review all high-severity incidents escalated from ISSOs this cycle. Ensure each has ISSM oversight, proper notifications, and resolution tracking.",
             "evidence_label": "Escalation review notes", "report_type": None},
        5:  {"title": "Control family gap analysis", "duration_min": 90,
             "instructions": "Analyze control implementation status across portfolio. Identify control families with systemic gaps. Prepare remediation guidance.",
             "evidence_label": "Control gap analysis notes", "report_type": None},
        6:  {"title": "Vendor risk aggregation", "duration_min": 90,
             "instructions": "Aggregate vendor risk across all portfolio systems. Identify vendors shared across multiple systems. Review BAA coverage for ePHI processors.",
             "evidence_label": "Vendor risk summary", "report_type": None},
        7:  {"title": "Policy review and update", "duration_min": 90,
             "instructions": "Review information security policies for currency. Identify any policy that is more than 12 months old or references outdated guidance.",
             "evidence_label": "Policy review log", "report_type": None},
        8:  {"title": "Training metrics review", "duration_min": 90,
             "instructions": "Review security awareness training completion rates across all systems. Identify departments or roles with low completion. Coordinate follow-up.",
             "evidence_label": "Training metrics report", "report_type": None},
        9:  {"title": "Risk board preparation", "duration_min": 90,
             "instructions": "Prepare risk summary for the next risk board meeting. Compile accepted risks, open high risks, and proposed mitigations across portfolio.",
             "evidence_label": "Risk board briefing draft", "report_type": None},
        10: {"title": "Portfolio risk board review", "duration_min": 90,
             "instructions": "Conduct or document the quarterly risk board review. Record decisions on risk acceptance, escalation, and mitigation strategies.",
             "evidence_label": "Risk board meeting notes", "report_type": None},
        11: {"title": "ATO status review", "duration_min": 90,
             "instructions": "Review ATO expiration dates for all portfolio systems. Flag any expiring within 180 days. Initiate re-authorization planning as needed.",
             "evidence_label": "ATO status tracking", "report_type": None},
        12: {"title": "Continuous monitoring plan review", "duration_min": 90,
             "instructions": "Review continuous monitoring plans for all systems. Verify monitoring frequencies are being met. Identify gaps.",
             "evidence_label": "ConMon plan review notes", "report_type": None},
        13: {"title": "ISSO performance review", "duration_min": 90,
             "instructions": "Review ISSO rotation completion rates, task completion streaks, and open item counts across portfolio. Document support needs.",
             "evidence_label": "ISSO performance notes", "report_type": None},
        14: {"title": "Security architecture review", "duration_min": 90,
             "instructions": "Review system security architectures for compliance with organizational standards. Flag deviations for corrective action.",
             "evidence_label": "Architecture review notes", "report_type": None},
        15: {"title": "Configuration management oversight", "duration_min": 90,
             "instructions": "Review configuration management records across systems. Verify change approval processes are being followed. Identify unauthorized changes.",
             "evidence_label": "CM oversight notes", "report_type": None},
        16: {"title": "Threat landscape briefing", "duration_min": 90,
             "instructions": "Compile current threat intelligence relevant to portfolio systems. Review CISA advisories, NVD CVEs affecting known tech stack. Distribute to ISSOs.",
             "evidence_label": "Threat briefing summary", "report_type": None},
        17: {"title": "Interconnection governance review", "duration_min": 90,
             "instructions": "Review all cross-system interconnections in portfolio. Verify ISAs are current. Coordinate with partner system ISSOs on shared risks.",
             "evidence_label": "Interconnection governance notes", "report_type": None},
        18: {"title": "Audit coordination", "duration_min": 90,
             "instructions": "Coordinate with internal and external auditors. Prepare evidence packages as requested. Track open audit findings.",
             "evidence_label": "Audit coordination log", "report_type": None},
        19: {"title": "POA&M executive summary", "duration_min": 90,
             "instructions": "Draft POA&M executive summary across portfolio for AO review. Highlight items approaching deadlines, risk-accepted items, and systemic gaps.",
             "evidence_label": "POA&M executive summary draft", "report_type": None},
        20: {"title": "Portfolio risk board prep (deep)", "duration_min": 90,
             "instructions": "Deep preparation for portfolio risk board: compile all risk decisions, acceptance rationale, and mitigation plans. Ensure AO briefing materials are ready.",
             "evidence_label": "Risk board package", "report_type": "portfolio_risk_summary"},
        21: {"title": "Continuous monitoring metrics review", "duration_min": 90,
             "instructions": "Review automated monitoring metrics, SIEM alerts, and log aggregation health across all systems. Identify monitoring gaps.",
             "evidence_label": "ConMon metrics report", "report_type": None},
        22: {"title": "Privacy program oversight", "duration_min": 90,
             "instructions": "Review PTA/PIA status across all ePHI-bearing systems. Ensure all assessments are current. Coordinate with data owners on any issues.",
             "evidence_label": "Privacy oversight notes", "report_type": None},
        23: {"title": "Workforce development planning", "duration_min": 90,
             "instructions": "Review ISSO skill gaps and development needs. Plan training, certifications, and mentoring for the upcoming cycle.",
             "evidence_label": "Workforce development notes", "report_type": None},
        24: {"title": "Annual program assessment", "duration_min": 90,
             "instructions": "Assess the overall information security program against NIST CSF and organizational objectives. Identify maturity improvements achieved and planned.",
             "evidence_label": "Program assessment notes", "report_type": None},
        25: {"title": "Portfolio executive summary", "duration_min": 90,
             "instructions": "Generate portfolio-level executive summary: overall security posture, ATO status, POA&M aging, top risks, program health. Deliver to AO.",
             "evidence_label": "Portfolio executive summary", "report_type": "portfolio_executive_summary"},
    },
    "sca": {
        1:  {"title": "Assessment scope confirmation", "duration_min": 90,
             "instructions": "Confirm scope of current assessment engagement. Review system boundary, controls to be assessed, and assessment approach.",
             "evidence_label": "Scope confirmation memo", "report_type": None},
        2:  {"title": "Control documentation review", "duration_min": 90,
             "instructions": "Review SSP control narratives for completeness and accuracy. Flag controls with insufficient narrative depth or missing implementation details.",
             "evidence_label": "Documentation review notes", "report_type": None},
        3:  {"title": "Evidence collection — AC family", "duration_min": 90,
             "instructions": "Collect and review evidence for Access Control family controls. Interview relevant personnel. Test control implementations as applicable.",
             "evidence_label": "AC evidence package", "report_type": None},
        4:  {"title": "Evidence collection — AU/CA/CM family", "duration_min": 90,
             "instructions": "Collect evidence for Audit, Assessment, and Configuration Management controls. Review audit logs, assessment records, and change management processes.",
             "evidence_label": "AU/CA/CM evidence package", "report_type": None},
        5:  {"title": "Evidence collection — CP/IA/IR family", "duration_min": 90,
             "instructions": "Collect evidence for Contingency Planning, Identification/Authentication, and Incident Response controls.",
             "evidence_label": "CP/IA/IR evidence package", "report_type": None},
        6:  {"title": "Evidence collection — MA/MP/PE/PL family", "duration_min": 90,
             "instructions": "Collect evidence for Maintenance, Media Protection, Physical Protection, and Planning controls.",
             "evidence_label": "MA/MP/PE/PL evidence package", "report_type": None},
        7:  {"title": "Evidence collection — RA/SA/SC family", "duration_min": 90,
             "instructions": "Collect evidence for Risk Assessment, System Acquisition, and System Communications controls.",
             "evidence_label": "RA/SA/SC evidence package", "report_type": None},
        8:  {"title": "Evidence collection — SI/PM family", "duration_min": 90,
             "instructions": "Collect evidence for System Integrity and Program Management controls. Review patch management, malware defenses, and security planning artifacts.",
             "evidence_label": "SI/PM evidence package", "report_type": None},
        9:  {"title": "Technical testing — vulnerability scan", "duration_min": 90,
             "instructions": "Execute or review vulnerability scan results. Correlate findings with known CVEs. Assess remediation status for critical/high findings.",
             "evidence_label": "Vulnerability scan report", "report_type": None},
        10: {"title": "Technical testing — configuration check", "duration_min": 90,
             "instructions": "Review system configuration against STIG or CIS benchmark. Document deviations. Assess risk impact of findings.",
             "evidence_label": "Configuration check results", "report_type": None},
        11: {"title": "Interview — system owner", "duration_min": 90,
             "instructions": "Conduct structured interview with system owner. Validate understanding of security responsibilities, risk posture, and control ownership.",
             "evidence_label": "Interview notes — system owner", "report_type": None},
        12: {"title": "Interview — ISSO", "duration_min": 90,
             "instructions": "Conduct structured interview with ISSO. Review daily operational practices, incident handling, and POA&M management approach.",
             "evidence_label": "Interview notes — ISSO", "report_type": None},
        13: {"title": "Finding draft — high/critical items", "duration_min": 90,
             "instructions": "Draft findings for all high and critical assessment observations. Include control reference, description, impact, and recommended corrective action.",
             "evidence_label": "Draft findings — critical/high", "report_type": None},
        14: {"title": "Finding draft — moderate items", "duration_min": 90,
             "instructions": "Draft findings for moderate assessment observations. Complete finding narratives with evidence citations and control mappings.",
             "evidence_label": "Draft findings — moderate", "report_type": None},
        15: {"title": "Reassessment — prior findings", "duration_min": 90,
             "instructions": "Reassess controls that had findings in the previous assessment cycle. Verify remediation was completed and effective.",
             "evidence_label": "Reassessment notes — prior findings", "report_type": None},
        16: {"title": "Assessment report draft", "duration_min": 90,
             "instructions": "Draft the full security assessment report (SAR). Include executive summary, methodology, findings, risk ratings, and recommendations.",
             "evidence_label": "SAR draft", "report_type": None},
        17: {"title": "Assessment report review", "duration_min": 90,
             "instructions": "Internal review of SAR draft. Check findings for accuracy, consistency, and completeness. Revise as needed before delivery.",
             "evidence_label": "SAR review notes", "report_type": None},
        18: {"title": "SAR delivery + ISSO walkthrough", "duration_min": 90,
             "instructions": "Deliver SAR to ISSO. Conduct walkthrough of findings. Answer questions and clarify remediation expectations.",
             "evidence_label": "Delivery confirmation + walkthrough notes", "report_type": None},
        19: {"title": "POA&M input validation", "duration_min": 90,
             "instructions": "Review POA&M entries created in response to SAR findings. Validate that all findings are captured and milestone dates are realistic.",
             "evidence_label": "POA&M validation notes", "report_type": None},
        20: {"title": "Continuous monitoring plan contribution", "duration_min": 90,
             "instructions": "Review and contribute to the system continuous monitoring plan. Recommend monitoring frequencies and assessment methods for key controls.",
             "evidence_label": "ConMon plan contribution notes", "report_type": None},
        21: {"title": "Assessment methodology review", "duration_min": 90,
             "instructions": "Review and update assessment methodology for the next cycle. Incorporate lessons learned from current assessment.",
             "evidence_label": "Methodology review notes", "report_type": None},
        22: {"title": "Security awareness training verification", "duration_min": 90,
             "instructions": "Verify completion of security awareness training for all assessed system users. Flag gaps for ISSO follow-up.",
             "evidence_label": "Training verification report", "report_type": None},
        23: {"title": "Privacy control assessment", "duration_min": 90,
             "instructions": "Assess privacy controls (AP, AR, DI, DM, IP, SE, TR, UL families). Review PTA/PIA currency and data handling practices.",
             "evidence_label": "Privacy assessment notes", "report_type": None},
        24: {"title": "Evidence package compilation", "duration_min": 90,
             "instructions": "Compile final evidence package supporting all assessment findings. Organize by control family. Verify all evidence is properly cited in SAR.",
             "evidence_label": "Final evidence package index", "report_type": "sca_evidence_pack"},
        25: {"title": "Assessment closeout and lessons learned", "duration_min": 90,
             "instructions": "Document lessons learned from the assessment cycle. Update assessment templates. Brief ISSO on future assessment preparation.",
             "evidence_label": "Closeout memo + lessons learned", "report_type": None},
    },
    "system_owner": {
        1:  {"title": "Operational status briefing", "duration_min": 90, "instructions": "Review current operational status of the system. Confirm all components are functioning normally. Review any active incidents or performance issues.", "evidence_label": "Status briefing notes", "report_type": None},
        2:  {"title": "Change request review", "duration_min": 90, "instructions": "Review pending change requests. Ensure all proposed changes have security review completed and approvals from ISSO and change board.", "evidence_label": "Change review log", "report_type": None},
        3:  {"title": "Risk acceptance review", "duration_min": 90, "instructions": "Review risks pending system owner acceptance. Document rationale and sign off on accepted risks within your authority level.", "evidence_label": "Risk acceptance decisions", "report_type": None},
        4:  {"title": "Resource and budget alignment", "duration_min": 90, "instructions": "Review security resource allocation. Confirm budget is aligned with current risk posture and POA&M remediation needs.", "evidence_label": "Resource alignment notes", "report_type": None},
        5:  {"title": "Vendor contract review", "duration_min": 90, "instructions": "Review vendor contracts for security terms and compliance requirements. Flag contracts approaching renewal that need BAA or security addendum review.", "evidence_label": "Contract review notes", "report_type": None},
        6:  {"title": "Stakeholder security briefing", "duration_min": 90, "instructions": "Prepare or deliver security status briefing for key stakeholders. Cover current posture, active risks, and planned improvements.", "evidence_label": "Briefing notes or deck", "report_type": None},
        7:  {"title": "Business continuity review", "duration_min": 90, "instructions": "Review business continuity plan for currency and accuracy. Confirm recovery objectives (RTO/RPO) are still aligned with business needs.", "evidence_label": "BCP review notes", "report_type": None},
        8:  {"title": "System lifecycle planning", "duration_min": 90, "instructions": "Review system lifecycle roadmap. Identify components approaching end-of-life. Plan for upgrades or replacements with security implications.", "evidence_label": "Lifecycle planning notes", "report_type": None},
        9:  {"title": "Inter-system dependency review", "duration_min": 90, "instructions": "Review dependencies on external systems and services. Verify SLAs are current. Identify single points of failure.", "evidence_label": "Dependency review notes", "report_type": None},
        10: {"title": "Workforce security review", "duration_min": 90, "instructions": "Review workforce security posture: training completion, background check currency, separation of duties compliance.", "evidence_label": "Workforce review notes", "report_type": None},
        11: {"title": "POA&M resource commitment", "duration_min": 90, "instructions": "Review open POA&M items requiring resource commitment from system owner. Confirm resources are assigned and schedules are realistic.", "evidence_label": "Resource commitment log", "report_type": None},
        12: {"title": "Third-party security review", "duration_min": 90, "instructions": "Review security posture of third-party services integrated with the system. Request evidence of compliance certifications (SOC 2, FedRAMP, HIPAA) as applicable.", "evidence_label": "Third-party review notes", "report_type": None},
        13: {"title": "Incident impact assessment", "duration_min": 90, "instructions": "Review any recent security incidents for business impact. Confirm recovery was complete and no residual impact remains.", "evidence_label": "Incident impact assessment notes", "report_type": None},
        14: {"title": "Data governance review", "duration_min": 90, "instructions": "Review data governance practices for the system. Confirm data classification, handling, and retention policies are being followed.", "evidence_label": "Data governance review notes", "report_type": None},
        15: {"title": "Authorization status review", "duration_min": 90, "instructions": "Review current authorization status and expiration. Initiate re-authorization planning if expiry is within 180 days.", "evidence_label": "Authorization status notes", "report_type": None},
        16: {"title": "Performance vs. security trade-off review", "duration_min": 90, "instructions": "Review any deferred security controls or accepted risks driven by performance requirements. Assess whether trade-offs remain justified.", "evidence_label": "Trade-off review notes", "report_type": None},
        17: {"title": "Audit finding remediation oversight", "duration_min": 90, "instructions": "Review progress on audit findings requiring system owner involvement. Confirm resources and schedules are on track.", "evidence_label": "Remediation oversight notes", "report_type": None},
        18: {"title": "Security metrics review", "duration_min": 90, "instructions": "Review system security metrics: patch compliance rate, training completion, POA&M on-time rate, incident response times.", "evidence_label": "Metrics dashboard export", "report_type": None},
        19: {"title": "Privacy compliance review", "duration_min": 90, "instructions": "Review privacy compliance status for ePHI/PII-bearing systems. Confirm breach notification procedures are documented and tested.", "evidence_label": "Privacy compliance notes", "report_type": None},
        20: {"title": "Contingency plan sign-off", "duration_min": 90, "instructions": "Review and sign off on the current contingency plan. Confirm it reflects current system architecture and organizational requirements.", "evidence_label": "CP sign-off record", "report_type": None},
        21: {"title": "Security investment review", "duration_min": 90, "instructions": "Review security tool and control investments. Assess effectiveness against current threat landscape. Identify gaps requiring new investment.", "evidence_label": "Investment review notes", "report_type": None},
        22: {"title": "Regulatory compliance check", "duration_min": 90, "instructions": "Review regulatory requirements applicable to the system. Confirm all compliance activities are current and documented.", "evidence_label": "Regulatory compliance checklist", "report_type": None},
        23: {"title": "System owner security attestation", "duration_min": 90, "instructions": "Complete system owner security attestation for the current cycle. Confirm understanding of and responsibility for system security posture.", "evidence_label": "Signed attestation", "report_type": None},
        24: {"title": "Annual security review meeting", "duration_min": 90, "instructions": "Conduct annual system security review with ISSO, ISSM, and key stakeholders. Document decisions and action items.", "evidence_label": "Meeting notes + action items", "report_type": None},
        25: {"title": "System owner executive summary", "duration_min": 90, "instructions": "Draft executive summary of system security posture for leadership. Include key risks, compliance status, and planned investments.", "evidence_label": "Executive summary draft", "report_type": "executive_summary"},
    },
    "pmo": {
        1:  {"title": "Project security milestone review", "duration_min": 90, "instructions": "Review security-related milestones across all active projects. Identify any that are at risk of slipping.", "evidence_label": "Milestone status report", "report_type": None},
        2:  {"title": "Risk register — PMO perspective", "duration_min": 90, "instructions": "Review project risks with security implications. Ensure each has an owner, mitigation plan, and escalation path.", "evidence_label": "Risk register notes", "report_type": None},
        3:  {"title": "Security requirements traceability", "duration_min": 90, "instructions": "Review requirements traceability matrix. Verify all security requirements from the SSP are assigned to project work items and tracked.", "evidence_label": "Traceability review notes", "report_type": None},
        4:  {"title": "Vendor delivery review", "duration_min": 90, "instructions": "Review vendor deliverables for security compliance. Check SOW security requirements are met. Flag any deficiencies.", "evidence_label": "Vendor delivery review notes", "report_type": None},
        5:  {"title": "Change management coordination", "duration_min": 90, "instructions": "Coordinate security review of pending project changes. Ensure all changes go through the change board and ISSO review.", "evidence_label": "Change coordination log", "report_type": None},
        6:  {"title": "Security acceptance testing coordination", "duration_min": 90, "instructions": "Coordinate security acceptance testing for deliverables approaching completion. Engage SCA or ISSO for testing support.", "evidence_label": "Test coordination notes", "report_type": None},
        7:  {"title": "Documentation currency check", "duration_min": 90, "instructions": "Review project security documentation for currency. Identify outdated artifacts that need refresh before next milestone.", "evidence_label": "Documentation review log", "report_type": None},
        8:  {"title": "Budget vs. security spend tracking", "duration_min": 90, "instructions": "Track security-related spend against budget. Identify variances. Escalate underfunded security work items.", "evidence_label": "Budget tracking notes", "report_type": None},
        9:  {"title": "Stakeholder security briefing prep", "duration_min": 90, "instructions": "Prepare security section of stakeholder briefing. Include current risk status, open findings, and upcoming security milestones.", "evidence_label": "Briefing preparation notes", "report_type": None},
        10: {"title": "Lessons learned — security", "duration_min": 90, "instructions": "Capture security-related lessons learned from the current project phase. Incorporate into future project planning.", "evidence_label": "Lessons learned notes", "report_type": None},
        11: {"title": "Personnel security tracking", "duration_min": 90, "instructions": "Verify all project personnel have current background investigations and system access justified by role.", "evidence_label": "Personnel security review", "report_type": None},
        12: {"title": "Subcontractor security review", "duration_min": 90, "instructions": "Review subcontractor security posture and compliance. Verify flow-down of security requirements to subcontractors.", "evidence_label": "Subcontractor review notes", "report_type": None},
        13: {"title": "POA&M project integration", "duration_min": 90, "instructions": "Review POA&M items requiring project resources for remediation. Integrate milestones into project schedule.", "evidence_label": "POA&M integration notes", "report_type": None},
        14: {"title": "Security gate review — phase transition", "duration_min": 90, "instructions": "Conduct security gate review for any project approaching phase transition. Verify all security criteria are met before advancing.", "evidence_label": "Gate review record", "report_type": None},
        15: {"title": "Earned value — security work packages", "duration_min": 90, "instructions": "Calculate earned value for security work packages. Identify any with cost or schedule variance. Develop corrective action plans.", "evidence_label": "EVM analysis notes", "report_type": None},
        16: {"title": "Risk response implementation tracking", "duration_min": 90, "instructions": "Track implementation status of all planned risk responses. Identify responses behind schedule.", "evidence_label": "Risk response tracking", "report_type": None},
        17: {"title": "Security work breakdown review", "duration_min": 90, "instructions": "Review the security WBS for completeness. Identify any security activities missing from the project plan.", "evidence_label": "WBS review notes", "report_type": None},
        18: {"title": "Quality assurance — security deliverables", "duration_min": 90, "instructions": "QA review of security deliverables completed this cycle. Verify they meet defined acceptance criteria.", "evidence_label": "QA review notes", "report_type": None},
        19: {"title": "Contract compliance review", "duration_min": 90, "instructions": "Review contract security compliance status. Confirm all required certifications, reports, and audits are current.", "evidence_label": "Contract compliance notes", "report_type": None},
        20: {"title": "Security program integration review", "duration_min": 90, "instructions": "Review integration of project security activities with the broader organizational security program.", "evidence_label": "Integration review notes", "report_type": None},
        21: {"title": "Transition planning — security", "duration_min": 90, "instructions": "Review security aspects of system transition or deployment plan. Ensure operational security requirements are met before go-live.", "evidence_label": "Transition security review", "report_type": None},
        22: {"title": "Post-implementation security review", "duration_min": 90, "instructions": "Conduct post-implementation review of security controls for recently deployed components. Document findings.", "evidence_label": "Post-implementation review notes", "report_type": None},
        23: {"title": "Independent project security audit prep", "duration_min": 90, "instructions": "Prepare project security artifacts for independent audit. Organize documentation and evidence packages.", "evidence_label": "Audit prep checklist", "report_type": None},
        24: {"title": "Program security health assessment", "duration_min": 90, "instructions": "Assess overall security health of the program. Identify systemic issues and recommend program-level improvements.", "evidence_label": "Health assessment notes", "report_type": None},
        25: {"title": "PMO security summary report", "duration_min": 90, "instructions": "Generate PMO security summary: project security milestone status, open risks, resource utilization, and upcoming gate reviews.", "evidence_label": "PMO security summary", "report_type": "pmo_security_summary"},
    },
    "pen_tester": {
        1:  {"title": "Engagement scope review", "duration_min": 90, "instructions": "Review current engagement scope, rules of engagement, and authorization. Confirm all targets are within scope.", "evidence_label": "Scope confirmation record", "report_type": None},
        2:  {"title": "Reconnaissance — passive", "duration_min": 90, "instructions": "Conduct passive reconnaissance on in-scope targets. Document findings without active interaction with target systems.", "evidence_label": "Passive recon notes", "report_type": None},
        3:  {"title": "Reconnaissance — active", "duration_min": 90, "instructions": "Conduct active reconnaissance and enumeration of in-scope targets. Document open ports, services, and initial attack surface.", "evidence_label": "Active recon results", "report_type": None},
        4:  {"title": "Vulnerability identification", "duration_min": 90, "instructions": "Identify vulnerabilities in enumerated services. Cross-reference with CVE database. Prioritize by exploitability and impact.", "evidence_label": "Vulnerability identification log", "report_type": None},
        5:  {"title": "Exploitation — low-hanging fruit", "duration_min": 90, "instructions": "Attempt exploitation of highest-confidence vulnerabilities. Document each attempt with methodology, outcome, and evidence.", "evidence_label": "Exploitation log — initial", "report_type": None},
        6:  {"title": "Privilege escalation attempts", "duration_min": 90, "instructions": "From any obtained access, attempt privilege escalation. Document escalation paths found and methods used.", "evidence_label": "Privilege escalation notes", "report_type": None},
        7:  {"title": "Lateral movement testing", "duration_min": 90, "instructions": "Test for lateral movement opportunities from compromised positions. Document network segmentation effectiveness.", "evidence_label": "Lateral movement notes", "report_type": None},
        8:  {"title": "Persistence mechanisms review", "duration_min": 90, "instructions": "Test for ability to establish persistence. Document what persistence mechanisms are available and would be detectable.", "evidence_label": "Persistence testing notes", "report_type": None},
        9:  {"title": "Data exfiltration path testing", "duration_min": 90, "instructions": "Test data exfiltration paths. Verify DLP controls are functioning. Document any viable exfil channels found.", "evidence_label": "Exfiltration path notes", "report_type": None},
        10: {"title": "Web application testing — auth/session", "duration_min": 90, "instructions": "Test web application authentication and session management. Check for common OWASP Top 10 vulnerabilities.", "evidence_label": "Web app auth testing notes", "report_type": None},
        11: {"title": "Web application testing — injection", "duration_min": 90, "instructions": "Test for injection vulnerabilities (SQL, command, LDAP, etc.). Document findings with proof-of-concept details.", "evidence_label": "Injection testing notes", "report_type": None},
        12: {"title": "Social engineering simulation design", "duration_min": 90, "instructions": "Design phishing or social engineering simulation (if in scope). Prepare campaign materials and metrics plan.", "evidence_label": "Simulation design notes", "report_type": None},
        13: {"title": "Physical security review (if in scope)", "duration_min": 90, "instructions": "Review physical access controls relevant to the target system. Document findings and observations.", "evidence_label": "Physical review notes", "report_type": None},
        14: {"title": "Configuration review — infrastructure", "duration_min": 90, "instructions": "Review infrastructure configurations for security weaknesses. Compare against hardening benchmarks.", "evidence_label": "Config review results", "report_type": None},
        15: {"title": "API security testing", "duration_min": 90, "instructions": "Test APIs for authentication weaknesses, broken object-level authorization, and data exposure vulnerabilities.", "evidence_label": "API testing notes", "report_type": None},
        16: {"title": "Cryptography review", "duration_min": 90, "instructions": "Review cryptographic implementations. Check for weak algorithms, key management issues, and certificate problems.", "evidence_label": "Crypto review notes", "report_type": None},
        17: {"title": "Finding documentation and triage", "duration_min": 90, "instructions": "Document all findings gathered to date. Triage by severity. Prepare preliminary finding descriptions.", "evidence_label": "Finding documentation draft", "report_type": None},
        18: {"title": "Remediation guidance development", "duration_min": 90, "instructions": "Develop actionable remediation guidance for all documented findings. Include references to applicable standards.", "evidence_label": "Remediation guidance draft", "report_type": None},
        19: {"title": "Penetration test report draft", "duration_min": 90, "instructions": "Draft full penetration test report: executive summary, scope, methodology, findings, risk ratings, remediation guidance.", "evidence_label": "Pentest report draft", "report_type": None},
        20: {"title": "Report review and quality check", "duration_min": 90, "instructions": "Internal review of pentest report. Check findings for accuracy, exploitability ratings, and remediation clarity.", "evidence_label": "Report review notes", "report_type": None},
        21: {"title": "ISSO findings walkthrough", "duration_min": 90, "instructions": "Walk ISSO through findings. Answer technical questions. Help prioritize remediation sequence.", "evidence_label": "Walkthrough notes", "report_type": None},
        22: {"title": "Retest of remediated findings", "duration_min": 90, "instructions": "Retest findings that the ISSO reports as remediated. Document retest results and update finding status.", "evidence_label": "Retest results", "report_type": None},
        23: {"title": "Evidence pack compilation", "duration_min": 90, "instructions": "Compile evidence pack: screenshots, payloads, logs, tool output. Organize by finding. Sanitize sensitive data.", "evidence_label": "Evidence pack index", "report_type": None},
        24: {"title": "Threat model update", "duration_min": 90, "instructions": "Update system threat model based on findings. Document new attack paths identified during testing.", "evidence_label": "Threat model updates", "report_type": None},
        25: {"title": "Engagement closeout", "duration_min": 90, "instructions": "Close out engagement: confirm all artifacts are delivered, cleanup any test accounts or implants, deliver final report.", "evidence_label": "Closeout memo", "report_type": "pentest_report"},
    },
    "auditor": {
        1:  {"title": "Audit planning and scope confirmation", "duration_min": 90, "instructions": "Confirm audit scope, objectives, and criteria. Review prior audit findings for context. Confirm stakeholder availability.", "evidence_label": "Audit plan document", "report_type": None},
        2:  {"title": "Document request list — initial", "duration_min": 90, "instructions": "Issue initial document request list to ISSO. Include SSP, POA&M, risk register, policies, and recent assessment reports.", "evidence_label": "Document request list", "report_type": None},
        3:  {"title": "Policy and procedure review", "duration_min": 90, "instructions": "Review information security policies and procedures for completeness, currency, and compliance with applicable standards.", "evidence_label": "Policy review notes", "report_type": None},
        4:  {"title": "Access control testing", "duration_min": 90, "instructions": "Test access control implementation. Review user access lists, approval records, and separation of duties.", "evidence_label": "Access control test results", "report_type": None},
        5:  {"title": "Change management review", "duration_min": 90, "instructions": "Review change management process and records. Verify all changes were approved and security-reviewed.", "evidence_label": "Change management review notes", "report_type": None},
        6:  {"title": "Audit log review", "duration_min": 90, "instructions": "Review system audit logs for completeness, integrity, and evidence of appropriate monitoring activity.", "evidence_label": "Audit log review notes", "report_type": None},
        7:  {"title": "Backup and recovery verification", "duration_min": 90, "instructions": "Verify backup procedures are implemented and restore tests are documented. Review backup logs.", "evidence_label": "Backup verification notes", "report_type": None},
        8:  {"title": "Incident response review", "duration_min": 90, "instructions": "Review incident response procedures and any incidents from the audit period. Verify proper handling and documentation.", "evidence_label": "IR review notes", "report_type": None},
        9:  {"title": "Physical and environmental review", "duration_min": 90, "instructions": "Review physical access controls and environmental protection measures applicable to the system.", "evidence_label": "Physical/environmental review notes", "report_type": None},
        10: {"title": "Training and awareness verification", "duration_min": 90, "instructions": "Verify security awareness training completion records. Confirm training covers required topics.", "evidence_label": "Training verification notes", "report_type": None},
        11: {"title": "Third-party and vendor audit", "duration_min": 90, "instructions": "Review third-party and vendor security posture. Verify BAAs are current and vendor compliance attestations are on file.", "evidence_label": "Vendor audit notes", "report_type": None},
        12: {"title": "Personnel security review", "duration_min": 90, "instructions": "Review personnel security records: background investigations, separation agreements, privileged user agreements.", "evidence_label": "Personnel security review notes", "report_type": None},
        13: {"title": "Configuration and patch review", "duration_min": 90, "instructions": "Review configuration management records and patch status. Verify unauthorized changes are detected and remediated.", "evidence_label": "Config/patch review notes", "report_type": None},
        14: {"title": "Contingency plan testing review", "duration_min": 90, "instructions": "Review contingency plan testing records. Verify tests were conducted as scheduled and results documented.", "evidence_label": "CP testing review notes", "report_type": None},
        15: {"title": "Risk management review", "duration_min": 90, "instructions": "Review risk assessment, risk register, and risk treatment decisions. Verify risk acceptance approvals are documented.", "evidence_label": "Risk management review notes", "report_type": None},
        16: {"title": "POA&M compliance review", "duration_min": 90, "instructions": "Review POA&M for accuracy, completeness, and timeliness. Flag overdue milestones and missing closure evidence.", "evidence_label": "POA&M compliance notes", "report_type": None},
        17: {"title": "Privacy compliance audit", "duration_min": 90, "instructions": "Audit privacy practices for ePHI/PII handling. Review PTA/PIA currency, consent mechanisms, and breach notification procedures.", "evidence_label": "Privacy audit notes", "report_type": None},
        18: {"title": "Finding draft — compliance gaps", "duration_min": 90, "instructions": "Draft audit findings for all identified compliance gaps. Include control reference, finding description, risk level, and recommendation.", "evidence_label": "Finding draft", "report_type": None},
        19: {"title": "Management response coordination", "duration_min": 90, "instructions": "Share draft findings with management for response. Document management's corrective action commitments and target dates.", "evidence_label": "Management response log", "report_type": None},
        20: {"title": "Audit report draft", "duration_min": 90, "instructions": "Draft the audit report: executive summary, scope, methodology, findings with management responses, and overall opinion.", "evidence_label": "Audit report draft", "report_type": None},
        21: {"title": "Audit report review", "duration_min": 90, "instructions": "Internal review of audit report draft. Check for accuracy, consistency, and completeness before issuance.", "evidence_label": "Audit report review notes", "report_type": None},
        22: {"title": "Audit report delivery", "duration_min": 90, "instructions": "Deliver final audit report to system owner, ISSM, and AO. Conduct walkthrough as needed.", "evidence_label": "Delivery confirmation", "report_type": None},
        23: {"title": "Finding remediation tracking setup", "duration_min": 90, "instructions": "Set up remediation tracking for audit findings. Confirm each finding has an owner and target date.", "evidence_label": "Remediation tracking setup", "report_type": None},
        24: {"title": "Follow-up audit planning", "duration_min": 90, "instructions": "Plan follow-up audit to verify remediation of critical and high findings. Set scope and timeline.", "evidence_label": "Follow-up audit plan", "report_type": None},
        25: {"title": "Audit closeout and lessons learned", "duration_min": 90, "instructions": "Close out audit engagement. Document lessons learned. Update audit methodology for next cycle.", "evidence_label": "Closeout memo", "report_type": "audit_report"},
    },
    "incident_responder": {
        1:  {"title": "Incident queue review", "duration_min": 90, "instructions": "Review all open incidents and security events. Confirm each has an assigned responder, severity, and current status.", "evidence_label": "Incident queue review notes", "report_type": None},
        2:  {"title": "Alert triage — SIEM", "duration_min": 90, "instructions": "Triage new SIEM alerts from the past 24 hours. Classify each as true positive, false positive, or requires investigation.", "evidence_label": "Alert triage log", "report_type": None},
        3:  {"title": "Threat hunting — IOC scan", "duration_min": 90, "instructions": "Hunt for known indicators of compromise in system logs and network traffic. Document findings.", "evidence_label": "Threat hunt results", "report_type": None},
        4:  {"title": "Malware analysis (if applicable)", "duration_min": 90, "instructions": "Perform static or dynamic analysis of any malware samples from current incidents. Document behavior and IOCs.", "evidence_label": "Malware analysis notes", "report_type": None},
        5:  {"title": "Containment verification", "duration_min": 90, "instructions": "Verify containment actions for active incidents are effective. Confirm no lateral spread has occurred.", "evidence_label": "Containment verification notes", "report_type": None},
        6:  {"title": "Evidence preservation and chain of custody", "duration_min": 90, "instructions": "Ensure all evidence collected from active incidents is properly preserved and chain of custody is documented.", "evidence_label": "Evidence preservation log", "report_type": None},
        7:  {"title": "Eradication verification", "duration_min": 90, "instructions": "Verify eradication steps for resolved incidents were effective. Confirm root cause is addressed.", "evidence_label": "Eradication verification notes", "report_type": None},
        8:  {"title": "Recovery monitoring", "duration_min": 90, "instructions": "Monitor systems recovering from incidents for signs of recurrence. Document recovery validation steps.", "evidence_label": "Recovery monitoring log", "report_type": None},
        9:  {"title": "Incident documentation update", "duration_min": 90, "instructions": "Update incident documentation for all active and recently closed incidents. Ensure timeline and response actions are current.", "evidence_label": "Incident documentation updates", "report_type": None},
        10: {"title": "Runbook review and update", "duration_min": 90, "instructions": "Review incident response runbooks for currency. Update procedures based on recent incident experience.", "evidence_label": "Runbook review notes", "report_type": None},
        11: {"title": "Tool health check", "duration_min": 90, "instructions": "Verify incident response tools (SIEM, EDR, forensic tools) are functioning correctly and data feeds are current.", "evidence_label": "Tool health check results", "report_type": None},
        12: {"title": "Communication plan review", "duration_min": 90, "instructions": "Review incident communication plans and contact lists. Verify escalation paths and stakeholder contacts are current.", "evidence_label": "Communication plan review notes", "report_type": None},
        13: {"title": "Tabletop exercise — IR scenario", "duration_min": 90, "instructions": "Conduct tabletop exercise for a current threat scenario relevant to the system. Document gaps identified.", "evidence_label": "Tabletop exercise notes", "report_type": None},
        14: {"title": "IOC sharing and threat intelligence", "duration_min": 90, "instructions": "Share relevant IOCs with partner organizations or ISACs as appropriate. Review incoming threat intelligence.", "evidence_label": "IOC sharing log", "report_type": None},
        15: {"title": "Post-incident review — recent closure", "duration_min": 90, "instructions": "Conduct post-incident review of most recently closed incident. Document lessons learned and process improvements.", "evidence_label": "Post-incident review notes", "report_type": None},
        16: {"title": "Forensic capability review", "duration_min": 90, "instructions": "Review forensic capability and tooling. Identify gaps. Verify forensic procedures are documented.", "evidence_label": "Forensic capability review", "report_type": None},
        17: {"title": "Legal and compliance coordination", "duration_min": 90, "instructions": "Coordinate with legal on any incidents with regulatory notification implications. Review breach notification requirements.", "evidence_label": "Legal coordination notes", "report_type": None},
        18: {"title": "Metrics review — MTTD/MTTR", "duration_min": 90, "instructions": "Review mean time to detect and mean time to respond metrics for the current period. Identify trends and improvement opportunities.", "evidence_label": "Metrics review notes", "report_type": None},
        19: {"title": "Vulnerability correlation", "duration_min": 90, "instructions": "Correlate recent incidents with known vulnerabilities. Identify patterns suggesting systemic control failures.", "evidence_label": "Vulnerability correlation notes", "report_type": None},
        20: {"title": "Security monitoring optimization", "duration_min": 90, "instructions": "Review and tune SIEM rules and detection signatures. Reduce false positive rate while maintaining detection coverage.", "evidence_label": "Monitoring optimization notes", "report_type": None},
        21: {"title": "Incident response plan review", "duration_min": 90, "instructions": "Review the full incident response plan for currency and completeness. Update sections as needed.", "evidence_label": "IRP review notes", "report_type": None},
        22: {"title": "Notification and reporting compliance", "duration_min": 90, "instructions": "Review all incidents from current period for regulatory notification requirements. Confirm all required notifications were made.", "evidence_label": "Notification compliance review", "report_type": None},
        23: {"title": "Recovery testing", "duration_min": 90, "instructions": "Test recovery procedures from a simulated incident. Validate that backup/restore and failover procedures work as designed.", "evidence_label": "Recovery test results", "report_type": None},
        24: {"title": "IR evidence pack compilation", "duration_min": 90, "instructions": "Compile evidence package from all incidents in the current cycle: timelines, containment records, and resolution evidence.", "evidence_label": "IR evidence pack index", "report_type": "ir_evidence_pack"},
        25: {"title": "Incident response summary", "duration_min": 90, "instructions": "Generate incident response cycle summary: incident count, severity breakdown, MTTD/MTTR, lessons learned, and process improvements.", "evidence_label": "IR cycle summary", "report_type": "ir_summary"},
    },
    "bcdr_coordinator": {
        1:  {"title": "BCP/DRP currency check", "duration_min": 90, "instructions": "Verify BCP and DRP are current and reflect the system's current architecture. Flag sections that need updating.", "evidence_label": "Currency check notes", "report_type": None},
        2:  {"title": "Recovery objective verification", "duration_min": 90, "instructions": "Verify that current RTO/RPO objectives are still aligned with business requirements. Confirm system owner concurrence.", "evidence_label": "RTO/RPO verification notes", "report_type": None},
        3:  {"title": "Backup system health review", "duration_min": 90, "instructions": "Review backup system health: job status, storage capacity, retention compliance, and encryption verification.", "evidence_label": "Backup health review", "report_type": None},
        4:  {"title": "Recovery site readiness check", "duration_min": 90, "instructions": "Verify recovery site readiness. Confirm systems, network, and access are available for failover activation.", "evidence_label": "Recovery site readiness notes", "report_type": None},
        5:  {"title": "Personnel and contact list review", "duration_min": 90, "instructions": "Review BCDR personnel assignments and contact lists. Verify alternates are identified for all critical roles.", "evidence_label": "Contact list review", "report_type": None},
        6:  {"title": "Vendor and supplier BCDR review", "duration_min": 90, "instructions": "Review BCDR capabilities of critical vendors and suppliers. Obtain copies of vendor BCP/DRP as applicable.", "evidence_label": "Vendor BCDR review notes", "report_type": None},
        7:  {"title": "Communication plan test", "duration_min": 90, "instructions": "Test emergency communication plan: verify notification tree, out-of-band communication methods, and stakeholder contacts.", "evidence_label": "Communication plan test results", "report_type": None},
        8:  {"title": "Critical function prioritization review", "duration_min": 90, "instructions": "Review and confirm priority order for recovery of critical business functions. Confirm with system owner and business stakeholders.", "evidence_label": "Function prioritization review", "report_type": None},
        9:  {"title": "Restore test execution", "duration_min": 90, "instructions": "Execute restore test for critical data or system components. Document time-to-restore and data integrity results.", "evidence_label": "Restore test record", "report_type": None},
        10: {"title": "Lessons learned — recent events", "duration_min": 90, "instructions": "Review lessons learned from any recent BCDR activations or near-misses. Update plans accordingly.", "evidence_label": "Lessons learned notes", "report_type": None},
        11: {"title": "Training and awareness — BCDR roles", "duration_min": 90, "instructions": "Verify that all personnel with BCDR roles have completed required training. Identify gaps.", "evidence_label": "Training verification", "report_type": None},
        12: {"title": "Single point of failure analysis", "duration_min": 90, "instructions": "Analyze system architecture for single points of failure not covered by current BCDR plan. Recommend mitigations.", "evidence_label": "SPOF analysis notes", "report_type": None},
        13: {"title": "Tabletop exercise — full activation", "duration_min": 90, "instructions": "Conduct BCDR tabletop exercise simulating full plan activation. Walk through decision points and escalation.", "evidence_label": "Tabletop exercise summary", "report_type": None},
        14: {"title": "Mutual aid agreement review", "duration_min": 90, "instructions": "Review mutual aid agreements with partner organizations. Verify activation procedures and resource sharing terms are current.", "evidence_label": "Mutual aid review notes", "report_type": None},
        15: {"title": "Data replication verification", "duration_min": 90, "instructions": "Verify data replication to recovery site is current and within RPO. Review replication lag metrics.", "evidence_label": "Replication verification notes", "report_type": None},
        16: {"title": "Pandemic/remote operations planning review", "duration_min": 90, "instructions": "Review business continuity provisions for pandemic or remote-operations scenarios. Verify remote access capacity and security.", "evidence_label": "Remote operations review notes", "report_type": None},
        17: {"title": "Regulatory BCDR compliance review", "duration_min": 90, "instructions": "Review BCDR compliance against applicable regulations (HIPAA, FISMA, etc.). Document compliance status.", "evidence_label": "Regulatory BCDR compliance notes", "report_type": None},
        18: {"title": "Full-scale test planning", "duration_min": 90, "instructions": "Plan full-scale BCDR test. Define scope, success criteria, participants, and rollback procedures.", "evidence_label": "Full-scale test plan", "report_type": None},
        19: {"title": "Post-exercise improvement actions", "duration_min": 90, "instructions": "Track improvement actions from recent BCDR exercises. Update plans based on completed actions.", "evidence_label": "Improvement action tracker", "report_type": None},
        20: {"title": "Insurance and risk transfer review", "duration_min": 90, "instructions": "Review cyber insurance and other risk transfer mechanisms in context of current BCDR posture.", "evidence_label": "Risk transfer review notes", "report_type": None},
        21: {"title": "BCP/DRP update cycle", "duration_min": 90, "instructions": "Execute scheduled BCP/DRP update. Incorporate system changes, lessons learned, and new threats.", "evidence_label": "Updated plan version notes", "report_type": None},
        22: {"title": "Alternate processing site test", "duration_min": 90, "instructions": "Test operation from alternate processing site. Verify system functionality meets minimum operating requirements.", "evidence_label": "Alternate site test results", "report_type": None},
        23: {"title": "BCDR metrics review", "duration_min": 90, "instructions": "Review BCDR program metrics: test frequency, RTO/RPO achievement rates, plan update currency, training completion.", "evidence_label": "BCDR metrics report", "report_type": None},
        24: {"title": "BCDR evidence pack build", "duration_min": 90, "instructions": "Compile BCDR evidence pack: test results, restore records, plan versions, training records. Generate report.", "evidence_label": "BCDR evidence pack index", "report_type": "bcdr_evidence_pack"},
        25: {"title": "BCDR annual program review", "duration_min": 90, "instructions": "Conduct annual BCDR program review. Assess maturity, identify improvement priorities, and present findings to system owner.", "evidence_label": "Annual review summary", "report_type": "bcdr_annual_summary"},
    },
    "data_owner": {
        1:  {"title": "Data inventory review", "duration_min": 90, "instructions": "Review the data inventory for the system. Confirm all data elements, classifications, and custodians are current.", "evidence_label": "Data inventory review notes", "report_type": None},
        2:  {"title": "Data classification verification", "duration_min": 90, "instructions": "Verify data classification labels are applied consistently across system data stores. Flag misclassified data elements.", "evidence_label": "Classification verification notes", "report_type": None},
        3:  {"title": "Access rights review — data level", "duration_min": 90, "instructions": "Review user access rights at the data level. Confirm access is limited to minimum necessary for each role.", "evidence_label": "Data access review", "report_type": None},
        4:  {"title": "Data sharing agreement review", "duration_min": 90, "instructions": "Review data sharing agreements with external organizations. Verify terms, data use restrictions, and expiration dates.", "evidence_label": "DSA review notes", "report_type": None},
        5:  {"title": "ePHI access spot-check", "duration_min": 90, "instructions": "Spot-check ePHI access logs. Identify any access patterns that appear unusual or unauthorized.", "evidence_label": "ePHI access review notes", "report_type": None},
        6:  {"title": "Data retention compliance check", "duration_min": 90, "instructions": "Review data retention practices. Verify data is retained according to policy and no data is retained beyond its retention limit.", "evidence_label": "Retention compliance notes", "report_type": None},
        7:  {"title": "Data disposal review", "duration_min": 90, "instructions": "Review data disposal records. Verify media sanitation and data deletion procedures comply with NIST 800-88.", "evidence_label": "Disposal review notes", "report_type": None},
        8:  {"title": "Data quality review", "duration_min": 90, "instructions": "Review data quality for accuracy and completeness in critical data sets. Document quality issues affecting security decisions.", "evidence_label": "Data quality review notes", "report_type": None},
        9:  {"title": "Privacy threshold analysis review", "duration_min": 90, "instructions": "Review PTA for system. Confirm data elements triggering PIA requirement are documented and assessed.", "evidence_label": "PTA review notes", "report_type": None},
        10: {"title": "Data breach scenario review", "duration_min": 90, "instructions": "Review breach scenarios for sensitive data held by the system. Verify notification procedures are documented and tested.", "evidence_label": "Breach scenario review notes", "report_type": None},
        11: {"title": "Data lineage documentation review", "duration_min": 90, "instructions": "Review data lineage documentation. Verify source, transformation, and consumption points for critical data elements.", "evidence_label": "Data lineage review notes", "report_type": None},
        12: {"title": "Consent management review", "duration_min": 90, "instructions": "Review consent records for personal data collection. Verify consent is documented, current, and scope-appropriate.", "evidence_label": "Consent management review", "report_type": None},
        13: {"title": "BAA and data processing agreement audit", "duration_min": 90, "instructions": "Audit BAAs and data processing agreements. Verify all ePHI-handling vendors have current BAAs.", "evidence_label": "BAA audit results", "report_type": None},
        14: {"title": "Data access request review", "duration_min": 90, "instructions": "Review any data access requests from individuals (HIPAA right of access). Verify requests were handled within required timeframes.", "evidence_label": "Access request review", "report_type": None},
        15: {"title": "Data security control verification", "duration_min": 90, "instructions": "Verify data-level security controls: encryption at rest, access logging, masking in non-production environments.", "evidence_label": "Data security control verification", "report_type": None},
        16: {"title": "Secondary data use review", "duration_min": 90, "instructions": "Review any secondary uses of system data. Confirm each use is within authorized purposes and documented.", "evidence_label": "Secondary use review notes", "report_type": None},
        17: {"title": "Data custodian coordination", "duration_min": 90, "instructions": "Coordinate with data custodians to confirm operational controls are implemented. Address any custodian-reported issues.", "evidence_label": "Custodian coordination notes", "report_type": None},
        18: {"title": "Data risk assessment", "duration_min": 90, "instructions": "Assess risks to system data: unauthorized access, data corruption, availability loss. Update risk register entries.", "evidence_label": "Data risk assessment notes", "report_type": None},
        19: {"title": "Third-party data processing review", "duration_min": 90, "instructions": "Review how third parties process system data. Verify processing limitations in agreements are being honored.", "evidence_label": "Third-party processing review", "report_type": None},
        20: {"title": "Data flow mapping update", "duration_min": 90, "instructions": "Update data flow maps for the system. Document any new data flows identified since last review.", "evidence_label": "Data flow map updates", "report_type": None},
        21: {"title": "Regulatory data compliance review", "duration_min": 90, "instructions": "Review compliance with data-specific regulations (HIPAA Privacy Rule, state privacy laws). Document compliance status.", "evidence_label": "Regulatory compliance notes", "report_type": None},
        22: {"title": "Data stewardship program review", "duration_min": 90, "instructions": "Review data stewardship program effectiveness. Assess training, policy adherence, and issue resolution.", "evidence_label": "Stewardship program review", "report_type": None},
        23: {"title": "Data governance committee prep", "duration_min": 90, "instructions": "Prepare data governance committee materials: current issues, pending decisions, and metrics summary.", "evidence_label": "Committee briefing notes", "report_type": None},
        24: {"title": "Annual data protection report", "duration_min": 90, "instructions": "Compile annual data protection report: data inventory status, access review results, breach incidents, compliance status.", "evidence_label": "Annual protection report draft", "report_type": "data_protection_report"},
        25: {"title": "Data owner attestation", "duration_min": 90, "instructions": "Complete annual data owner attestation confirming data inventory accuracy, access appropriateness, and compliance status.", "evidence_label": "Signed attestation", "report_type": None},
    },
}

_REPORT_DIR = Path("data/reports")

# Shell role aliases → canonical rotation content keys
_ROTATION_CONTENT["bcdr"] = _ROTATION_CONTENT["bcdr_coordinator"]


def _p25_task_config(role: str) -> list:
    """Return task number list for the given role (defaults to isso)."""
    return ROLE_TASK_CONFIGS.get(role, ROLE_TASK_CONFIGS["isso"])


def _p25_rotation_content(role: str) -> dict:
    """Return 25-day rotation map for a role (fallback: isso)."""
    return _ROTATION_CONTENT.get(role, _ROTATION_CONTENT["isso"])


async def _p25_get_or_create_rotation(session, user: str, system_id: str, role: str) -> DeepWorkRotation:
    """Fetch or create the DeepWorkRotation record for this user/system/role."""
    row = (await session.execute(
        select(DeepWorkRotation)
        .where(DeepWorkRotation.remote_user == user)
        .where(DeepWorkRotation.system_id == system_id)
        .where(DeepWorkRotation.role_variant == role)
    )).scalar_one_or_none()
    if row is None:
        row = DeepWorkRotation(
            remote_user=user, system_id=system_id, role_variant=role, current_day=1)
        session.add(row)
        await session.flush()
    return row


async def _p25_daily_snapshot(session, system_id: str) -> dict:
    """Collect live metric counts for the daily logbook snapshot."""
    from sqlalchemy import func
    now_str = datetime.now(timezone.utc).isoformat()
    today   = date.today().isoformat()

    open_poams = (await session.execute(
        select(func.count(PoamItem.id))
        .where(PoamItem.system_id == system_id)
        .where(PoamItem.status.notin_(["closed", "false_positive", "not_applicable"]))
    )).scalar() or 0

    overdue_poams = (await session.execute(
        select(func.count(PoamItem.id))
        .where(PoamItem.system_id == system_id)
        .where(PoamItem.status.notin_(["closed", "false_positive", "not_applicable"]))
        .where(PoamItem.scheduled_completion < today)
    )).scalar() or 0

    open_risks = (await session.execute(
        select(func.count(Risk.id))
        .where(Risk.system_id == system_id)
        .where(Risk.status.notin_(["closed", "accepted"]))
    )).scalar() or 0

    open_obs = (await session.execute(
        select(func.count(Observation.id))
        .where(Observation.system_id == system_id)
        .where(Observation.status == "open")
    )).scalar() or 0

    open_incidents = (await session.execute(
        select(func.count(BcdrEvent.id))
        .where(BcdrEvent.system_id == system_id)
        .where(BcdrEvent.status == "open")
    )).scalar() or 0

    return {
        "snap_open_poams":    open_poams,
        "snap_overdue_poams": overdue_poams,
        "snap_open_risks":    open_risks,
        "snap_open_obs":      open_obs,
        "snap_open_incidents":open_incidents,
    }


async def _generate_system_report(report_id: int, system_id: str, report_type: str, user: str):
    """BackgroundTask: build a PDF report and update GeneratedReport row."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io

    try:
        async with SessionLocal() as s:
            sys_row = await s.get(System, system_id)
            if not sys_row:
                raise ValueError(f"System {system_id} not found")

            sysidx = (sys_row.abbreviation or system_id[:8]).upper()
            today  = date.today().strftime("%Y%m%d")
            fname  = f"{sysidx}.{report_type.upper()}.{today}.pdf"

            dest_dir = _REPORT_DIR / system_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / fname

            # ── Build PDF ─────────────────────────────────────────────────────
            buf  = io.BytesIO()
            doc  = SimpleDocTemplate(str(dest), pagesize=letter,
                                     leftMargin=inch, rightMargin=inch,
                                     topMargin=inch, bottomMargin=inch)
            styles = getSampleStyleSheet()
            RED    = colors.HexColor("#c41c1c")
            DARK   = colors.HexColor("#0d0d1a")
            CYAN   = colors.HexColor("#00bcd4")
            MUTED  = colors.HexColor("#7a7a9a")

            h1  = ParagraphStyle("h1",  parent=styles["Heading1"],
                                 fontSize=18, textColor=RED, spaceAfter=6)
            h2  = ParagraphStyle("h2",  parent=styles["Heading2"],
                                 fontSize=13, textColor=CYAN, spaceAfter=4)
            bod = ParagraphStyle("bod", parent=styles["Normal"],
                                 fontSize=10, leading=14, textColor=DARK)
            mut = ParagraphStyle("mut", parent=styles["Normal"],
                                 fontSize=9, textColor=MUTED)

            story = []

            def _add_section(title, rows):
                story.append(Paragraph(title, h2))
                story.append(Spacer(1, 4))
                tbl = Table(rows, colWidths=[2*inch, 4.5*inch])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1e1e30")),
                    ("TEXTCOLOR",   (0,0), (-1,0), CYAN),
                    ("FONTSIZE",    (0,0), (-1,-1), 9),
                    ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#2a2a40")),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1),
                     [colors.HexColor("#f8f8ff"), colors.HexColor("#eef0f4")]),
                    ("VALIGN",      (0,0), (-1,-1), "TOP"),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 12))

            # Cover
            story.append(Paragraph("BLACKSITE", h1))
            story.append(Paragraph(f"System: {sys_row.name} ({sysidx})", bod))
            story.append(Paragraph(f"Report: {report_type.replace('_',' ').title()}", bod))
            story.append(Paragraph(f"Generated: {date.today().isoformat()}  |  By: {user}", mut))
            story.append(HRFlowable(width="100%", thickness=1, color=RED, spaceAfter=12))

            # System overview section
            impact = f"C:{sys_row.confidentiality_impact or '—'} / I:{sys_row.integrity_impact or '—'} / A:{sys_row.availability_impact or '—'}"
            _add_section("System Overview", [
                ["Field", "Value"],
                ["System Name", sys_row.name or "—"],
                ["Abbreviation", sysidx],
                ["Impact Level", sys_row.overall_impact or "—"],
                ["FIPS 199", impact],
                ["ATO Status", sys_row.ato_decision or "Not Authorized"],
                ["Description", (sys_row.description or "")[:300]],
            ])

            # Report-type-specific data
            async with SessionLocal() as s2:
                if report_type == "executive_summary":
                    snap = await _p25_daily_snapshot(s2, system_id)
                    _add_section("Security Posture Snapshot", [
                        ["Metric", "Count"],
                        ["Open POA&Ms",    str(snap["snap_open_poams"])],
                        ["Overdue POA&Ms", str(snap["snap_overdue_poams"])],
                        ["Open Risks",     str(snap["snap_open_risks"])],
                        ["Open Observations", str(snap["snap_open_obs"])],
                        ["Open Incidents", str(snap["snap_open_incidents"])],
                    ])

                elif report_type in ("evidence_pack_controls", "sca_evidence_pack"):
                    arts = (await s2.execute(
                        select(Artifact).where(Artifact.system_id == system_id)
                        .where(Artifact.approval_status == "approved")
                        .limit(50)
                    )).scalars().all()
                    rows = [["Control", "Artifact", "Owner", "Status"]]
                    for a in arts:
                        rows.append([a.control_id or "—", a.title[:50], a.owner or "—", a.approval_status])
                    if len(rows) > 1:
                        _add_section("Approved Artifacts", rows)

                elif report_type in ("bcdr_evidence_pack", "bcdr_annual_summary"):
                    recs = (await s2.execute(
                        select(RestoreTestRecord).where(RestoreTestRecord.system_id == system_id)
                        .order_by(RestoreTestRecord.test_date.desc()).limit(20)
                    )).scalars().all()
                    rows = [["Test Date", "Scope", "Result", "RTO (min)"]]
                    for r in recs:
                        rows.append([r.test_date, (r.scope or "")[:40], r.result,
                                     str(r.time_to_restore_min or "—")])
                    if len(rows) > 1:
                        _add_section("Restore Test Records", rows)

                elif report_type == "ir_evidence_pack":
                    story.append(Paragraph(
                        "Incident Response evidence pack includes all open and recently closed "
                        "incidents and their associated timelines.", bod))
                    story.append(Spacer(1, 8))

            doc.build(story)
            fsize = dest.stat().st_size

        async with SessionLocal() as s:
            rpt = await s.get(GeneratedReport, report_id)
            if rpt:
                rpt.status       = "ready"
                rpt.filename     = fname
                rpt.file_path    = str(dest)
                rpt.file_size    = fsize
                rpt.generated_at = datetime.now(timezone.utc)
                await s.commit()

    except Exception as exc:
        log.exception("Report generation failed report_id=%s: %s", report_id, exc)
        async with SessionLocal() as s:
            rpt = await s.get(GeneratedReport, report_id)
            if rpt:
                rpt.status    = "error"
                rpt.error_msg = str(exc)
                await s.commit()



# ── Phase 25 Routes: Daily Hub ─────────────────────────────────────────────────

@app.get("/systems/{system_id}/daily", response_class=HTMLResponse)
async def system_daily_hub(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        role   = await _get_user_role(request, session)
        sys_r  = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        today  = date.today().isoformat()
        task_nums = _p25_task_config(role)

        # Today's logbook (if exists)
        lb = (await session.execute(
            select(DailyLogbook)
            .where(DailyLogbook.remote_user == user)
            .where(DailyLogbook.system_id == system_id)
            .where(DailyLogbook.log_date == today)
        )).scalar_one_or_none()

        flags = json.loads(lb.task_flags) if (lb and lb.task_flags) else {}
        completed_today = sum(1 for k in [str(t) for t in task_nums] if flags.get(k))

        # Rotation state
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)
        await session.commit()

        rot_content = _p25_rotation_content(role)
        today_rot   = rot_content.get(rotation.current_day, {})
        is_holiday  = date.today() in FEDERAL_HOLIDAYS_2026

        snap = await _p25_daily_snapshot(session, system_id)
        ctx  = await _full_ctx(request, session,
            system=sys_r,
            today=today,
            task_nums=task_nums,
            task_labels=_TASK_LABELS,
            task_flags=flags,
            completed_today=completed_today,
            logbook=lb,
            rotation=rotation,
            today_rot=today_rot,
            is_holiday=is_holiday,
            **snap,
        )
    return templates.TemplateResponse("system_daily.html", ctx)


@app.post("/systems/{system_id}/daily/save")
async def system_daily_save(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        role      = await _get_user_role(request, session)
        task_nums = _p25_task_config(role)
        today     = date.today().isoformat()
        flags     = {str(t): (form.get(f"task_{t}") == "on") for t in task_nums}
        notes     = form.get("notes", "").strip()
        snap      = await _p25_daily_snapshot(session, system_id)

        lb = (await session.execute(
            select(DailyLogbook)
            .where(DailyLogbook.remote_user == user)
            .where(DailyLogbook.system_id == system_id)
            .where(DailyLogbook.log_date == today)
        )).scalar_one_or_none()

        if lb:
            lb.task_flags         = json.dumps(flags)
            lb.notes              = notes
            lb.snap_open_poams    = snap["snap_open_poams"]
            lb.snap_overdue_poams = snap["snap_overdue_poams"]
            lb.snap_open_risks    = snap["snap_open_risks"]
            lb.snap_open_obs      = snap["snap_open_obs"]
            lb.snap_open_incidents= snap["snap_open_incidents"]
        else:
            lb = DailyLogbook(
                remote_user=user, system_id=system_id, log_date=today,
                task_flags=json.dumps(flags), notes=notes, **snap)
            session.add(lb)

        await _log_audit(session, user, "UPDATE", "daily_logbook", system_id,
                         {"log_date": today, "flags": flags})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/daily", status_code=303)


@app.get("/systems/{system_id}/daily/history", response_class=HTMLResponse)
async def system_daily_history(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        role = await _get_user_role(request, session)
        rows = (await session.execute(
            select(DailyLogbook)
            .where(DailyLogbook.remote_user == user)
            .where(DailyLogbook.system_id == system_id)
            .order_by(DailyLogbook.log_date.desc())
            .limit(30)
        )).scalars().all()
        task_nums = _p25_task_config(role)
        ctx = await _full_ctx(request, session,
            system=sys_r, logbooks=rows,
            task_nums=task_nums, task_labels=_TASK_LABELS)
    return templates.TemplateResponse("system_daily_history.html", ctx)


@app.get("/systems/{system_id}/daily/logbook/{log_date}", response_class=HTMLResponse)
async def system_daily_logbook_view(request: Request, system_id: str, log_date: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        role = await _get_user_role(request, session)
        lb = (await session.execute(
            select(DailyLogbook)
            .where(DailyLogbook.remote_user == user)
            .where(DailyLogbook.system_id == system_id)
            .where(DailyLogbook.log_date == log_date)
        )).scalar_one_or_none()
        if not lb:
            raise HTTPException(404)
        flags     = json.loads(lb.task_flags) if lb.task_flags else {}
        task_nums = _p25_task_config(role)
        ctx = await _full_ctx(request, session,
            system=sys_r, logbook=lb, flags=flags,
            task_nums=task_nums, task_labels=_TASK_LABELS, log_date=log_date)
    return templates.TemplateResponse("system_daily_logbook.html", ctx)



# ── Phase 25 Routes: Task Sub-forms ───────────────────────────────────────────

@app.get("/systems/{system_id}/daily/change-review", response_class=HTMLResponse)
async def system_change_review_get(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        today = date.today().isoformat()
        existing = (await session.execute(
            select(ChangeReviewRecord)
            .where(ChangeReviewRecord.remote_user == user)
            .where(ChangeReviewRecord.system_id == system_id)
            .where(ChangeReviewRecord.review_date == today)
        )).scalar_one_or_none()
        ctx = await _full_ctx(request, session,
            system=sys_r, today=today, existing=existing)
    return templates.TemplateResponse("system_daily_change_review.html", ctx)


@app.post("/systems/{system_id}/daily/change-review")
async def system_change_review_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        today = date.today().isoformat()
        rec = ChangeReviewRecord(
            remote_user     = user,
            system_id       = system_id,
            review_date     = today,
            ticket_refs     = form.get("ticket_refs", ""),
            high_risk_count = int(form.get("high_risk_count", 0) or 0),
            all_approved    = form.get("all_approved") == "on",
            backout_exists  = form.get("backout_exists") == "on",
            untracked_found = form.get("untracked_found") == "on",
            notes           = form.get("notes", ""),
        )
        session.add(rec)
        await _log_audit(session, user, "CREATE", "change_review_record", system_id,
                         {"date": today})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/daily", status_code=303)


@app.get("/systems/{system_id}/daily/backup-check", response_class=HTMLResponse)
async def system_backup_check_get(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        today = date.today().isoformat()
        existing = (await session.execute(
            select(BackupCheckRecord)
            .where(BackupCheckRecord.remote_user == user)
            .where(BackupCheckRecord.system_id == system_id)
            .where(BackupCheckRecord.check_date == today)
        )).scalar_one_or_none()
        ctx = await _full_ctx(request, session,
            system=sys_r, today=today, existing=existing)
    return templates.TemplateResponse("system_daily_backup_check.html", ctx)


@app.post("/systems/{system_id}/daily/backup-check")
async def system_backup_check_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        today = date.today().isoformat()
        # Upsert — one record per user/system/day
        existing = (await session.execute(
            select(BackupCheckRecord)
            .where(BackupCheckRecord.remote_user == user)
            .where(BackupCheckRecord.system_id == system_id)
            .where(BackupCheckRecord.check_date == today)
        )).scalar_one_or_none()
        if existing:
            existing.result       = form.get("result", "pass")
            existing.ephi_systems = form.get("ephi_systems", "")
            existing.job_health   = form.get("job_health", "ok")
            existing.issue_raised = form.get("issue_raised") == "on"
            existing.notes        = form.get("notes", "")
        else:
            rec = BackupCheckRecord(
                remote_user  = user,
                system_id    = system_id,
                check_date   = today,
                result       = form.get("result", "pass"),
                ephi_systems = form.get("ephi_systems", ""),
                job_health   = form.get("job_health", "ok"),
                issue_raised = form.get("issue_raised") == "on",
                notes        = form.get("notes", ""),
            )
            session.add(rec)
        await _log_audit(session, user, "CREATE", "backup_check_record", system_id,
                         {"date": today, "result": form.get("result")})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/daily", status_code=303)


@app.get("/systems/{system_id}/daily/access-spotcheck", response_class=HTMLResponse)
async def system_access_spotcheck_get(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        today = date.today().isoformat()
        existing = (await session.execute(
            select(AccessSpotCheck)
            .where(AccessSpotCheck.remote_user == user)
            .where(AccessSpotCheck.system_id == system_id)
            .where(AccessSpotCheck.check_date == today)
        )).scalar_one_or_none()
        ctx = await _full_ctx(request, session,
            system=sys_r, today=today, existing=existing)
    return templates.TemplateResponse("system_daily_access_spotcheck.html", ctx)


@app.post("/systems/{system_id}/daily/access-spotcheck")
async def system_access_spotcheck_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        today = date.today().isoformat()
        existing = (await session.execute(
            select(AccessSpotCheck)
            .where(AccessSpotCheck.remote_user == user)
            .where(AccessSpotCheck.system_id == system_id)
            .where(AccessSpotCheck.check_date == today)
        )).scalar_one_or_none()
        vals = dict(
            records_sampled       = int(form.get("records_sampled", 0) or 0),
            anomaly_found         = form.get("anomaly_found") == "on",
            terminated_user_found = form.get("terminated_user_found") == "on",
            anomaly_description   = form.get("anomaly_description", ""),
            notes                 = form.get("notes", ""),
        )
        if existing:
            for k, v in vals.items():
                setattr(existing, k, v)
        else:
            session.add(AccessSpotCheck(
                remote_user=user, system_id=system_id, check_date=today, **vals))
        await _log_audit(session, user, "CREATE", "access_spot_check", system_id,
                         {"date": today})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/daily", status_code=303)



# ── Phase 25 Routes: Rotation Engine ──────────────────────────────────────────

@app.get("/systems/{system_id}/rotation", response_class=HTMLResponse)
async def system_rotation(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        role     = await _get_user_role(request, session)
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)
        await session.commit()
        rot_content  = _p25_rotation_content(role)
        current_item = rot_content.get(rotation.current_day, {})
        is_holiday   = date.today() in FEDERAL_HOLIDAYS_2026
        ctx = await _full_ctx(request, session,
            system=sys_r, rotation=rotation,
            current_item=current_item, is_holiday=is_holiday,
            today=date.today().isoformat())
    return templates.TemplateResponse("system_rotation.html", ctx)


@app.post("/systems/{system_id}/rotation/complete")
async def system_rotation_complete(request: Request, system_id: str,
                                    background_tasks: BackgroundTasks):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        role     = await _get_user_role(request, session)
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)

        if rotation.paused:
            raise HTTPException(400, "Rotation is paused")

        today        = date.today().isoformat()
        current_day  = rotation.current_day
        rot_content  = _p25_rotation_content(role)
        item         = rot_content.get(current_day, {})
        report_type  = item.get("report_type")

        # Save completion record
        comp = DeepWorkCompletion(
            rotation_id    = rotation.id,
            remote_user    = user,
            system_id      = system_id,
            rotation_day   = current_day,
            completed_date = today,
            notes          = form.get("notes", ""),
            evidence_name  = form.get("evidence_name", ""),
        )
        session.add(comp)

        # Advance rotation day (wrap 25 → 1)
        rotation.current_day   = (current_day % 25) + 1
        rotation.last_work_date = today

        # Trigger background report if this day has one
        if report_type:
            sys_row = await session.get(System, system_id)
            rpt = GeneratedReport(
                system_id   = system_id,
                remote_user = user,
                report_type = report_type,
                status      = "generating",
            )
            session.add(rpt)
            await session.flush()
            background_tasks.add_task(_generate_system_report,
                                       rpt.id, system_id, report_type, user)

        await _log_audit(session, user, "CREATE", "deep_work_completion", system_id,
                         {"day": current_day, "role": role})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/rotation", status_code=303)


@app.post("/systems/{system_id}/rotation/pause")
async def system_rotation_pause(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        role     = await _get_user_role(request, session)
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)
        rotation.paused = True
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/rotation", status_code=303)


@app.post("/systems/{system_id}/rotation/resume")
async def system_rotation_resume(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        role     = await _get_user_role(request, session)
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)
        rotation.paused = False
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/rotation", status_code=303)


@app.get("/systems/{system_id}/rotation/history", response_class=HTMLResponse)
async def system_rotation_history(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        role     = await _get_user_role(request, session)
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)
        await session.commit()
        completions = (await session.execute(
            select(DeepWorkCompletion)
            .where(DeepWorkCompletion.rotation_id == rotation.id)
            .order_by(DeepWorkCompletion.completed_date.desc())
            .limit(100)
        )).scalars().all()
        rot_content = _p25_rotation_content(role)
        ctx = await _full_ctx(request, session,
            system=sys_r, rotation=rotation,
            completions=completions, rot_content=rot_content)
    return templates.TemplateResponse("system_rotation_history.html", ctx)


@app.get("/systems/{system_id}/rotation/calendar", response_class=HTMLResponse)
async def system_rotation_calendar(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        role     = await _get_user_role(request, session)
        rotation = await _p25_get_or_create_rotation(session, user, system_id, role)
        await session.commit()
        completions = (await session.execute(
            select(DeepWorkCompletion)
            .where(DeepWorkCompletion.rotation_id == rotation.id)
            .order_by(DeepWorkCompletion.completed_date.desc())
            .limit(200)
        )).scalars().all()
        # Build day→last_completed_date map
        day_map = {}
        for c in completions:
            if c.rotation_day not in day_map:
                day_map[c.rotation_day] = c.completed_date
        rot_content = _p25_rotation_content(role)
        holidays    = [d.isoformat() for d in FEDERAL_HOLIDAYS_2026]
        ctx = await _full_ctx(request, session,
            system=sys_r, rotation=rotation,
            rot_content=rot_content, day_map=day_map,
            holidays=holidays)
    return templates.TemplateResponse("system_rotation_calendar.html", ctx)



# ── Phase 25 Routes: Compliance Records ───────────────────────────────────────

@app.get("/systems/{system_id}/vendors", response_class=HTMLResponse)
async def system_vendors(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        vendors = (await session.execute(
            select(Vendor).where(Vendor.system_id == system_id)
            .order_by(Vendor.name)
        )).scalars().all()
        today = date.today().isoformat()
        ctx = await _full_ctx(request, session,
            system=sys_r, vendors=vendors, today=today)
    return templates.TemplateResponse("system_vendors.html", ctx)


@app.post("/systems/{system_id}/vendors")
async def system_vendors_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        v = Vendor(
            system_id     = system_id,
            name          = form.get("name", "").strip(),
            service_type  = form.get("service_type", "other"),
            handles_ephi  = form.get("handles_ephi") == "on",
            has_baa       = form.get("has_baa") == "on",
            baa_expiry    = form.get("baa_expiry") or None,
            contact_name  = form.get("contact_name", ""),
            contact_email = form.get("contact_email", ""),
            status        = form.get("status", "active"),
            notes         = form.get("notes", ""),
            created_by    = user,
        )
        session.add(v)
        await _log_audit(session, user, "CREATE", "vendor", system_id,
                         {"name": v.name})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/vendors", status_code=303)


@app.post("/systems/{system_id}/vendors/{vid}")
async def system_vendor_update(request: Request, system_id: str, vid: int):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        v = await session.get(Vendor, vid)
        if not v or v.system_id != system_id:
            raise HTTPException(404)
        v.name          = form.get("name", v.name).strip()
        v.service_type  = form.get("service_type", v.service_type)
        v.handles_ephi  = form.get("handles_ephi") == "on"
        v.has_baa       = form.get("has_baa") == "on"
        v.baa_expiry    = form.get("baa_expiry") or None
        v.contact_name  = form.get("contact_name", v.contact_name)
        v.contact_email = form.get("contact_email", v.contact_email)
        v.status        = form.get("status", v.status)
        v.notes         = form.get("notes", v.notes)
        await _log_audit(session, user, "UPDATE", "vendor", str(vid), {"name": v.name})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/vendors", status_code=303)


@app.get("/systems/{system_id}/interconnections", response_class=HTMLResponse)
async def system_interconnections(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        recs = (await session.execute(
            select(InterconnectionRecord).where(InterconnectionRecord.system_id == system_id)
            .order_by(InterconnectionRecord.partner_name)
        )).scalars().all()
        ctx = await _full_ctx(request, session, system=sys_r, records=recs,
                               today=date.today().isoformat())
    return templates.TemplateResponse("system_interconnections.html", ctx)


@app.post("/systems/{system_id}/interconnections")
async def system_interconnections_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        rec = InterconnectionRecord(
            system_id            = system_id,
            partner_name         = form.get("partner_name", "").strip(),
            data_types           = form.get("data_types", ""),
            isa_exists           = form.get("isa_exists") == "on",
            isa_expiry           = form.get("isa_expiry") or None,
            monitoring_confirmed = form.get("monitoring_confirmed") == "on",
            encrypted_in_transit = form.get("encrypted_in_transit") == "on",
            auth_method          = form.get("auth_method", ""),
            notes                = form.get("notes", ""),
            last_reviewed        = date.today().isoformat(),
            reviewed_by          = user,
        )
        session.add(rec)
        await _log_audit(session, user, "CREATE", "interconnection_record", system_id,
                         {"partner": rec.partner_name})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/interconnections", status_code=303)


@app.get("/systems/{system_id}/dataflows", response_class=HTMLResponse)
async def system_dataflows(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        recs = (await session.execute(
            select(DataFlowRecord).where(DataFlowRecord.system_id == system_id)
            .order_by(DataFlowRecord.integration_name)
        )).scalars().all()
        ctx = await _full_ctx(request, session, system=sys_r, records=recs,
                               today=date.today().isoformat())
    return templates.TemplateResponse("system_dataflows.html", ctx)


@app.post("/systems/{system_id}/dataflows")
async def system_dataflows_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        rec = DataFlowRecord(
            system_id            = system_id,
            integration_name     = form.get("integration_name", "").strip(),
            auth_method          = form.get("auth_method", ""),
            encrypted_in_transit = form.get("encrypted_in_transit") == "on",
            encrypted_at_rest    = form.get("encrypted_at_rest") == "on",
            logging_confirmed    = form.get("logging_confirmed") == "on",
            termination_steps    = form.get("termination_steps", ""),
            data_types           = form.get("data_types", ""),
            notes                = form.get("notes", ""),
            last_reviewed        = date.today().isoformat(),
            reviewed_by          = user,
        )
        session.add(rec)
        await _log_audit(session, user, "CREATE", "data_flow_record", system_id,
                         {"integration": rec.integration_name})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/dataflows", status_code=303)


@app.get("/systems/{system_id}/privacy-assessments", response_class=HTMLResponse)
async def system_privacy_assessments(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        recs = (await session.execute(
            select(PrivacyAssessment).where(PrivacyAssessment.system_id == system_id)
            .order_by(PrivacyAssessment.created_at.desc())
        )).scalars().all()
        ctx = await _full_ctx(request, session, system=sys_r, records=recs,
                               today=date.today().isoformat())
    return templates.TemplateResponse("system_privacy_assessments.html", ctx)


@app.post("/systems/{system_id}/privacy-assessments")
async def system_privacy_assessments_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        rec = PrivacyAssessment(
            system_id        = system_id,
            assess_type      = form.get("assess_type", "pta"),
            data_elements    = form.get("data_elements", ""),
            purpose          = form.get("purpose", ""),
            disclosures      = form.get("disclosures", ""),
            retention_policy = form.get("retention_policy", ""),
            access_controls  = form.get("access_controls", ""),
            last_reviewed    = date.today().isoformat(),
            reviewer         = user,
            status           = form.get("status", "draft"),
            notes            = form.get("notes", ""),
        )
        session.add(rec)
        await _log_audit(session, user, "CREATE", "privacy_assessment", system_id,
                         {"type": rec.assess_type})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/privacy-assessments", status_code=303)


@app.get("/systems/{system_id}/restore-tests", response_class=HTMLResponse)
async def system_restore_tests(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        recs = (await session.execute(
            select(RestoreTestRecord).where(RestoreTestRecord.system_id == system_id)
            .order_by(RestoreTestRecord.test_date.desc())
        )).scalars().all()
        ctx = await _full_ctx(request, session, system=sys_r, records=recs,
                               today=date.today().isoformat())
    return templates.TemplateResponse("system_restore_tests.html", ctx)


@app.post("/systems/{system_id}/restore-tests")
async def system_restore_tests_post(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        rto = form.get("time_to_restore_min")
        rec = RestoreTestRecord(
            system_id           = system_id,
            test_date           = form.get("test_date", date.today().isoformat()),
            scope               = form.get("scope", ""),
            result              = form.get("result", "pass"),
            time_to_restore_min = int(rto) if rto else None,
            validated_by        = form.get("validated_by", user),
            notes               = form.get("notes", ""),
            created_by          = user,
        )
        session.add(rec)
        await _log_audit(session, user, "CREATE", "restore_test_record", system_id,
                         {"date": rec.test_date, "result": rec.result})
        await session.commit()
    return RedirectResponse(f"/systems/{system_id}/restore-tests", status_code=303)



# ── Phase 25 Routes: Reports ───────────────────────────────────────────────────

@app.get("/systems/{system_id}/reports", response_class=HTMLResponse)
async def system_reports(request: Request, system_id: str):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        sys_r = await session.get(System, system_id)
        if not sys_r or sys_r.deleted_at:
            raise HTTPException(404)
        rpts = (await session.execute(
            select(GeneratedReport).where(GeneratedReport.system_id == system_id)
            .order_by(GeneratedReport.created_at.desc()).limit(50)
        )).scalars().all()
        ctx = await _full_ctx(request, session, system=sys_r, reports=rpts)
    return templates.TemplateResponse("system_reports.html", ctx)


@app.post("/systems/{system_id}/reports/generate")
async def system_reports_generate(request: Request, system_id: str,
                                   background_tasks: BackgroundTasks):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    form = await request.form()
    report_type = form.get("report_type", "executive_summary")
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        rpt = GeneratedReport(
            system_id   = system_id,
            remote_user = user,
            report_type = report_type,
            status      = "generating",
        )
        session.add(rpt)
        await session.flush()
        rpt_id = rpt.id
        await _log_audit(session, user, "CREATE", "generated_report", system_id,
                         {"type": report_type})
        await session.commit()
    background_tasks.add_task(_generate_system_report, rpt_id, system_id, report_type, user)
    return RedirectResponse(f"/systems/{system_id}/reports", status_code=303)


@app.get("/systems/{system_id}/reports/{rid}/download")
async def system_report_download(request: Request, system_id: str, rid: int):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    from fastapi.responses import FileResponse
    async with SessionLocal() as session:
        if not await _can_access_system(system_id, request, session):
            raise HTTPException(403)
        rpt = await session.get(GeneratedReport, rid)
        if not rpt or rpt.system_id != system_id or rpt.status != "ready":
            raise HTTPException(404)
        fpath = Path(rpt.file_path)
        if not fpath.exists():
            raise HTTPException(404, "Report file missing")
        await _log_audit(session, user, "DOWNLOAD", "generated_report", str(rid), {})
        await session.commit()
    return FileResponse(
        path=str(fpath),
        filename=rpt.filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{rpt.filename}"'},
    )


# ── Phase 25 Routes: ISSM Portfolio Roll-up ───────────────────────────────────

@app.get("/issm/daily", response_class=HTMLResponse)
async def issm_daily_portfolio(request: Request):
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(401)
    async with SessionLocal() as session:
        role = await _get_user_role(request, session)
        if role not in ("issm", "admin", "ao", "ciso"):
            raise HTTPException(403)

        today = date.today().isoformat()
        from sqlalchemy import func

        # All systems user can access
        sys_ids = await _user_system_ids(request, session)
        systems_rows = (await session.execute(
            select(System)
            .where(System.id.in_(sys_ids))
            .where(System.deleted_at.is_(None))
            .order_by(System.name)
        )).scalars().all()

        portfolio = []
        for sys_r in systems_rows:
            sid = sys_r.id

            # Find the ISSO assigned to this system (program_role = 'isso')
            isso_row = (await session.execute(
                select(ProgramRoleAssignment)
                .where(ProgramRoleAssignment.system_id == sid)
                .where(ProgramRoleAssignment.program_role == "isso")
                .where(ProgramRoleAssignment.status == "active")
                .limit(1)
            )).scalar_one_or_none()
            isso_user = isso_row.remote_user if isso_row else None

            # Today's logbook for ISSO (if exists)
            lb = None
            if isso_user:
                lb = (await session.execute(
                    select(DailyLogbook)
                    .where(DailyLogbook.remote_user == isso_user)
                    .where(DailyLogbook.system_id == sid)
                    .where(DailyLogbook.log_date == today)
                )).scalar_one_or_none()

            isso_flags   = json.loads(lb.task_flags) if (lb and lb.task_flags) else {}
            isso_task_ct = len(ROLE_TASK_CONFIGS.get("isso", []))
            isso_done_ct = sum(1 for v in isso_flags.values() if v)

            # ISSO rotation
            isso_rotation = None
            if isso_user:
                isso_rotation = (await session.execute(
                    select(DeepWorkRotation)
                    .where(DeepWorkRotation.remote_user == isso_user)
                    .where(DeepWorkRotation.system_id == sid)
                    .where(DeepWorkRotation.role_variant == "isso")
                )).scalar_one_or_none()

            # Overdue POA&Ms
            overdue = (await session.execute(
                select(func.count(PoamItem.id))
                .where(PoamItem.system_id == sid)
                .where(PoamItem.status.notin_(["closed", "false_positive", "not_applicable"]))
                .where(PoamItem.scheduled_completion < today)
            )).scalar() or 0

            open_poams = (await session.execute(
                select(func.count(PoamItem.id))
                .where(PoamItem.system_id == sid)
                .where(PoamItem.status.notin_(["closed", "false_positive", "not_applicable"]))
            )).scalar() or 0

            portfolio.append({
                "system":         sys_r,
                "isso_user":      isso_user,
                "tasks_done":     isso_done_ct,
                "tasks_total":    isso_task_ct,
                "logbook_today":  lb is not None,
                "overdue_poams":  overdue,
                "open_poams":     open_poams,
                "rotation":       isso_rotation,
                "ato_status":     sys_r.ato_decision or "Not Authorized",
            })

        ctx = await _full_ctx(request, session,
            portfolio=portfolio, today=today)
    return templates.TemplateResponse("issm_daily_portfolio.html", ctx)

