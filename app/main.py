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
import os
import random
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
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
from sqlalchemy import func, select, update, text

from app.models import (
    Assessment, Candidate, ControlResult, ControlsMeta, DailyQuizActivity, QuizResponse,
    System, PoamItem, Risk, UserProfile, AuditLog, SystemAssignment, ControlEdit,
    SystemControl, Submission,
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
    return {
        "app_name":    _cfg("app.name", "BLACKSITE"),
        "brand":       _cfg("app.brand", "TheKramerica"),
        "tagline":     _cfg("app.tagline", "Security Assessment Platform"),
        "remote_user": user,
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
async def admin_audit(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403)

    async with SessionLocal() as session:
        rows = await session.execute(
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(200)
        )
        entries = rows.scalars().all()

    return templates.TemplateResponse("audit_log.html", {
        "request": request,
        "entries": entries,
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
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    today_str = date.today().isoformat()
    week_str  = (date.today() + timedelta(days=7)).isoformat()
    month_ago = (date.today() - timedelta(days=30)).isoformat()

    async with SessionLocal() as session:
        rows = await session.execute(
            select(PoamItem).order_by(PoamItem.severity, PoamItem.scheduled_completion)
        )
        all_items = rows.scalars().all()

        # Load linked systems for display
        sys_ids = {p.system_id for p in all_items if p.system_id}
        systems_map = {}
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(list(sys_ids)))
            )
            systems_map = {s.id: s for s in sys_rows.scalars().all()}

    open_items   = [p for p in all_items if p.status in ("open","in_progress")]
    crit_high    = [p for p in open_items if p.severity in ("Critical","High")]
    overdue      = [p for p in open_items if p.scheduled_completion and p.scheduled_completion < today_str]
    due_soon     = [p for p in open_items if p.scheduled_completion and today_str <= p.scheduled_completion <= week_str]
    closed_month = [p for p in all_items if p.status == "closed" and p.completion_date and p.completion_date >= month_ago]

    sev_counts = {
        "Critical": sum(1 for p in open_items if p.severity == "Critical"),
        "High":     sum(1 for p in open_items if p.severity == "High"),
        "Moderate": sum(1 for p in open_items if p.severity == "Moderate"),
        "Low":      sum(1 for p in open_items if p.severity == "Low"),
    }

    # Aging buckets
    aging = {"0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0}
    today_dt = date.today()
    for p in open_items:
        if p.created_at:
            age = (today_dt - p.created_at.date()).days
        else:
            age = 0
        if age <= 30:
            aging["0_30"] += 1
        elif age <= 60:
            aging["31_60"] += 1
        elif age <= 90:
            aging["61_90"] += 1
        else:
            aging["90_plus"] += 1

    return templates.TemplateResponse("poam.html", {
        "request":      request,
        "all_items":    all_items,
        "open_items":   open_items,
        "crit_high":    crit_high,
        "overdue":      overdue,
        "due_soon":     due_soon,
        "closed_month": closed_month,
        "sev_counts":   sev_counts,
        "aging":        aging,
        "systems_map":  systems_map,
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
    user = request.headers.get("Remote-User", "")
    if not user:
        raise HTTPException(status_code=401)

    async with SessionLocal() as session:
        rows = await session.execute(
            select(Risk).order_by(Risk.risk_score.desc())
        )
        risks = rows.scalars().all()

        sys_ids = {r.system_id for r in risks if r.system_id}
        systems_map = {}
        if sys_ids:
            sys_rows = await session.execute(
                select(System).where(System.id.in_(list(sys_ids)))
            )
            systems_map = {s.id: s for s in sys_rows.scalars().all()}

    # Build 5×5 heat matrix
    matrix = [[0]*5 for _ in range(5)]
    for r in risks:
        if r.status != "closed":
            li = max(0, min(4, (r.likelihood or 1) - 1))
            im = max(0, min(4, (r.impact or 1) - 1))
            matrix[4 - li][im] += 1

    return templates.TemplateResponse("risks.html", {
        "request":     request,
        "risks":       risks,
        "systems_map": systems_map,
        "matrix":      matrix,
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

        # Other systems for inheritance dropdown
        other_sys_rows = await session.execute(
            select(System).where(System.id != system_id).order_by(System.name)
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
