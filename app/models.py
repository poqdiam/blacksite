"""
BLACKSITE — Database models (SQLAlchemy + SQLite)
"""
from __future__ import annotations

# ── SQLCipher early patch ──────────────────────────────────────────────────────
# Must run BEFORE any import that transitively imports sqlite3 (aiosqlite,
# sqlalchemy aiosqlite dialect).  When BLACKSITE_DB_KEY is set, pysqlcipher3
# replaces stdlib sqlite3 so every subsequent sqlite3.connect() call goes
# through SQLCipher.  The PRAGMA key is applied via the connect event in
# _configure_sqlite().
import os as _os
_BLACKSITE_DB_KEY_EARLY = _os.environ.get("BLACKSITE_DB_KEY", "")
if _BLACKSITE_DB_KEY_EARLY:
    try:
        from pysqlcipher3 import dbapi2 as _pysqlcipher3_mod
        import sys as _sys

        # pysqlcipher3 1.2.0 is a C extension built against SQLCipher 3.4.x.
        # It doesn't support the `deterministic` kwarg added to create_function
        # in Python 3.8 sqlite3.  Since Connection is a C type we can't patch
        # it directly — instead we wrap every connection in a thin Python shim.
        class _SQLCipherConnShim:
            """Python 3.8 sqlite3-compatible shim over a pysqlcipher3 Connection."""
            __slots__ = ("_c",)
            def __init__(self, conn):
                object.__setattr__(self, "_c", conn)
            def create_function(self, name, narg, func, deterministic=False):
                object.__getattribute__(self, "_c").create_function(name, narg, func)
            def __getattr__(self, name):
                return getattr(object.__getattribute__(self, "_c"), name)
            def __setattr__(self, name, value):
                if name == "_c":
                    object.__setattr__(self, name, value)
                else:
                    setattr(object.__getattribute__(self, "_c"), name, value)

        _orig_connect = _pysqlcipher3_mod.connect
        def _shim_connect(*a, **kw):
            return _SQLCipherConnShim(_orig_connect(*a, **kw))
        _pysqlcipher3_mod.connect = _shim_connect  # type: ignore

        _sys.modules["sqlite3"] = _pysqlcipher3_mod  # type: ignore[assignment]
    except ImportError:
        pass  # make_engine() will raise a clearer RuntimeError

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, create_engine, Index, text, event, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime, timezone
import uuid, os, sys

Base = declarative_base()


def _now():
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = Column(String, nullable=False)
    email      = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)


class Assessment(Base):
    __tablename__ = "assessments"

    id                     = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id           = Column(String, ForeignKey("candidates.id"), nullable=False)
    system_id              = Column(String, ForeignKey("systems.id"), nullable=True)   # Phase 3
    filename               = Column(String, nullable=False)
    file_path              = Column(String, nullable=False)
    uploaded_at            = Column(DateTime, default=_now)
    submitted_by           = Column(String, nullable=True)       # Remote-User who uploaded
    status                 = Column(String, default="processing")   # processing|complete|error
    total_controls_found   = Column(Integer, default=0)
    controls_complete      = Column(Integer, default=0)
    controls_partial       = Column(Integer, default=0)
    controls_insufficient  = Column(Integer, default=0)
    controls_not_found     = Column(Integer, default=0)
    ssp_score              = Column(Float, default=0.0)   # 0-100
    quiz_score             = Column(Float, default=0.0)   # 0-100
    combined_score         = Column(Float, default=0.0)   # 0-100
    is_allstar             = Column(Boolean, default=False)
    email_sent             = Column(Boolean, default=False)
    error_message          = Column(Text, nullable=True)


class ControlResult(Base):
    __tablename__ = "control_results"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id       = Column(String, ForeignKey("assessments.id"), nullable=False, index=True)
    control_id          = Column(String, nullable=False)        # e.g. "ac-1"
    control_family      = Column(String, nullable=False)        # e.g. "AC"
    control_title       = Column(String, nullable=False)
    found_in_ssp        = Column(Boolean, default=False)
    is_na               = Column(Boolean, default=False)        # explicitly marked N/A in SSP
    implementation_status = Column(String, nullable=True)
    responsible_role    = Column(String, nullable=True)
    narrative_excerpt   = Column(Text, nullable=True)           # first 500 chars of extracted text
    ai_score            = Column(Integer, default=0)            # 0-5
    ai_grade            = Column(String, default="NOT_FOUND")   # COMPLETE|PARTIAL|INSUFFICIENT|NOT_FOUND|NA
    ai_issues           = Column(Text, nullable=True)           # pipe-separated issues
    ai_elements_covered = Column(String, nullable=True)         # "3/7"
    proctor_assessment  = Column(Text, nullable=True)
    proctor_score       = Column(Integer, nullable=True)        # override by human


class QuizResponse(Base):
    __tablename__ = "quiz_responses"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id  = Column(String, ForeignKey("assessments.id"), nullable=False)
    question_id    = Column(Integer, nullable=False)
    selected_answer = Column(String, nullable=True)
    is_correct     = Column(Boolean, default=False)
    completed_at   = Column(DateTime, default=_now)


class DailyQuizActivity(Base):
    __tablename__ = "daily_quiz_activity"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    remote_user  = Column(String, nullable=False)
    quiz_date    = Column(String, nullable=False)    # ISO date "2026-02-26"
    score        = Column(Integer, default=0)        # 0-100
    passed       = Column(Boolean, default=False)
    completed_at = Column(DateTime, default=_now)


class ControlsMeta(Base):
    __tablename__ = "controls_meta"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    revision       = Column(String, nullable=False)       # "800-53r5"
    last_updated   = Column(DateTime, nullable=True)
    source_url     = Column(String, nullable=True)
    total_controls = Column(Integer, default=0)
    git_sha        = Column(String, nullable=True)


# ── Phase 3 Models ─────────────────────────────────────────────────────────────

class System(Base):
    """IT System Catalog (NIST SP 800-18 System Identification)"""
    __tablename__ = "systems"

    id                      = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name                    = Column(String, nullable=False)
    abbreviation            = Column(String, nullable=True)
    system_type             = Column(String, nullable=True)   # major_application|general_support_system|minor_application
    environment             = Column(String, nullable=True)   # on_prem|cloud|hybrid|saas|paas|iaas
    owner_name              = Column(String, nullable=True)
    owner_email             = Column(String, nullable=True)
    description             = Column(Text, nullable=True)
    purpose                 = Column(Text, nullable=True)
    boundary                = Column(Text, nullable=True)
    confidentiality_impact  = Column(String, nullable=True)   # Low|Moderate|High
    integrity_impact        = Column(String, nullable=True)
    availability_impact     = Column(String, nullable=True)
    overall_impact          = Column(String, nullable=True)   # computed max (FIPS 199)
    auth_status             = Column(String, default="not_authorized")  # authorized|in_progress|expired|not_authorized
    auth_date               = Column(String, nullable=True)   # ISO date
    auth_expiry             = Column(String, nullable=True)   # ISO date
    ato_decision            = Column(String, nullable=True)   # NULL|approved|denied (Phase 10)
    inventory_number        = Column(String, nullable=True, unique=True)  # TTTT-0200 format
    created_at              = Column(DateTime, default=_now)
    updated_at              = Column(DateTime, default=_now, onupdate=_now)
    created_by              = Column(String, nullable=True)   # Remote-User
    # Phase 15 — soft-delete
    deleted_at              = Column(DateTime, nullable=True)
    deleted_by              = Column(String, nullable=True)
    # Phase 17 — FIPS 199 data sensitivity flags
    has_pii                 = Column(Boolean, default=False)
    has_phi                 = Column(Boolean, default=False)
    has_ephi                = Column(Boolean, default=False)
    has_financial_data      = Column(Boolean, default=False)
    is_public_facing        = Column(Boolean, default=False)
    has_cui                 = Column(Boolean, default=False)
    connects_to_federal     = Column(Boolean, default=False)
    has_gdpr_data           = Column(Boolean, default=False)  # processes EU personal data
    # Phase 17 — categorization workflow
    categorization_status   = Column(String, default="draft")  # draft|pending_review|approved
    categorization_approved_by = Column(String, nullable=True)
    categorization_note     = Column(Text, nullable=True)
    # EIS flag (added via migration, Phase 12-era)
    is_eis                  = Column(Boolean, default=False)
    # Federal/FISMA applicability flag
    is_federal              = Column(Boolean, default=False)   # drives RMF banner + ATO package track
    # Primary control catalog — determines baseline options and control language
    primary_catalog         = Column(String, default="nist80053r5")  # nist80053r5|iso27001
    # Phase 20 — AO decision detail
    ato_duration            = Column(String, nullable=True)    # 1_year|3_year|5_year|ongoing|custom
    ato_notes               = Column(Text, nullable=True)      # AO decision rationale
    ato_signed_by           = Column(String, nullable=True)    # AO username
    ato_signed_at           = Column(DateTime, nullable=True)  # timestamp of AO signature
    # Phase 28 — Key personnel fields (free-text for external contacts + system contacts)
    ao_name                 = Column(String, nullable=True)    # Authorizing Official name
    ao_email                = Column(String, nullable=True)    # AO email
    issm_name               = Column(String, nullable=True)    # ISSM name
    issm_email              = Column(String, nullable=True)    # ISSM email
    isso_name               = Column(String, nullable=True)    # ISSO name
    isso_email              = Column(String, nullable=True)    # ISSO email
    # Phase 36 — Multi-tenant org ownership (added via col_migrations)
    org_id                  = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    # Control plan lock (added via col_migrations)
    controls_built          = Column(Boolean, default=False)
    controls_built_by       = Column(String, nullable=True)
    controls_built_at       = Column(DateTime, nullable=True)


class PoamItem(Base):
    """Plan of Action & Milestones.
    Status lifecycle: draft → open → in_progress → blocked → ready_for_review
      → closed_verified | deferred_waiver | accepted_risk | false_positive
    """
    __tablename__ = "poam_items"

    id                   = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    poam_id              = Column(String, nullable=True, unique=True, index=True)  # human ID: ABVR022826-1001AC01
    system_id            = Column(String, ForeignKey("systems.id"), nullable=True, index=True)
    assessment_id        = Column(String, ForeignKey("assessments.id"), nullable=True, index=True)
    control_id           = Column(String, nullable=True)        # e.g. "ac-2" or "ac-2,si-3"
    weakness_name        = Column(String, nullable=False)
    weakness_description = Column(Text, nullable=True)
    detection_source     = Column(String, nullable=True)        # assessment|scan|audit|pentest|self_report
    severity             = Column(String, default="Moderate")   # Critical|High|Moderate|Low|Informational
    responsible_party    = Column(String, nullable=True)
    resources_required   = Column(Text, nullable=True)
    scheduled_completion = Column(String, nullable=True)        # ISO date
    # Status set: draft|open|in_progress|blocked|ready_for_review|closed_verified|deferred_waiver|accepted_risk|false_positive
    status               = Column(String, default="open")
    approval_stage       = Column(String, nullable=True)        # pending_so|pending_ciso|pending_ao|approved
    remediation_plan     = Column(Text, nullable=True)
    root_cause           = Column(Text, nullable=True)
    closure_evidence     = Column(Text, nullable=True)          # required before closed_verified
    residual_risk        = Column(Text, nullable=True)          # required for ready_for_review
    completion_date      = Column(String, nullable=True)        # ISO date (actual)
    comments             = Column(Text, nullable=True)
    # Blocked status fields
    blocker_category     = Column(String, nullable=True)        # technical|process|resource|external
    blocker_owner        = Column(String, nullable=True)
    unblock_plan         = Column(Text, nullable=True)
    # Verification fields (closed_verified, false_positive)
    verifier             = Column(String, nullable=True)
    verification_date    = Column(String, nullable=True)        # ISO date
    verification_method  = Column(String, nullable=True)        # automated_scan|manual_review|pen_test|external_audit
    # Waiver / Risk Acceptance fields
    waiver_id            = Column(String, nullable=True)        # FK to future Waiver table
    waiver_start         = Column(String, nullable=True)        # ISO date
    waiver_end           = Column(String, nullable=True)        # ISO date
    monitoring_checkpoints = Column(Text, nullable=True)
    compensating_controls  = Column(Text, nullable=True)
    risk_accept_review   = Column(String, nullable=True)        # ISO date for next annual review
    # False Positive fields
    non_applicability_rationale = Column(Text, nullable=True)
    # Approval chain tracking (JSON list of {"role","user","date","action","notes"})
    signoff_trail        = Column(Text, nullable=True)
    system_generated     = Column(Boolean, default=False)   # True = created by auto-fail engine
    auto_fail_event_id   = Column(Integer, nullable=True)   # FK to auto_fail_events.id (if system_generated)
    created_at           = Column(DateTime, default=_now)
    updated_at           = Column(DateTime, default=_now, onupdate=_now)
    created_by           = Column(String, nullable=True)


class PoamEvidence(Base):
    """File attachments uploaded as closure evidence for a POA&M item."""
    __tablename__ = "poam_evidence"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    poam_item_id = Column(String, ForeignKey("poam_items.id"), nullable=False, index=True)
    filename    = Column(String, nullable=False)
    file_path   = Column(String, nullable=False)
    file_size   = Column(Integer, nullable=True)
    uploaded_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=_now)
    description = Column(String, nullable=True)


class Risk(Base):
    """Risk Register"""
    __tablename__ = "risks"

    id                  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id           = Column(String, ForeignKey("systems.id"), nullable=True, index=True)
    poam_id             = Column(String, ForeignKey("poam_items.id"), nullable=True)
    risk_name           = Column(String, nullable=False)
    risk_description    = Column(Text, nullable=True)
    threat_source       = Column(String, nullable=True)         # human|environmental|technical
    threat_event        = Column(String, nullable=True)
    vulnerability       = Column(Text, nullable=True)
    likelihood          = Column(Integer, default=3)            # 1-5
    impact              = Column(Integer, default=3)            # 1-5
    risk_score          = Column(Integer, default=9)            # likelihood × impact
    risk_level          = Column(String, default="Moderate")    # Low|Moderate|High|Critical
    treatment           = Column(String, default="Mitigate")    # Accept|Mitigate|Transfer|Avoid
    treatment_plan      = Column(Text, nullable=True)
    residual_likelihood = Column(Integer, default=2)
    residual_impact     = Column(Integer, default=2)
    residual_score      = Column(Integer, default=4)
    residual_level      = Column(String, default="Low")
    owner               = Column(String, nullable=True)
    status              = Column(String, default="open")        # open|closed|accepted
    review_date         = Column(String, nullable=True)         # ISO date
    created_at          = Column(DateTime, default=_now)
    updated_at          = Column(DateTime, default=_now, onupdate=_now)
    created_by          = Column(String, nullable=True)


class UserProfile(Base):
    """Per-user preferences and profile"""
    __tablename__ = "user_profiles"

    remote_user           = Column(String, primary_key=True)    # Authelia username
    display_name          = Column(String, nullable=True)
    email                 = Column(String, nullable=True)
    department            = Column(String, nullable=True)
    role                  = Column(String, default="employee")  # legacy shell/impersonation field
    company_tier          = Column(String, default="analyst")   # principal|executive|manager|analyst
    notifications_email   = Column(Boolean, default=True)
    notifications_quiz    = Column(Boolean, default=True)
    quiz_domains          = Column(Text, nullable=True)         # JSON list e.g. ["D1","D3"]
    max_packages          = Column(Integer, default=10)         # Max systems this ISSO can hold
    last_login            = Column(DateTime, nullable=True)
    status                = Column(String, default="active")    # active|frozen|removed
    removed_at            = Column(DateTime, nullable=True)
    removed_by            = Column(String, nullable=True)
    removal_reason        = Column(String, nullable=True)
    avatar_url            = Column(String, nullable=True)       # relative path: /profile/avatar/{user}
    # Phase 6 — H6: UI preferences persisted to DB
    pref_font_size        = Column(String, default="14px")    # 12px|14px|16px|18px|20px
    pref_density          = Column(String, default="comfortable")  # compact|comfortable|spacious
    pref_rows_per_page    = Column(Integer, default=25)        # 10|25|50|100
    chat_name             = Column(String, nullable=True)       # editable chat alias (max 20, unique)
    created_at            = Column(DateTime, default=_now)
    updated_at            = Column(DateTime, default=_now, onupdate=_now)


class ProgramRoleAssignment(Base):
    """
    Links a user to a system role on a specific system (or program-wide when system_id is NULL).
    Requires approval when assigning to a higher-authority role.
    status: active | pending_approval | denied | revoked
    """
    __tablename__ = "program_role_assignments"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    remote_user  = Column(String, ForeignKey("user_profiles.remote_user"), nullable=False, index=True)
    system_id    = Column(String, ForeignKey("systems.id"), nullable=True, index=True)  # NULL = program-wide
    program_role = Column(String, nullable=False)
    # ao|aodr|ciso|issm|isso|sca|system_owner|pmo|incident_responder|bcdr_coordinator|data_owner|pen_tester|auditor

    status       = Column(String, default="active")
    requested_by = Column(String, nullable=True)
    requested_at = Column(DateTime, default=_now)
    approved_by  = Column(String, nullable=True)
    approved_at  = Column(DateTime, nullable=True)
    revoked_by   = Column(String, nullable=True)
    revoked_at   = Column(DateTime, nullable=True)
    note         = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("remote_user", "program_role", "system_id",
                         name="uq_program_role_assignment"),
    )


class DutyAssignment(Base):
    """
    Lightweight duty assignments on a system — assigned by ISSO/ISSM, no approval chain.
    expires_at supports time-boxed duties (pen_tester, auditor engagements).
    duty: incident_responder|bcdr_coordinator|data_owner|pen_tester|auditor|aodr
    """
    __tablename__ = "duty_assignments"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    remote_user = Column(String, ForeignKey("user_profiles.remote_user"), nullable=False, index=True)
    system_id   = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    duty        = Column(String, nullable=False)

    assigned_by = Column(String, nullable=True)
    assigned_at = Column(DateTime, default=_now)
    active      = Column(Boolean, default=True)
    expires_at  = Column(DateTime, nullable=True)  # NULL = no expiry
    note        = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("remote_user", "duty", "system_id",
                         name="uq_duty_assignment"),
    )


class Notification(Base):
    """
    In-app alerts for role approval requests, approvals, duty assignments, etc.
    related_type: "role" | "duty"
    notif_type: role_approval_request|role_approved|role_denied|role_revoked|duty_assigned|duty_expired|duty_revoked
    """
    __tablename__ = "notifications"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    remote_user  = Column(String, ForeignKey("user_profiles.remote_user"), nullable=False, index=True)
    notif_type   = Column(String, nullable=False)
    title        = Column(String, nullable=False)
    body         = Column(Text, nullable=True)
    action_url   = Column(String, nullable=True)
    related_id   = Column(Integer, nullable=True)
    related_type = Column(String, nullable=True)
    is_read      = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=_now)
    read_at      = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Audit trail for all mutations (NIST AU-2/AU-12)"""
    __tablename__ = "audit_log"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    timestamp     = Column(DateTime, default=_now, index=True)
    remote_user   = Column(String, nullable=True)
    action        = Column(String, nullable=False)    # CREATE|UPDATE|DELETE|VIEW|LOGIN|EXPORT
    resource_type = Column(String, nullable=True)     # assessment|system|poam|risk|profile
    resource_id   = Column(String, nullable=True)
    details       = Column(Text, nullable=True)       # JSON summary
    remote_ip     = Column(String, nullable=True)     # operator IP from reverse proxy
    outcome       = Column(String, nullable=True, default="ok")  # ok|denied|error


class SecurityEvent(Base):
    """SIEM event log — HTTP, auth, access, and anomaly events."""
    __tablename__ = "security_events"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    timestamp   = Column(DateTime, default=_now, index=True)
    event_type  = Column(String, index=True)   # http|login|failed_auth|access_denied|frozen_access|anomaly
    severity    = Column(String, default="info")  # info|low|medium|high|critical
    remote_ip   = Column(String)
    remote_user = Column(String, index=True)
    method      = Column(String)
    path        = Column(String)
    status_code = Column(Integer)
    user_agent  = Column(String)
    details     = Column(Text)


# ── Phase 4 Models ─────────────────────────────────────────────────────────────

class SystemAssignment(Base):
    """Links an employee (remote_user) to a System they are responsible for."""
    __tablename__ = "system_assignments"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    system_id   = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    remote_user = Column(String, nullable=False, index=True)   # Authelia username of the assignee
    assigned_by = Column(String, nullable=True)    # admin who made the assignment
    assigned_at = Column(DateTime, default=_now)
    note        = Column(String, nullable=True)    # optional context note


class ControlEdit(Base):
    """Employee-authored edits to a control result (narrative, status, role)."""
    __tablename__ = "control_edits"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    control_result_id   = Column(Integer, ForeignKey("control_results.id"), nullable=False)
    assessment_id       = Column(String, ForeignKey("assessments.id"), nullable=False)
    remote_user         = Column(String, nullable=False)
    field               = Column(String, nullable=False)    # 'narrative'|'status'|'responsible_role'|'note'
    old_value           = Column(Text, nullable=True)
    new_value           = Column(Text, nullable=True)
    edited_at           = Column(DateTime, default=_now)


# ── Phase 5 Models ─────────────────────────────────────────────────────────────

class SystemControl(Base):
    """Per-system control implementation record (living SSP, independent of assessments)."""
    __tablename__ = "system_controls"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    system_id            = Column(String, ForeignKey("systems.id"), nullable=False)
    control_id           = Column(String, nullable=False)       # e.g. "ac-1" or "A.5.18"
    control_family       = Column(String, nullable=False)       # e.g. "AC" or "Technological"
    control_title        = Column(String, nullable=True)
    source_catalog       = Column(String, default="nist80053r5")  # nist80053r5|iso27001|cis8|etc.
    status               = Column(String, default="not_started")
    # not_started|in_progress|implemented|not_applicable|inherited|planned
    implementation_type  = Column(String, default="system")     # system|hybrid|inherited
    narrative            = Column(Text, nullable=True)          # implementation narrative
    responsible_role     = Column(String, nullable=True)
    inherited_from       = Column(String, ForeignKey("systems.id"), nullable=True)
    inherited_narrative  = Column(Text, nullable=True)          # what the providing system implements
    last_updated_by      = Column(String, nullable=True)
    last_updated_at      = Column(DateTime, default=_now, onupdate=_now)
    created_at           = Column(DateTime, default=_now)
    created_by           = Column(String, nullable=True)
    # SCA assessment fields — written by assessor, independent of ISSO implementation record
    assessment_result    = Column(String, nullable=True)   # satisfied|other_than_satisfied|not_applicable|not_assessed
    assessment_notes     = Column(Text, nullable=True)     # assessor observations, evidence references, findings
    assessed_by          = Column(String, nullable=True)
    assessed_at          = Column(DateTime, nullable=True)
    # Crosswalk propagation tracking — set when status was derived from another framework
    xw_source            = Column(String, nullable=True)   # e.g. "nist80053r5:ac-2" — source of propagated status
    # Post-build suppression (N/A or removal approved via two-party workflow)
    hidden_post_build    = Column(Boolean, default=False)
    hidden_approved_at   = Column(DateTime, nullable=True)
    hidden_approved_by   = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_sysctl_system_ctrl", "system_id", "control_id", unique=True),
    )


class ControlRemovalRequest(Base):
    """Two-party approval workflow for removing or N/A-ing a control after the plan is locked."""
    __tablename__ = "control_removal_requests"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    system_id         = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    control_id        = Column(String, nullable=False)
    requested_action  = Column(String, nullable=False)   # "remove" | "set_na"
    justification     = Column(Text, nullable=False)
    status            = Column(String, default="pending")  # pending|approved|denied|withdrawn
    initiated_by      = Column(String, nullable=False)
    initiated_by_role = Column(String, nullable=False)
    initiated_at      = Column(DateTime, default=_now)
    reviewed_by       = Column(String, nullable=True)
    reviewed_by_role  = Column(String, nullable=True)
    reviewed_at       = Column(DateTime, nullable=True)
    review_comment    = Column(Text, nullable=True)


class Submission(Base):
    """Authorization package / ATO submission tracking."""
    __tablename__ = "submissions"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id        = Column(String, ForeignKey("systems.id"), nullable=False)
    submission_type  = Column(String, default="initial")
    # initial|reauthorization|significant_change|annual_review
    authorization_type = Column(String, default="ATO")          # ATO|ATP|IATO|EIS
    term_months      = Column(Integer, nullable=True)           # ATP=12, IATO=6, None=indefinite
    term_expires_at  = Column(String, nullable=True)            # ISO date for term-limited auths
    extension_used   = Column(Boolean, default=False)
    status           = Column(String, default="draft")
    # draft|submitted|under_review|authorized|denied|withdrawn
    package_notes    = Column(Text, nullable=True)
    submitted_by     = Column(String, nullable=True)
    submitted_at     = Column(DateTime, nullable=True)
    reviewer         = Column(String, nullable=True)
    reviewed_at      = Column(DateTime, nullable=True)
    decision         = Column(String, nullable=True)            # authorized|denied
    decision_date    = Column(String, nullable=True)            # ISO date
    ato_expiry       = Column(String, nullable=True)            # ISO date
    controls_total   = Column(Integer, default=0)               # snapshot at submission
    controls_impl    = Column(Integer, default=0)
    controls_na      = Column(Integer, default=0)
    controls_gap     = Column(Integer, default=0)
    created_at       = Column(DateTime, default=_now)
    updated_at       = Column(DateTime, default=_now, onupdate=_now)
    created_by       = Column(String, nullable=True)


# ── Phase 6 Models ─────────────────────────────────────────────────────────────

class RmfRecord(Base):
    """Per-system RMF step tracking (NIST SP 800-37 Rev 2)."""
    __tablename__ = "rmf_records"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id   = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    step        = Column(String, nullable=False)   # prepare|categorize|select|implement|assess|authorize|monitor
    status      = Column(String, default="not_started")  # not_started|in_progress|complete|waived
    owner       = Column(String, nullable=True)
    target_date = Column(String, nullable=True)    # ISO date
    actual_date = Column(String, nullable=True)    # ISO date
    evidence    = Column(Text, nullable=True)
    artifacts   = Column(Text, nullable=True)      # JSON list of references
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)
    created_by  = Column(String, nullable=True)


# ── Phase 7 Models ─────────────────────────────────────────────────────────────

class AtoDocument(Base):
    """Per-system ATO artifact with workflow lifecycle."""
    __tablename__ = "ato_documents"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id   = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    doc_type    = Column(String, nullable=False)   # FIPS199 | SSP | SAP | etc.
    title       = Column(String, nullable=False)
    version     = Column(String, default="0.1")
    status      = Column(String, default="draft")  # draft|in_review|approved|finalized
    content     = Column(Text, nullable=True)      # freeform text / JSON notes
    assigned_to = Column(String, nullable=True)    # current reviewer/assignee
    due_date    = Column(String, nullable=True)    # ISO date
    file_path   = Column(String, nullable=True)    # path to uploaded or generated file
    file_size   = Column(Integer, nullable=True)   # bytes
    source_type = Column(String, nullable=True)    # "uploaded" | "generated"
    created_by  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)


class AtoDocumentVersion(Base):
    """Immutable snapshot of an AtoDocument at each state transition."""
    __tablename__ = "ato_document_versions"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id  = Column(String, ForeignKey("ato_documents.id"), nullable=False, index=True)
    version      = Column(String, nullable=False)
    content_snap = Column(Text, nullable=True)
    from_status  = Column(String, nullable=True)
    to_status    = Column(String, nullable=True)
    changed_by   = Column(String, nullable=True)
    changed_at   = Column(DateTime, default=_now)
    change_note  = Column(String, nullable=True)


class AtoWorkflowEvent(Base):
    """Immutable workflow transition log for ATO documents."""
    __tablename__ = "ato_workflow_events"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("ato_documents.id"), nullable=False, index=True)
    from_status = Column(String, nullable=True)
    to_status   = Column(String, nullable=True)
    actor       = Column(String, nullable=True)
    actor_role  = Column(String, nullable=True)
    comment     = Column(Text, nullable=True)
    timestamp   = Column(DateTime, default=_now)


# ── Phase 10 Models ────────────────────────────────────────────────────────────

class SystemTeam(Base):
    """Teams/groups associated with a system (recovery, response, general, BCDR)."""
    __tablename__ = "system_teams"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    system_id   = Column(String, ForeignKey("systems.id"), nullable=False)
    name        = Column(String, nullable=False)          # e.g. "Rapid Response Team"
    team_type   = Column(String, default="general")       # general|recovery|response|bcdr
    description = Column(String, nullable=True)
    created_by  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=_now)


class TeamMembership(Base):
    """Membership linking a user to a SystemTeam."""
    __tablename__ = "team_memberships"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    team_id      = Column(Integer, ForeignKey("system_teams.id"), nullable=False)
    remote_user  = Column(String, nullable=False)
    role_in_team = Column(String, default="member")       # lead|member|observer
    assigned_by  = Column(String, nullable=True)
    assigned_at  = Column(DateTime, default=_now)


class BcdrEvent(Base):
    """BCDR incident / drill / test event."""
    __tablename__ = "bcdr_events"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    system_id    = Column(String, ForeignKey("systems.id"), nullable=True)
    team_id      = Column(Integer, ForeignKey("system_teams.id"), nullable=True)
    event_type   = Column(String, nullable=True)          # drill|incident|recovery|test
    title        = Column(String, nullable=True)
    status       = Column(String, default="open")         # open|in_progress|closed
    triggered_by = Column(String, nullable=True)
    triggered_at = Column(DateTime, default=_now)
    target_rto   = Column(Integer, nullable=True)         # hours
    target_rpo   = Column(Integer, nullable=True)         # hours
    closed_at    = Column(DateTime, nullable=True)


class BcdrSignoff(Base):
    """Required sign-off record for a BcdrEvent."""
    __tablename__ = "bcdr_signoffs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    event_id     = Column(Integer, ForeignKey("bcdr_events.id"), nullable=False)
    remote_user  = Column(String, nullable=False)
    role_in_team = Column(String, nullable=True)
    required     = Column(Boolean, default=True)
    signed_off   = Column(Boolean, default=False)
    signed_at    = Column(DateTime, nullable=True)
    notes        = Column(String, nullable=True)


# ── Phase 12 Models ────────────────────────────────────────────────────────────

class Observation(Base):
    """Unified findings inbox — pre-POA&M staging (FedRAMP gap closure)."""
    __tablename__ = "observations"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id        = Column(String, ForeignKey("systems.id"), nullable=True, index=True)
    title            = Column(String, nullable=False)
    source           = Column(String)    # assessment|scan|audit|pentest|self_report|threat_intel
    obs_type         = Column(String)    # finding|shortcoming|deviation|risk_indicator
    severity         = Column(String, default="Moderate")  # Critical|High|Moderate|Low|Info
    description      = Column(Text)
    control_ids      = Column(Text)      # JSON list ["ac-1","ac-2"]
    scope_tags       = Column(Text)      # JSON list ["environment:prod","component:db"]
    status           = Column(String, default="open")  # open|promoted|closed|false_positive
    promoted_to_poam = Column(String, ForeignKey("poam_items.id"), nullable=True)
    assigned_to      = Column(String)
    due_date         = Column(String)
    created_by       = Column(String)
    created_at       = Column(DateTime, default=_now)
    updated_at       = Column(DateTime, default=_now, onupdate=_now)


class InventoryItem(Base):
    """Structured hardware/software/firmware inventory rows."""
    __tablename__ = "inventory_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    item_type     = Column(String, nullable=False)   # hardware|software|firmware
    name          = Column(String, nullable=False)
    vendor        = Column(String)
    version       = Column(String)
    quantity      = Column(Integer, default=1)
    location      = Column(String)
    ip_address    = Column(String)
    serial_number = Column(String)
    notes         = Column(Text)
    added_by      = Column(String)
    added_at      = Column(DateTime, default=_now)


class SystemConnection(Base):
    """Internal/external boundary connection records."""
    __tablename__ = "system_connections"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    conn_type     = Column(String)    # internal|external
    name          = Column(String, nullable=False)
    description   = Column(Text)
    remote_system = Column(String)
    data_types    = Column(String)
    protocol      = Column(String)
    port          = Column(String)
    direction     = Column(String)    # inbound|outbound|bidirectional
    has_isa       = Column(Boolean, default=False)
    isa_doc_id    = Column(String, nullable=True)
    added_by      = Column(String)
    added_at      = Column(DateTime, default=_now)


class Artifact(Base):
    """Evidence artifact with integrity metadata."""
    __tablename__ = "artifacts"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id       = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    control_id      = Column(String, index=True)
    artifact_type   = Column(String)   # screenshot|log|config|policy|report|scan_result|other
    title           = Column(String, nullable=False)
    description     = Column(Text)
    file_path       = Column(String)
    source          = Column(String)
    integrity_hash  = Column(String)   # SHA-256
    collected_at    = Column(DateTime)
    freshness_days  = Column(Integer, default=365)
    owner           = Column(String)
    approval_status = Column(String, default="pending")  # pending|approved|rejected
    approved_by     = Column(String)
    approved_at     = Column(DateTime)
    created_by      = Column(String)
    created_at      = Column(DateTime, default=_now)


# ── Phase 16 Models ────────────────────────────────────────────────────────────

class AdminChatMessage(Base):
    __tablename__ = "admin_chat_messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    room       = Column(String(120), nullable=False, index=True)
    # room values: "@group"  OR  sorted pair "alice:dan"
    from_user  = Column(String(120), nullable=False)
    body       = Column(Text, nullable=False)
    sent_at    = Column(DateTime, default=_now)
    media_path = Column(String(260), nullable=True)   # relative path under data/uploads/chat_images/
    media_mime = Column(String(40),  nullable=True)   # e.g. image/jpeg


class AdminChatReceipt(Base):
    """Tracks last-read message ID per user per room for unread counts."""
    __tablename__ = "admin_chat_receipts"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    room         = Column(String(120), nullable=False)
    username     = Column(String(120), nullable=False)
    last_read_id = Column(Integer, default=0)


# ── Database setup ─────────────────────────────────────────────────────────────

import re as _re_upsert

def _upsert_sql(sql: str, dialect: str) -> str:
    """Return SQL adapted for the dialect's INSERT-or-skip syntax.

    PostgreSQL uses ON CONFLICT DO NOTHING (SQL standard upsert).
    SQLite — including pysqlcipher3 which bundles SQLite 3.15 — uses
    INSERT OR IGNORE INTO (supported since SQLite 2.x).
    """
    if dialect == "postgresql":
        return sql  # already in ON CONFLICT DO NOTHING form
    # SQLite path: swap ON CONFLICT DO NOTHING → INSERT OR IGNORE
    sql = sql.replace("INSERT INTO ", "INSERT OR IGNORE INTO ", 1)
    sql = _re_upsert.sub(r"\s*ON CONFLICT DO NOTHING\s*", " ", sql).strip()
    return sql


def get_db_url(config: dict) -> str:
    """Return the SQLAlchemy database URL.

    Checks DATABASE_URL environment variable first (for PostgreSQL and other
    backends). Falls back to SQLite using the path from config.
    """
    if db_url := os.environ.get("DATABASE_URL"):
        return db_url
    db_path = config.get("db", {}).get("path", "blacksite.db")
    return f"sqlite+aiosqlite:///{db_path}"


# ── Phase 36 — Multi-tenant Organizations ─────────────────────────────────────

DEFAULT_ORG_ID   = "00000000-0000-0000-0000-000000000001"
DEFAULT_ORG_NAME = "Default Organization"


class Organization(Base):
    __tablename__ = "organizations"

    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    name        = Column(String,  nullable=False)
    slug        = Column(String,  nullable=True)   # url-safe short name, unique
    description = Column(Text,    nullable=True)
    logo_url    = Column(String,  nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)
    created_by  = Column(String,  nullable=True)


class UserOrganizationMembership(Base):
    __tablename__ = "user_org_memberships"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    org_id      = Column(String,  ForeignKey("organizations.id"), nullable=False, index=True)
    remote_user = Column(String,  ForeignKey("user_profiles.remote_user"), nullable=False, index=True)
    org_role    = Column(String,  default="member")   # org_admin | member | viewer
    invited_by  = Column(String,  nullable=True)
    joined_at   = Column(DateTime, default=_now)
    is_active   = Column(Boolean, default=True)


async def _migrate_db(engine):
    """Add any missing columns and indexes to existing tables (safe migrations)."""
    col_migrations = [
        # (table_name, column_name, column_def)
        ("assessments",     "system_id",          "TEXT REFERENCES systems(id)"),
        ("control_results", "is_na",               "BOOLEAN DEFAULT 0"),
        ("control_results", "proctor_assessment",  "TEXT"),
        ("control_results", "proctor_score",       "INTEGER"),
        ("user_profiles",   "role",                "TEXT DEFAULT 'employee'"),
        ("user_profiles",   "max_packages",        "INTEGER DEFAULT 10"),
        ("systems",         "ato_decision",        "TEXT DEFAULT NULL"),
        # Phase 12 additions
        ("submissions",     "authorization_type",  "TEXT DEFAULT 'ATO'"),
        ("submissions",     "term_months",         "INTEGER DEFAULT NULL"),
        ("submissions",     "term_expires_at",     "TEXT DEFAULT NULL"),
        ("submissions",     "extension_used",      "BOOLEAN DEFAULT 0"),
        ("systems",         "is_eis",              "BOOLEAN DEFAULT 0"),
        # Phase 13 additions
        ("user_profiles",   "last_login",          "DATETIME DEFAULT NULL"),
        ("user_profiles",   "status",              "TEXT DEFAULT 'active'"),
        ("user_profiles",   "removed_at",          "DATETIME DEFAULT NULL"),
        ("user_profiles",   "removed_by",          "TEXT DEFAULT NULL"),
        ("user_profiles",   "removal_reason",      "TEXT DEFAULT NULL"),
        # Phase 14 — POA&M state expansion
        ("poam_items",      "root_cause",          "TEXT DEFAULT NULL"),
        ("poam_items",      "closure_evidence",    "TEXT DEFAULT NULL"),
        ("poam_items",      "waiver_id",           "TEXT DEFAULT NULL"),
        ("poam_items",      "risk_accept_review",  "TEXT DEFAULT NULL"),
        # Phase 18 — POA&M human ID + status workflow columns
        ("poam_items",      "poam_id",             "TEXT DEFAULT NULL"),
        ("poam_items",      "approval_stage",      "TEXT DEFAULT NULL"),
        ("poam_items",      "residual_risk",       "TEXT DEFAULT NULL"),
        ("poam_items",      "blocker_category",    "TEXT DEFAULT NULL"),
        ("poam_items",      "blocker_owner",       "TEXT DEFAULT NULL"),
        ("poam_items",      "unblock_plan",        "TEXT DEFAULT NULL"),
        ("poam_items",      "verifier",            "TEXT DEFAULT NULL"),
        ("poam_items",      "verification_date",   "TEXT DEFAULT NULL"),
        ("poam_items",      "verification_method", "TEXT DEFAULT NULL"),
        ("poam_items",      "waiver_start",        "TEXT DEFAULT NULL"),
        ("poam_items",      "waiver_end",          "TEXT DEFAULT NULL"),
        ("poam_items",      "monitoring_checkpoints", "TEXT DEFAULT NULL"),
        ("poam_items",      "compensating_controls",  "TEXT DEFAULT NULL"),
        ("poam_items",      "non_applicability_rationale", "TEXT DEFAULT NULL"),
        ("poam_items",      "signoff_trail",       "TEXT DEFAULT NULL"),
        # Phase 15 — System soft-delete
        ("systems",         "deleted_at",          "DATETIME DEFAULT NULL"),
        ("systems",         "deleted_by",          "TEXT DEFAULT NULL"),
        # Phase 16+ — Inventory number
        ("systems",         "inventory_number",    "TEXT DEFAULT NULL"),
        # Phase 17 — FIPS 199 data sensitivity flags
        ("systems",         "has_pii",             "BOOLEAN DEFAULT 0"),
        ("systems",         "has_phi",             "BOOLEAN DEFAULT 0"),
        ("systems",         "has_ephi",            "BOOLEAN DEFAULT 0"),
        ("systems",         "has_financial_data",  "BOOLEAN DEFAULT 0"),
        ("systems",         "is_public_facing",    "BOOLEAN DEFAULT 0"),
        ("systems",         "has_cui",             "BOOLEAN DEFAULT 0"),
        ("systems",         "connects_to_federal", "BOOLEAN DEFAULT 0"),
        ("systems",         "has_gdpr_data",       "BOOLEAN DEFAULT 0"),
        # Phase 17 — categorization workflow
        ("systems",         "categorization_status",      "TEXT DEFAULT 'draft'"),
        ("systems",         "categorization_approved_by", "TEXT DEFAULT NULL"),
        ("systems",         "categorization_note",        "TEXT DEFAULT NULL"),
        # Phase 6 — H6: UI preference columns on UserProfile
        ("user_profiles",   "avatar_url",                  "TEXT DEFAULT NULL"),
        ("user_profiles",   "pref_font_size",              "TEXT DEFAULT '14px'"),
        ("user_profiles",   "pref_density",                "TEXT DEFAULT 'comfortable'"),
        ("user_profiles",   "pref_rows_per_page",          "INTEGER DEFAULT 25"),
        # Phase 20 — Platform tier, AO decision detail, ATO doc file storage
        ("user_profiles",   "company_tier",               "TEXT DEFAULT 'analyst'"),
        ("systems",         "ato_duration",               "TEXT DEFAULT NULL"),
        ("systems",         "ato_notes",                  "TEXT DEFAULT NULL"),
        ("systems",         "ato_signed_by",              "TEXT DEFAULT NULL"),
        ("systems",         "ato_signed_at",              "DATETIME DEFAULT NULL"),
        # Phase 28 — Key personnel fields
        ("systems",         "ao_name",                    "TEXT DEFAULT NULL"),
        ("systems",         "ao_email",                   "TEXT DEFAULT NULL"),
        ("systems",         "issm_name",                  "TEXT DEFAULT NULL"),
        ("systems",         "issm_email",                 "TEXT DEFAULT NULL"),
        ("systems",         "isso_name",                  "TEXT DEFAULT NULL"),
        ("systems",         "isso_email",                 "TEXT DEFAULT NULL"),
        ("ato_documents",   "file_path",                  "TEXT DEFAULT NULL"),
        ("ato_documents",   "file_size",                  "INTEGER DEFAULT NULL"),
        ("ato_documents",   "source_type",                "TEXT DEFAULT NULL"),
        # Phase 26 audit log enrichment
        ("audit_log",       "remote_ip",                  "TEXT DEFAULT NULL"),
        ("audit_log",       "outcome",                    "TEXT DEFAULT 'ok'"),
        # Phase 31 — cross-industry auth package tracking
        ("systems",               "is_federal",    "BOOLEAN DEFAULT 0"),
        ("system_frameworks",     "sub_category",  "TEXT DEFAULT NULL"),
        # Phase 31 — control catalog taxonomy
        ("compliance_frameworks", "kind",            "TEXT DEFAULT 'framework'"),
        # Phase 32 — parallel catalog support
        ("system_controls",       "source_catalog",           "TEXT DEFAULT 'nist80053r5'"),
        ("systems",               "primary_catalog",          "TEXT DEFAULT 'nist80053r5'"),
        # Phase 33 — framework suppression on org disable
        ("system_controls",       "suppressed_by_framework_id", "TEXT DEFAULT NULL"),
        ("system_controls",       "suppressed_at",              "DATETIME DEFAULT NULL"),
        # Chat name — user-editable alias shown in admin chat (max 20 chars, unique)
        ("user_profiles",         "chat_name",                  "TEXT DEFAULT NULL"),
        # Phase 34 — agnostic catalog FK columns (nullable; backfilled by migrate_catalog.py)
        ("system_controls",    "catalog_control_id", "TEXT DEFAULT NULL REFERENCES catalog_controls(id)"),
        ("control_results",    "catalog_control_id", "TEXT DEFAULT NULL REFERENCES catalog_controls(id)"),
        ("poam_items",         "catalog_control_id", "TEXT DEFAULT NULL REFERENCES catalog_controls(id)"),
        ("control_parameters", "catalog_control_id", "TEXT DEFAULT NULL REFERENCES catalog_controls(id)"),
        ("auto_fail_events",   "catalog_control_id", "TEXT DEFAULT NULL REFERENCES catalog_controls(id)"),
        ("artifacts",          "catalog_control_id", "TEXT DEFAULT NULL REFERENCES catalog_controls(id)"),
        # SCA assessment fields on system_controls
        ("system_controls", "assessment_result", "TEXT DEFAULT NULL"),
        ("system_controls", "assessment_notes",  "TEXT DEFAULT NULL"),
        ("system_controls", "assessed_by",       "TEXT DEFAULT NULL"),
        ("system_controls", "assessed_at",        "DATETIME DEFAULT NULL"),
        # Crosswalk propagation source tracking
        ("system_controls", "xw_source",         "TEXT DEFAULT NULL"),
        # Phase 36 — Multi-tenant org columns
        ("systems",    "org_id",   "TEXT DEFAULT NULL REFERENCES organizations(id)"),
        ("audit_log",  "org_id",   "TEXT DEFAULT NULL"),
        # Phase 38 — mime_type on generated_reports (PDF vs DOCX templates)
        ("generated_reports", "mime_type", "TEXT DEFAULT 'application/pdf'"),
        # Control plan lock + two-party approval workflow
        ("systems",          "controls_built",       "BOOLEAN DEFAULT 0"),
        ("systems",          "controls_built_by",    "TEXT DEFAULT NULL"),
        ("systems",          "controls_built_at",    "DATETIME DEFAULT NULL"),
        ("system_controls",  "hidden_post_build",    "BOOLEAN DEFAULT 0"),
        ("system_controls",  "hidden_approved_at",   "DATETIME DEFAULT NULL"),
        ("system_controls",  "hidden_approved_by",   "TEXT DEFAULT NULL"),
        # Chat image attachments
        ("admin_chat_messages", "media_path", "TEXT DEFAULT NULL"),
        ("admin_chat_messages", "media_mime", "TEXT DEFAULT NULL"),
        # Interview session type (control_interview vs daily_ops)
        ("interview_sessions", "session_type", "TEXT DEFAULT 'control_interview'"),
        # Interview overlay framework tracking
        ("interview_questions", "overlay_framework", "TEXT DEFAULT NULL"),
        ("interview_questions", "parent_control_id",  "TEXT DEFAULT NULL"),
        ("interview_questions", "question_type",    "TEXT DEFAULT 'text'"),
        ("interview_questions", "question_options", "TEXT DEFAULT NULL"),
    ]
    # Performance indexes — CREATE INDEX IF NOT EXISTS is idempotent
    index_migrations = [
        # Phase 6 — B2: reservation indexes
        "CREATE INDEX IF NOT EXISTS idx_ruv_username ON removed_user_reservations(username)",
        "CREATE INDEX IF NOT EXISTS idx_ruv_email    ON removed_user_reservations(email)",
        "CREATE INDEX IF NOT EXISTS idx_ruv_hold     ON removed_user_reservations(hold_until)",
        "CREATE INDEX IF NOT EXISTS ix_control_results_assessment_id ON control_results (assessment_id)",
        "CREATE INDEX IF NOT EXISTS ix_poam_items_system_id           ON poam_items (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_poam_items_assessment_id       ON poam_items (assessment_id)",
        "CREATE INDEX IF NOT EXISTS ix_risks_system_id                ON risks (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_system_assignments_system_id   ON system_assignments (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_system_assignments_remote_user ON system_assignments (remote_user)",
        "CREATE INDEX IF NOT EXISTS ix_audit_log_remote_user          ON audit_log (remote_user)",
        "CREATE INDEX IF NOT EXISTS ix_report_templates_org_id        ON report_templates (org_id)",
        "CREATE INDEX IF NOT EXISTS ix_report_templates_active        ON report_templates (is_active, deleted_at)",
        "CREATE INDEX IF NOT EXISTS ix_assessments_system_id          ON assessments (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_ato_documents_system_id        ON ato_documents (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_ato_doc_versions_document_id   ON ato_document_versions (document_id)",
        "CREATE INDEX IF NOT EXISTS ix_ato_workflow_events_document_id ON ato_workflow_events (document_id)",
        # Phase 25 — Daily Workflow indexes
        "CREATE INDEX IF NOT EXISTS ix_daily_logbooks_sys_date        ON daily_logbooks (system_id, log_date)",
        "CREATE INDEX IF NOT EXISTS ix_daily_logbooks_user_sys        ON daily_logbooks (remote_user, system_id)",
        "CREATE INDEX IF NOT EXISTS ix_dw_completions_rotation        ON deep_work_completions (rotation_id)",
        "CREATE INDEX IF NOT EXISTS ix_dw_completions_user_sys        ON deep_work_completions (remote_user, system_id)",
        "CREATE INDEX IF NOT EXISTS ix_change_review_sys_date         ON change_review_records (system_id, review_date)",
        "CREATE INDEX IF NOT EXISTS ix_backup_checks_sys              ON backup_check_records (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_access_spot_checks_sys         ON access_spot_checks (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_vendors_system_id              ON vendors (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_interconnections_system_id     ON interconnection_records (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_data_flows_system_id           ON data_flow_records (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_privacy_assessments_sys        ON privacy_assessments (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_restore_tests_sys              ON restore_test_records (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_generated_reports_sys_status   ON generated_reports (system_id, status)",
        # Unique constraints backfilled for existing DBs (safe on new installs — IF NOT EXISTS)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_dw_completion_day_date ON deep_work_completions (rotation_id, rotation_day, completed_date)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_change_review_user_sys_date ON change_review_records (remote_user, system_id, review_date)",
        # Phase 26 audit log filter indexes
        "CREATE INDEX IF NOT EXISTS ix_audit_log_action        ON audit_log (action)",
        "CREATE INDEX IF NOT EXISTS ix_audit_log_resource_type ON audit_log (resource_type)",
        "CREATE INDEX IF NOT EXISTS ix_audit_log_outcome       ON audit_log (outcome)",
        # Phase 34 — catalog control indexes
        "CREATE INDEX IF NOT EXISTS ix_catalog_controls_framework    ON catalog_controls (framework_id)",
        "CREATE INDEX IF NOT EXISTS ix_catalog_controls_control_id   ON catalog_controls (control_id)",
        "CREATE INDEX IF NOT EXISTS ix_ctrl_rel_a                    ON control_relationships (control_a_id)",
        "CREATE INDEX IF NOT EXISTS ix_ctrl_rel_b                    ON control_relationships (control_b_id)",
        "CREATE INDEX IF NOT EXISTS ix_baseline_controls_baseline    ON baseline_controls (baseline_id)",
        "CREATE INDEX IF NOT EXISTS ix_baseline_controls_ctrl        ON baseline_controls (catalog_control_id)",
        "CREATE INDEX IF NOT EXISTS ix_system_controls_cat_ctrl      ON system_controls (catalog_control_id)",
        "CREATE INDEX IF NOT EXISTS ix_control_results_cat_ctrl      ON control_results (catalog_control_id)",
        # Phase 36 — org membership uniqueness (safe dedup for existing DBs)
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_uom_org_user ON user_org_memberships(org_id, remote_user)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_org_settings_key ON org_settings(org_id, key)",
    ]
    async with engine.begin() as conn:
        dialect_name = conn.dialect.name

        def _adapt_col_def(defn: str) -> str:
            """Adapt SQLite column definitions to the current dialect."""
            if dialect_name != "postgresql":
                return defn
            defn = defn.replace("DATETIME", "TIMESTAMP")
            import re as _re
            defn = _re.sub(r'\bBOOLEAN DEFAULT 0\b', 'BOOLEAN DEFAULT FALSE', defn)
            defn = _re.sub(r'\bBOOLEAN DEFAULT 1\b', 'BOOLEAN DEFAULT TRUE', defn)
            return defn

        def _get_cols(sync_conn, tname):
            from sqlalchemy import inspect as _sa_inspect
            try:
                return {c["name"] for c in _sa_inspect(sync_conn).get_columns(tname)}
            except Exception:
                return set()

        for table, col, col_def in col_migrations:
            existing = await conn.run_sync(_get_cols, table)
            if col not in existing:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN {col} {_adapt_col_def(col_def)}"
                ))
        # Control plan removal request table (created here for existing DBs that predate Base.metadata.create_all)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS control_removal_requests (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                system_id         TEXT NOT NULL REFERENCES systems(id),
                control_id        TEXT NOT NULL,
                requested_action  TEXT NOT NULL,
                justification     TEXT NOT NULL,
                status            TEXT DEFAULT 'pending',
                initiated_by      TEXT NOT NULL,
                initiated_by_role TEXT NOT NULL,
                initiated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_by       TEXT,
                reviewed_by_role  TEXT,
                reviewed_at       DATETIME,
                review_comment    TEXT
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_ctrl_removal_system ON control_removal_requests (system_id)"
        ))

        # Phase 36: dedup org membership rows before unique index (backfill may run multiple times)
        await conn.execute(text("""
            DELETE FROM user_org_memberships WHERE id NOT IN (
                SELECT MIN(id) FROM user_org_memberships GROUP BY org_id, remote_user
            )
        """))
        await conn.execute(text("""
            DELETE FROM org_settings WHERE id NOT IN (
                SELECT MIN(id) FROM org_settings GROUP BY org_id, key
            )
        """))

        for idx_sql in index_migrations:
            await conn.execute(text(idx_sql))

        # ── Phase 36 — Multi-tenant org backfill ────────────────────────────────
        # Step 1: Ensure default org exists
        await conn.execute(text(_upsert_sql("""
            INSERT INTO organizations (id, name, slug, is_active, created_at, updated_at)
            VALUES (:id, :name, 'default', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
        """, dialect_name)), {"id": DEFAULT_ORG_ID, "name": DEFAULT_ORG_NAME})

        # Step 2: Backfill all existing systems to default org
        await conn.execute(text("""
            UPDATE systems SET org_id = :org_id WHERE org_id IS NULL
        """), {"org_id": DEFAULT_ORG_ID})

        # Step 3: Create org memberships for all existing users → default org, role=member
        await conn.execute(text(_upsert_sql("""
            INSERT INTO user_org_memberships (org_id, remote_user, org_role, joined_at, is_active)
            SELECT :org_id, remote_user, 'member', CURRENT_TIMESTAMP, 1
            FROM user_profiles
            ON CONFLICT DO NOTHING
        """, dialect_name)), {"org_id": DEFAULT_ORG_ID})

        # Seed default feed sources (INSERT OR IGNORE — never overwrites admin changes)
        for key, cfg in FEED_ALLOWLIST.items():
            await conn.execute(text(
                _upsert_sql(
                    "INSERT INTO feed_sources (key, name, url, enabled, sort_order) "
                    "VALUES (:key, :name, :url, :enabled, :sort_order) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name)
            ), {"key": key, "name": cfg["name"], "url": cfg["url"],
                "enabled": 1 if cfg["enabled"] else 0, "sort_order": cfg["sort_order"]})

        # ── Phase 31 — Reclassify compliance_frameworks by kind ─────────────────
        # These are idempotent UPDATEs — safe to re-run on every startup.

        # Reclassify existing entries
        _cf_kinds: list[tuple[str, str, str, str]] = [
            # (short_name, new_kind, new_category, new_name_or_None)
            # ── Reclassify to overlay ───────────────────────────────────────────
            ("fedramp",    "overlay",    "federal",     "FedRAMP Overlay"),
            ("sp800171",   "overlay",    "federal",     None),
            ("cmmc2",      "regulation", "contractor",  "CMMC 2.0"),
            ("cis8",       "catalog",    "industry",    None),
            # ── Reclassify to framework ─────────────────────────────────────────
            ("csf2",       "framework",  "industry",    None),
            ("ssdf",       "framework",  "industry",    None),
            ("cis8",       "framework",  "industry",    None),
            ("csaccm",     "framework",  "industry",    None),
            ("isa62443",   "framework",  "industry",    None),
            ("iso27001",   "catalog",    "industry",    "ISO/IEC 27001:2022"),
            ("soc1",       "framework",  "financial",   None),
            ("soc2",       "framework",  "industry",    None),
            ("swiftcsp",   "overlay",    "financial",   None),
            ("tisax",      "framework",  "industry",    None),
            # ── Reclassify to regulation ────────────────────────────────────────
            ("fisma",      "regulation", "federal",     None),
            ("pcidss",     "regulation", "financial",   None),
            ("hipaa",      "regulation", "healthcare",  None),
            ("hitech",     "regulation", "healthcare",  None),
            ("gdpr",       "regulation", "privacy",     None),
            ("ccpa",       "regulation", "privacy",     None),
            ("lgpd",       "regulation", "privacy",     None),
            ("appi",       "regulation", "privacy",     None),
            ("pipeda",     "regulation", "privacy",     None),
            ("sox",        "regulation", "financial",   None),
            ("glba",       "regulation", "financial",   None),
            ("nydfs500",   "regulation", "financial",   None),
            ("naic",       "regulation", "financial",   None),
            ("basel3",     "regulation", "financial",   None),
            ("ffiec",      "regulation", "financial",   None),
            ("cfr11",      "regulation", "healthcare",  None),
            ("fdamdcyber", "regulation", "healthcare",  None),
            ("nerccip",    "regulation", "industry",    None),
            ("tsapipeline","regulation", "industry",    None),
        ]
        for sn, kind, cat, newname in _cf_kinds:
            if newname:
                await conn.execute(text(
                    "UPDATE compliance_frameworks SET kind=:k, category=:c, name=:n WHERE short_name=:sn"
                ), {"k": kind, "c": cat, "n": newname, "sn": sn})
            else:
                await conn.execute(text(
                    "UPDATE compliance_frameworks SET kind=:k, category=:c WHERE short_name=:sn"
                ), {"k": kind, "c": cat, "sn": sn})
        # Set ISO 27001 description if blank
        await conn.execute(text(
            "UPDATE compliance_frameworks SET "
            "description = 'ISO/IEC 27001:2022 information security management system standard. "
            "93 Annex A controls across 4 themes: Organizational, People, Physical, and Technological. "
            "Used as the primary catalog for commercial, international, and non-federal programs.' "
            "WHERE short_name='iso27001' AND (description IS NULL OR description='')"
        ))

        # Seed missing catalog + baseline + overlay entries (INSERT OR IGNORE)
        _cf_seed: list[dict] = [
            # ── Catalogs ────────────────────────────────────────────────────────
            {"sn": "nist80053r5", "name": "NIST SP 800-53 Rev 5",
             "kind": "catalog", "cat": "federal", "pub": "NIST",
             "desc": "The authoritative security and privacy control catalog for federal information systems. "
                     "Baselines (Low/Moderate/High) and overlays (FedRAMP, Privacy, ICS) derive from this catalog."},
            # iso27001 already exists as a row — migration above sets kind=catalog; desc handled below
            # ── Baselines ───────────────────────────────────────────────────────
            {"sn": "iso27001_annex_a", "name": "ISO 27001 Annex A (Full)",
             "kind": "baseline", "cat": "industry", "pub": "ISO",
             "desc": "All 93 Annex A controls from ISO/IEC 27001:2022 across 4 themes: "
                     "Organizational, People, Physical, and Technological."},
            {"sn": "iso27001_core",   "name": "ISO 27001 Annex A (Core)",
             "kind": "baseline", "cat": "industry", "pub": "ISO",
             "desc": "~50 essential Annex A controls applicable to most organisations. "
                     "A practical starting point; refine applicability via Statement of Applicability (SoA)."},
            {"sn": "nist_low",    "name": "NIST SP 800-53 Low Baseline",
             "kind": "baseline",  "cat": "federal", "pub": "NIST",
             "desc": "~125 controls selected from 800-53r5 for Low-impact systems (FIPS 199 Low)."},
            {"sn": "nist_mod",    "name": "NIST SP 800-53 Moderate Baseline",
             "kind": "baseline",  "cat": "federal", "pub": "NIST",
             "desc": "~325 controls selected from 800-53r5 for Moderate-impact systems (FIPS 199 Moderate). "
                     "Most federal systems operate at this baseline."},
            {"sn": "nist_high",   "name": "NIST SP 800-53 High Baseline",
             "kind": "baseline",  "cat": "federal", "pub": "NIST",
             "desc": "~421 controls selected from 800-53r5 for High-impact systems (FIPS 199 High). "
                     "Required for systems handling classified or highly sensitive data."},
            {"sn": "nist_all",    "name": "NIST SP 800-53 Complete Catalog",
             "kind": "baseline",  "cat": "federal", "pub": "NIST",
             "desc": "All ~1000+ controls and control enhancements from NIST SP 800-53 Rev 5. "
                     "Use when full coverage review is needed or when no standard baseline applies."},
            {"sn": "user_generated", "name": "User Generated (Questionnaire)",
             "kind": "baseline",  "cat": "industry",
             "desc": "Controls determined through an applicability questionnaire completed by the system owner. "
                     "Produces a tailored control set based on system characteristics and operational context."},
            # ── CMMC 2.0 level baselines ─────────────────────────────────────
            {"sn": "cmmc_l1", "name": "CMMC Level 1 — Foundational",
             "kind": "baseline", "cat": "contractor", "pub": "DoD",
             "desc": "17 practices covering basic cyber hygiene for FCI protection. "
                     "Aligns with FAR 52.204-21. Annual self-assessment."},
            {"sn": "cmmc_l2", "name": "CMMC Level 2 — Advanced",
             "kind": "baseline", "cat": "contractor", "pub": "DoD",
             "desc": "110 practices aligned to NIST SP 800-171 Rev 2 for CUI protection. "
                     "Third-party assessment required for critical programs; self-assessment for others."},
            {"sn": "cmmc_l3", "name": "CMMC Level 3 — Expert",
             "kind": "baseline", "cat": "contractor", "pub": "DoD",
             "desc": "110+ practices from NIST SP 800-172 for highest-priority CUI programs. "
                     "Government-led assessment required."},
            # ── CIS Controls v8 implementation group baselines ───────────────
            {"sn": "cis_ig1", "name": "CIS Controls v8 — IG1 (Basic Cyber Hygiene)",
             "kind": "baseline", "cat": "industry", "pub": "CIS",
             "desc": "56 safeguards covering essential cyber hygiene for small organizations "
                     "with limited IT resources. Protects against the most common attacks."},
            {"sn": "cis_ig2", "name": "CIS Controls v8 — IG2 (Foundational)",
             "kind": "baseline", "cat": "industry", "pub": "CIS",
             "desc": "74 additional safeguards for organizations with moderate IT complexity. "
                     "Addresses targeted attacks and data sensitivity. Includes all IG1."},
            {"sn": "cis_ig3", "name": "CIS Controls v8 — IG3 (Organizational)",
             "kind": "baseline", "cat": "industry", "pub": "CIS",
             "desc": "18 additional safeguards for mature organizations with significant IT. "
                     "Addresses sophisticated adversaries. Includes all IG1 and IG2."},
            # ── Overlays ────────────────────────────────────────────────────────
            {"sn": "nist_privacy", "name": "NIST Privacy Overlay",
             "kind": "overlay",   "cat": "federal", "pub": "NIST",
             "desc": "SP 800-53B Appendix J — additional privacy controls applied on top of any baseline "
                     "for systems that process PII. Required when Privacy Act applies."},
            {"sn": "nist_ics",    "name": "ICS/SCADA Overlay (NIST SP 800-82)",
             "kind": "overlay",   "cat": "industry", "pub": "NIST",
             "desc": "NIST SP 800-82 Rev 3 overlay for industrial control systems and operational technology. "
                     "Adjusts 800-53 controls for OT/ICS/SCADA environments."},
            {"sn": "dod_srg",     "name": "DoD Cloud Computing SRG Overlay",
             "kind": "overlay",   "cat": "federal", "pub": "DoD",
             "desc": "Department of Defense Cloud Computing Security Requirements Guide overlay, "
                     "applied on top of FedRAMP for DoD cloud workloads."},
            # ── Privacy overlays / frameworks ────────────────────────────────────
            {"sn": "iso27701", "name": "ISO/IEC 27701:2019",
             "kind": "overlay",   "cat": "industry", "pub": "ISO",
             "desc": "Privacy Information Management System (PIMS) extension to ISO/IEC 27001. "
                     "Specifies requirements and guidance for PII controllers and processors. "
                     "Maps directly to GDPR, CCPA, and other privacy regulations."},
            {"sn": "iso27017", "name": "ISO/IEC 27017:2015",
             "kind": "overlay",   "cat": "industry", "pub": "ISO",
             "desc": "Code of Practice for Information Security Controls for Cloud Services. "
                     "Extension to ISO 27001 providing cloud-specific implementation guidance "
                     "for both cloud service providers and customers."},
            {"sn": "iso27018", "name": "ISO/IEC 27018:2019",
             "kind": "overlay",   "cat": "industry", "pub": "ISO",
             "desc": "Code of Practice for Protection of Personally Identifiable Information (PII) "
                     "in public cloud computing environments. Extension to ISO 27001 addressing "
                     "PII processor obligations and privacy controls for cloud services."},
            {"sn": "npf",      "name": "NIST Privacy Framework v1.0",
             "kind": "framework", "cat": "federal",  "pub": "NIST",
             "desc": "NIST Privacy Framework (January 2020) — 5 functions (Identify-P, Govern-P, "
                     "Control-P, Communicate-P, Protect-P), 18 categories, ~100 subcategories. "
                     "Maps to GDPR, CCPA, ISO 27701, and NIST SP 800-53 Privacy Controls."},
        ]
        for e in _cf_seed:
            await conn.execute(text(_upsert_sql(
                "INSERT INTO compliance_frameworks "
                "(id, name, short_name, kind, category, published_by, description, is_active, created_at) "
                "VALUES (:id, :name, :sn, :kind, :cat, :pub, :desc, 1, CURRENT_TIMESTAMP) "
                "ON CONFLICT DO NOTHING",
                dialect_name
            )), {"id": str(uuid.uuid4()).replace("-", ""), "name": e["name"], "sn": e["sn"],
                "kind": e["kind"], "cat": e["cat"], "pub": e.get("pub"), "desc": e.get("desc")})

        # ── Phase 32 — Seed ISO 27001:2022 Annex A controls ─────────────────────
        # All 93 controls grouped into 4 themes (Organizational / People / Physical / Technological)
        _ISO27001_CONTROLS: list[tuple[str, str, str]] = [
            # (control_id, title, domain)
            # Organizational (A.5)
            ("A.5.1",  "Policies for information security",                                       "Organizational"),
            ("A.5.2",  "Information security roles and responsibilities",                          "Organizational"),
            ("A.5.3",  "Segregation of duties",                                                   "Organizational"),
            ("A.5.4",  "Management responsibilities",                                              "Organizational"),
            ("A.5.5",  "Contact with authorities",                                                 "Organizational"),
            ("A.5.6",  "Contact with special interest groups",                                     "Organizational"),
            ("A.5.7",  "Threat intelligence",                                                      "Organizational"),
            ("A.5.8",  "Information security in project management",                               "Organizational"),
            ("A.5.9",  "Inventory of information and other associated assets",                     "Organizational"),
            ("A.5.10", "Acceptable use of information and other associated assets",                "Organizational"),
            ("A.5.11", "Return of assets",                                                         "Organizational"),
            ("A.5.12", "Classification of information",                                            "Organizational"),
            ("A.5.13", "Labelling of information",                                                 "Organizational"),
            ("A.5.14", "Information transfer",                                                     "Organizational"),
            ("A.5.15", "Access control",                                                           "Organizational"),
            ("A.5.16", "Identity management",                                                      "Organizational"),
            ("A.5.17", "Authentication information",                                               "Organizational"),
            ("A.5.18", "Access rights",                                                            "Organizational"),
            ("A.5.19", "Information security in supplier relationships",                           "Organizational"),
            ("A.5.20", "Addressing information security within supplier agreements",               "Organizational"),
            ("A.5.21", "Managing information security in the ICT supply chain",                   "Organizational"),
            ("A.5.22", "Monitoring, review and change management of supplier services",            "Organizational"),
            ("A.5.23", "Information security for use of cloud services",                           "Organizational"),
            ("A.5.24", "Information security incident management planning and preparation",        "Organizational"),
            ("A.5.25", "Assessment and decision on information security events",                   "Organizational"),
            ("A.5.26", "Response to information security incidents",                               "Organizational"),
            ("A.5.27", "Learning from information security incidents",                             "Organizational"),
            ("A.5.28", "Collection of evidence",                                                   "Organizational"),
            ("A.5.29", "Information security during disruption",                                   "Organizational"),
            ("A.5.30", "ICT readiness for business continuity",                                    "Organizational"),
            ("A.5.31", "Legal, statutory, regulatory and contractual requirements",                "Organizational"),
            ("A.5.32", "Intellectual property rights",                                             "Organizational"),
            ("A.5.33", "Protection of records",                                                    "Organizational"),
            ("A.5.34", "Privacy and protection of personally identifiable information",            "Organizational"),
            ("A.5.35", "Independent review of information security",                               "Organizational"),
            ("A.5.36", "Compliance with policies, rules and standards for information security",   "Organizational"),
            ("A.5.37", "Documented operating procedures",                                          "Organizational"),
            # People (A.6)
            ("A.6.1",  "Screening",                                                                "People"),
            ("A.6.2",  "Terms and conditions of employment",                                       "People"),
            ("A.6.3",  "Information security awareness, education and training",                   "People"),
            ("A.6.4",  "Disciplinary process",                                                     "People"),
            ("A.6.5",  "Responsibilities after termination or change of employment",               "People"),
            ("A.6.6",  "Confidentiality or non-disclosure agreements",                             "People"),
            ("A.6.7",  "Remote working",                                                           "People"),
            ("A.6.8",  "Information security event reporting",                                     "People"),
            # Physical (A.7)
            ("A.7.1",  "Physical security perimeters",                                             "Physical"),
            ("A.7.2",  "Physical entry",                                                           "Physical"),
            ("A.7.3",  "Securing offices, rooms and facilities",                                   "Physical"),
            ("A.7.4",  "Physical security monitoring",                                             "Physical"),
            ("A.7.5",  "Protecting against physical and environmental threats",                    "Physical"),
            ("A.7.6",  "Working in secure areas",                                                  "Physical"),
            ("A.7.7",  "Clear desk and clear screen",                                              "Physical"),
            ("A.7.8",  "Equipment siting and protection",                                          "Physical"),
            ("A.7.9",  "Security of assets off-premises",                                          "Physical"),
            ("A.7.10", "Storage media",                                                            "Physical"),
            ("A.7.11", "Supporting utilities",                                                     "Physical"),
            ("A.7.12", "Cabling security",                                                         "Physical"),
            ("A.7.13", "Equipment maintenance",                                                    "Physical"),
            ("A.7.14", "Secure disposal or re-use of equipment",                                   "Physical"),
            # Technological (A.8)
            ("A.8.1",  "User endpoint devices",                                                    "Technological"),
            ("A.8.2",  "Privileged access rights",                                                 "Technological"),
            ("A.8.3",  "Information access restriction",                                           "Technological"),
            ("A.8.4",  "Access to source code",                                                    "Technological"),
            ("A.8.5",  "Secure authentication",                                                    "Technological"),
            ("A.8.6",  "Capacity management",                                                      "Technological"),
            ("A.8.7",  "Protection against malware",                                               "Technological"),
            ("A.8.8",  "Management of technical vulnerabilities",                                  "Technological"),
            ("A.8.9",  "Configuration management",                                                 "Technological"),
            ("A.8.10", "Information deletion",                                                     "Technological"),
            ("A.8.11", "Data masking",                                                             "Technological"),
            ("A.8.12", "Data leakage prevention",                                                  "Technological"),
            ("A.8.13", "Information backup",                                                       "Technological"),
            ("A.8.14", "Redundancy of information processing facilities",                          "Technological"),
            ("A.8.15", "Logging",                                                                   "Technological"),
            ("A.8.16", "Monitoring activities",                                                    "Technological"),
            ("A.8.17", "Clock synchronization",                                                    "Technological"),
            ("A.8.18", "Use of privileged utility programs",                                       "Technological"),
            ("A.8.19", "Installation of software on operational systems",                          "Technological"),
            ("A.8.20", "Networks security",                                                        "Technological"),
            ("A.8.21", "Security of network services",                                             "Technological"),
            ("A.8.22", "Segregation of networks",                                                  "Technological"),
            ("A.8.23", "Web filtering",                                                            "Technological"),
            ("A.8.24", "Use of cryptography",                                                      "Technological"),
            ("A.8.25", "Secure development life cycle",                                            "Technological"),
            ("A.8.26", "Application security requirements",                                        "Technological"),
            ("A.8.27", "Secure system architecture and engineering principles",                    "Technological"),
            ("A.8.28", "Secure coding",                                                            "Technological"),
            ("A.8.29", "Security testing in development and acceptance",                           "Technological"),
            ("A.8.30", "Outsourced development",                                                   "Technological"),
            ("A.8.31", "Separation of development, test and production environments",              "Technological"),
            ("A.8.32", "Change management",                                                        "Technological"),
            ("A.8.33", "Test information",                                                         "Technological"),
            ("A.8.34", "Protection of information systems during audit testing",                   "Technological"),
        ]
        # Resolve iso27001 framework_id
        iso_row = await conn.execute(
            text("SELECT id FROM compliance_frameworks WHERE short_name='iso27001' LIMIT 1")
        )
        iso_id = iso_row.scalar()
        if iso_id:
            for ctrl_id, title, domain in _ISO27001_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO framework_controls "
                    "(framework_id, control_id, title, domain) "
                    "VALUES (:fw, :cid, :title, :dom) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"fw": iso_id, "cid": ctrl_id, "title": title, "dom": domain})

        # ── ISO/IEC 27701:2019 — Privacy extension to ISO 27001 ──────────────────
        _ISO27701_CONTROLS: list[tuple[str, str, str]] = [
            # Section 7 — PII Controller controls
            ("7.2.1",  "Identify and document purpose",                                        "Controller"),
            ("7.2.2",  "Identify lawful basis",                                                "Controller"),
            ("7.2.3",  "Determine when and how consent is to be obtained",                     "Controller"),
            ("7.2.4",  "Assess necessity and proportionality of processing",                   "Controller"),
            ("7.2.5",  "Privacy risk assessment",                                              "Controller"),
            ("7.2.6",  "Privacy by design and privacy by default",                             "Controller"),
            ("7.2.7",  "PII inventories",                                                      "Controller"),
            ("7.2.8",  "Use, retention and disposal of PII",                                   "Controller"),
            ("7.3.1",  "Obligations to PII principals — determine legitimate interest",        "Controller"),
            ("7.3.2",  "Obligations to PII principals — controller responsibilities",          "Controller"),
            ("7.3.3",  "Privacy notice to PII principal",                                      "Controller"),
            ("7.3.4",  "Provide mechanism to modify or withdraw consent",                      "Controller"),
            ("7.3.5",  "Provide privacy notice in specific cases",                             "Controller"),
            ("7.4.1",  "Limit collection of PII to what is necessary",                         "Controller"),
            ("7.4.2",  "Limit processing of PII",                                              "Controller"),
            ("7.4.3",  "Accuracy and quality of PII",                                          "Controller"),
            ("7.4.4",  "PII minimization objectives",                                          "Controller"),
            ("7.4.5",  "PII de-identification and deletion at end of processing",              "Controller"),
            ("7.4.6",  "Temporary files",                                                      "Controller"),
            ("7.4.7",  "Retention of PII",                                                     "Controller"),
            ("7.4.8",  "Disposal of PII",                                                      "Controller"),
            ("7.4.9",  "PII transmission controls",                                            "Controller"),
            ("7.5.1",  "Identify basis for PII transfer between jurisdictions",                "Controller"),
            ("7.5.2",  "Countries and organizations to which PII can be transferred",          "Controller"),
            ("7.5.3",  "Records of transfer of PII to third parties",                          "Controller"),
            ("7.6.1",  "Determine the need to share PII with third parties",                   "Controller"),
            ("7.6.2",  "Sharing PII with third parties",                                       "Controller"),
            ("7.6.3",  "Third party PII disclosure notification",                              "Controller"),
            ("7.7.1",  "Roles and responsibilities for PII subject request handling",          "Controller"),
            ("7.7.2",  "How to fulfill PII subject requests",                                  "Controller"),
            ("7.7.3",  "Communication to PII subjects",                                        "Controller"),
            ("7.8.1",  "Assess data protection implications of sharing groups of PII",         "Controller"),
            ("7.8.2",  "Records related to processing PII",                                    "Controller"),
            ("7.8.3",  "Security of PII processing",                                           "Controller"),
            ("7.8.4",  "Record of transfers of PII to third parties",                          "Controller"),
            ("7.8.5",  "Communication of PII breaches to supervisory authorities",             "Controller"),
            # Section 8 — PII Processor controls
            ("8.2.1",  "Customer agreement",                                                   "Processor"),
            ("8.2.2",  "Processor's purposes",                                                 "Processor"),
            ("8.2.3",  "Marketing and advertising use restriction",                            "Processor"),
            ("8.2.4",  "Handling infringing instructions from customers",                      "Processor"),
            ("8.2.5",  "Customer obligations on behalf of the processor",                      "Processor"),
            ("8.2.6",  "Records related to processing PII as a processor",                     "Processor"),
            ("8.3.1",  "Obligations to PII principals (processor)",                            "Processor"),
            ("8.4.1",  "Basis for PII transfer between jurisdictions (processor)",             "Processor"),
            ("8.4.2",  "Countries and organizations to which PII can be transferred",          "Processor"),
            ("8.4.3",  "Records of transfers of PII to third parties (processor)",             "Processor"),
            ("8.5.1",  "Engagement and management of sub-processors",                          "Processor"),
            ("8.5.2",  "Agreements with sub-processors",                                       "Processor"),
            ("8.5.3",  "Sub-processor access to PII",                                          "Processor"),
            ("8.5.4",  "Change of sub-processor",                                              "Processor"),
            ("8.5.5",  "Contracts with customers (processor)",                                 "Processor"),
            ("8.5.6",  "Independent determination of business purposes by sub-processor",      "Processor"),
            ("8.5.7",  "Notification of sub-processors",                                       "Processor"),
        ]
        iso27701_row = await conn.execute(
            text("SELECT id FROM compliance_frameworks WHERE short_name='iso27701' LIMIT 1")
        )
        iso27701_id = iso27701_row.scalar()
        if iso27701_id:
            for ctrl_id, title, domain in _ISO27701_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO framework_controls "
                    "(framework_id, control_id, title, domain) "
                    "VALUES (:fw, :cid, :title, :dom) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"fw": iso27701_id, "cid": ctrl_id, "title": title, "dom": domain})
            for ctrl_id, title, domain in _ISO27701_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO catalog_controls "
                    "(id, framework_id, control_id, title, domain, created_at) "
                    "VALUES (:id, :fw, :cid, :title, :dom, CURRENT_TIMESTAMP) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"id": str(uuid.uuid4()), "fw": iso27701_id,
                    "cid": ctrl_id, "title": title, "dom": domain})

        # ── ISO/IEC 27017:2015 — Cloud Security Controls ──────────────────────────
        _ISO27017_CONTROLS: list[tuple[str, str, str]] = [
            # ── New cloud-specific controls (CLD) ────────────────────────────────
            ("CLD.6.3.1",  "Shared roles and responsibilities within a cloud computing environment", "Organisation"),
            ("CLD.8.1.5",  "Removal of cloud service customer assets",                              "Asset Management"),
            ("CLD.9.5.1",  "Segregation in virtual computing environments",                         "Access Control"),
            ("CLD.9.5.2",  "Virtual machine hardening",                                             "Access Control"),
            ("CLD.12.1.5", "Administrator's operational security",                                  "Operations Security"),
            ("CLD.12.4.5", "Monitoring of cloud services",                                          "Operations Security"),
            ("CLD.13.1.4", "Alignment of security management for virtual and physical networks",    "Communications Security"),
            # ── Extended guidance for existing ISO 27001 controls ────────────────
            ("A.5.1.1",  "Policies for information security (cloud context)",                        "Information Security Policies"),
            ("A.6.1.1",  "Information security roles and responsibilities in cloud environments",    "Organisation"),
            ("A.6.1.2",  "Segregation of duties in cloud service delivery",                          "Organisation"),
            ("A.7.2.1",  "Management responsibilities for cloud service security",                   "Human Resource Security"),
            ("A.7.2.2",  "Information security awareness and training for cloud services",           "Human Resource Security"),
            ("A.8.1.1",  "Inventory of cloud service assets",                                        "Asset Management"),
            ("A.8.1.2",  "Ownership of cloud service assets",                                        "Asset Management"),
            ("A.8.2.1",  "Classification of information processed in cloud environments",            "Asset Management"),
            ("A.9.1.1",  "Access control policy for cloud services",                                 "Access Control"),
            ("A.9.1.2",  "Access to cloud networks and cloud network services",                      "Access Control"),
            ("A.9.2.3",  "Management of privileged access rights in cloud environments",             "Access Control"),
            ("A.9.4.1",  "Information access restriction in cloud service environments",             "Access Control"),
            ("A.9.4.4",  "Use of privileged utility programs in cloud environments",                 "Access Control"),
            ("A.10.1.1", "Cryptographic key management policy for cloud services",                   "Cryptography"),
            ("A.11.1.1", "Physical security perimeter considerations for cloud data centres",        "Physical Security"),
            ("A.12.1.1", "Documented operating procedures for cloud service operations",             "Operations Security"),
            ("A.12.1.2", "Change management for cloud service environments",                         "Operations Security"),
            ("A.12.3.1", "Backup of cloud service customer information",                             "Operations Security"),
            ("A.12.4.1", "Event logging in cloud service environments",                              "Operations Security"),
            ("A.12.4.3", "Administrator and operator logs for cloud services",                       "Operations Security"),
            ("A.12.6.1", "Technical vulnerability management in cloud environments",                 "Operations Security"),
            ("A.13.1.1", "Network controls for cloud service environments",                          "Communications Security"),
            ("A.13.1.2", "Security of cloud network services",                                       "Communications Security"),
            ("A.13.1.3", "Segregation in cloud networks",                                            "Communications Security"),
            ("A.14.2.5", "Secure system engineering principles for cloud services",                  "System Development"),
            ("A.15.1.1", "Cloud service supply chain information security policy",                   "Supplier Relationships"),
            ("A.15.1.2", "Addressing security within cloud service agreements",                      "Supplier Relationships"),
            ("A.16.1.2", "Reporting cloud information security events",                              "Incident Management"),
            ("A.16.1.3", "Reporting cloud information security weaknesses",                          "Incident Management"),
            ("A.18.1.3", "Protection of cloud-stored records",                                       "Compliance"),
            ("A.18.1.4", "Privacy and protection of PII in cloud environments",                      "Compliance"),
            ("A.18.2.3", "Technical compliance review for cloud service environments",               "Compliance"),
        ]
        iso27017_row = await conn.execute(
            text("SELECT id FROM compliance_frameworks WHERE short_name='iso27017' LIMIT 1")
        )
        iso27017_id = iso27017_row.scalar()
        if iso27017_id:
            for ctrl_id, title, domain in _ISO27017_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO framework_controls "
                    "(framework_id, control_id, title, domain) "
                    "VALUES (:fw, :cid, :title, :dom) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"fw": iso27017_id, "cid": ctrl_id, "title": title, "dom": domain})
            for ctrl_id, title, domain in _ISO27017_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO catalog_controls "
                    "(id, framework_id, control_id, title, domain, created_at) "
                    "VALUES (:id, :fw, :cid, :title, :dom, CURRENT_TIMESTAMP) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"id": str(uuid.uuid4()), "fw": iso27017_id,
                    "cid": ctrl_id, "title": title, "dom": domain})

        # ── ISO/IEC 27018:2019 — Protection of PII in Public Clouds ───────────────
        _ISO27018_CONTROLS: list[tuple[str, str, str]] = [
            # ── Annex A — Additional cloud privacy controls ───────────────────────
            ("A.1.1",  "Obligation to cooperate regarding PII principals' rights",                   "Consent and Choice"),
            ("A.1.2",  "Obligation to inform PII principals of cloud processor sub-contractors",     "Consent and Choice"),
            ("A.2.1",  "Adherence to public cloud PII processor purpose declaration",                "Purpose Legitimacy"),
            ("A.3.1",  "Obligations to PII principals — data minimisation",                         "Collection Limitation"),
            ("A.4.1",  "Limit use of PII for public cloud services to specified purposes",           "Data Minimisation"),
            ("A.5.1",  "Use of PII — restrict use to contracted purposes only",                     "Use and Retention"),
            ("A.5.2",  "Temporary files containing PII — secure handling and deletion",             "Use and Retention"),
            ("A.5.3",  "Provision of information on PII sub-processing to cloud customers",         "Use and Retention"),
            ("A.5.4",  "Disclosure of PII to law enforcement — notification to customer",           "Use and Retention"),
            ("A.5.5",  "Notification of data requests — inform cloud customer promptly",            "Use and Retention"),
            ("A.6.1",  "Return, transfer and disposal of PII at end of contract",                   "Accuracy and Quality"),
            ("A.7.1",  "Disclosure of PII sub-processors — maintain and provide list",              "Openness and Transparency"),
            ("A.7.2",  "Notification if PII cannot be returned or irreversibly destroyed",          "Openness and Transparency"),
            ("A.7.3",  "Records of PII processing activities",                                       "Openness and Transparency"),
            ("A.8.1",  "Access by PII principals — support cloud customer in fulfilling requests",  "Individual Participation"),
            ("A.9.1",  "Notification of changes to sub-contracted PII processors",                  "Accountability"),
            ("A.9.2",  "Audit log access and modification records for PII processing",              "Accountability"),
            ("A.10.1", "Restriction on creating hard-copy material containing PII",                 "Information Security"),
            ("A.10.2", "Restriction on use of unmanaged removable storage media for PII",           "Information Security"),
            ("A.10.3", "Restriction on printing PII",                                               "Information Security"),
            ("A.11.1", "Geolocation restrictions and customer notification for PII storage",        "Privacy Compliance"),
            # ── Extended guidance on ISO 27001/27002 controls for PII in cloud ───
            ("CC.9.1",  "Access control policy — include PII handling requirements",                 "Access Control"),
            ("CC.9.4",  "Use of privileged utility programs — restrict access to PII systems",       "Access Control"),
            ("CC.10.1", "Cryptographic controls for PII at rest and in transit",                     "Cryptography"),
            ("CC.12.3", "PII backup — ensure recoverability and integrity",                          "Operations Security"),
            ("CC.12.4", "Logging of PII access and processing events",                               "Operations Security"),
            ("CC.13.1", "Secure network transmission of PII",                                        "Communications Security"),
            ("CC.15.1", "PII processing requirements in cloud supplier agreements",                  "Supplier Relationships"),
            ("CC.16.1", "PII breach response — notify cloud customers of incidents",                 "Incident Management"),
            ("CC.18.1", "Identification and documentation of applicable PII privacy regulations",    "Compliance"),
        ]
        iso27018_row = await conn.execute(
            text("SELECT id FROM compliance_frameworks WHERE short_name='iso27018' LIMIT 1")
        )
        iso27018_id = iso27018_row.scalar()
        if iso27018_id:
            for ctrl_id, title, domain in _ISO27018_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO framework_controls "
                    "(framework_id, control_id, title, domain) "
                    "VALUES (:fw, :cid, :title, :dom) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"fw": iso27018_id, "cid": ctrl_id, "title": title, "dom": domain})
            for ctrl_id, title, domain in _ISO27018_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO catalog_controls "
                    "(id, framework_id, control_id, title, domain, created_at) "
                    "VALUES (:id, :fw, :cid, :title, :dom, CURRENT_TIMESTAMP) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"id": str(uuid.uuid4()), "fw": iso27018_id,
                    "cid": ctrl_id, "title": title, "dom": domain})

        # ── NIST Privacy Framework v1.0 (January 2020) ───────────────────────────
        _NPF_CONTROLS: list[tuple[str, str, str]] = [
            # ── Identify-P ──────────────────────────────────────────────────────
            ("ID.IM-P1",  "Inventory systems/products/services that process PII",                "Identify-P"),
            ("ID.IM-P2",  "Identify owners/operators of systems that process PII",               "Identify-P"),
            ("ID.IM-P3",  "Identify the organization's role(s) in the data processing ecosystem","Identify-P"),
            ("ID.IM-P4",  "Manage PII consistently with the organization's privacy risk strategy","Identify-P"),
            ("ID.IM-P5",  "Identify and document processes that handle PII",                     "Identify-P"),
            ("ID.IM-P6",  "Identify data processing performed by third parties on your behalf",  "Identify-P"),
            ("ID.IM-P7",  "Identify owners/operators of systems processing PII on your behalf",  "Identify-P"),
            ("ID.IM-P8",  "Inventory systems that process PII on behalf of the organization",    "Identify-P"),
            ("ID.BE-P1",  "Understand the organization's role in the data processing ecosystem", "Identify-P"),
            ("ID.BE-P2",  "Establish priorities for organizational mission and objectives",       "Identify-P"),
            ("ID.BE-P3",  "Establish dependencies and critical functions for critical services",  "Identify-P"),
            ("ID.BE-P4",  "Establish resilience requirements for delivery of critical services",  "Identify-P"),
            ("ID.RA-P1",  "Identify contextual factors related to PII processing",               "Identify-P"),
            ("ID.RA-P2",  "Evaluate PII processing to understand privacy risk to individuals",   "Identify-P"),
            ("ID.RA-P3",  "Identify future processing states requiring updated risk assessments", "Identify-P"),
            ("ID.RA-P4",  "Identify and document privacy risks, likelihood, and impact",          "Identify-P"),
            ("ID.RA-P5",  "Use threats, vulnerabilities, and impacts to understand privacy risk", "Identify-P"),
            ("ID.RA-P6",  "Identify and prioritize risk responses",                              "Identify-P"),
            ("ID.DE-P1",  "Establish data processing ecosystem risk management policies",        "Identify-P"),
            ("ID.DE-P2",  "Identify, prioritize, and assess third parties with data processing roles","Identify-P"),
            ("ID.DE-P3",  "Include privacy requirements in third-party contracts",               "Identify-P"),
            ("ID.DE-P4",  "Routinely assess third parties via audits or evaluations",            "Identify-P"),
            ("ID.DE-P5",  "Conduct response and recovery planning and testing with third parties","Identify-P"),
            # ── Govern-P ────────────────────────────────────────────────────────
            ("GV.PO-P1",  "Establish organizational privacy values and policies",                "Govern-P"),
            ("GV.PO-P2",  "Establish processes to instill privacy values in system development", "Govern-P"),
            ("GV.PO-P3",  "Establish privacy roles and responsibilities for the workforce",      "Govern-P"),
            ("GV.PO-P4",  "Establish and manage privacy risk management processes",              "Govern-P"),
            ("GV.PO-P5",  "Understand and manage legal and regulatory privacy requirements",     "Govern-P"),
            ("GV.PO-P6",  "Address cybersecurity and privacy risks in governance processes",     "Govern-P"),
            ("GV.RM-P1",  "Establish and manage organizational risk management processes",       "Govern-P"),
            ("GV.RM-P2",  "Determine and clearly express organizational risk tolerance",         "Govern-P"),
            ("GV.RM-P3",  "Inform risk tolerance by the organization's data processing ecosystem role","Govern-P"),
            ("GV.AT-P1",  "Inform and train workforce on organizational privacy policies",       "Govern-P"),
            ("GV.AT-P2",  "Ensure senior executives understand their privacy risk management role","Govern-P"),
            ("GV.AT-P3",  "Ensure privacy personnel understand their roles and responsibilities","Govern-P"),
            ("GV.AT-P4",  "Ensure workforce understands privacy practice responsibilities",      "Govern-P"),
            ("GV.MT-P1",  "Re-evaluate privacy risk on an ongoing basis as conditions change",   "Govern-P"),
            ("GV.MT-P2",  "Review and update privacy practices based on audit/assessment results","Govern-P"),
            ("GV.MT-P3",  "Test and evaluate organizational privacy practices",                  "Govern-P"),
            ("GV.MT-P4",  "Incorporate workforce and public feedback into privacy practices",    "Govern-P"),
            ("GV.MT-P5",  "Evaluate and document privacy performance against policies",          "Govern-P"),
            ("GV.MT-P6",  "Establish a documented approach for handling privacy breaches",       "Govern-P"),
            # ── Control-P ───────────────────────────────────────────────────────
            ("CT.PO-P1",  "Establish policies for authorizing PII processing",                   "Control-P"),
            ("CT.PO-P2",  "Establish policies enabling individuals to review PII",               "Control-P"),
            ("CT.PO-P3",  "Establish policies for maintaining accurate PII",                     "Control-P"),
            ("CT.PO-P4",  "Align PII handling policies with direct privacy notice",              "Control-P"),
            ("CT.DM-P1",  "Process data elements only to support identified purpose(s)",         "Control-P"),
            ("CT.DM-P2",  "Process PII to limit observability and linkability",                  "Control-P"),
            ("CT.DM-P3",  "Process PII only for identified purposes",                            "Control-P"),
            ("CT.DM-P4",  "Follow a system life cycle that accounts for privacy needs",          "Control-P"),
            ("CT.DM-P5",  "Retain PII only as long as needed to fulfill stated purpose(s)",      "Control-P"),
            ("CT.DM-P6",  "Delete or de-identify PII that is no longer needed",                  "Control-P"),
            ("CT.DM-P7",  "Fulfill individual requests for access, correction, and deletion",    "Control-P"),
            ("CT.DM-P8",  "Incorporate individuals' privacy preferences into systems",           "Control-P"),
            ("CT.DM-P9",  "Review audit logs to ensure PII is accessed and used appropriately",  "Control-P"),
            ("CT.DM-P10", "Regularly test privacy controls and protections",                     "Control-P"),
            ("CT.DP-P1",  "Evaluate opportunities to disassociate PII from data actions",        "Control-P"),
            ("CT.DP-P2",  "Use disassociated processing to limit observability of data actions", "Control-P"),
            ("CT.DP-P3",  "Evaluate opportunities to use disassociated processing",              "Control-P"),
            ("CT.DP-P4",  "Implement disassociated processing where appropriate",                "Control-P"),
            ("CT.DP-P5",  "Review privacy architecture for disassociated processing opportunities","Control-P"),
            # ── Communicate-P ───────────────────────────────────────────────────
            ("CM.PO-P1",  "Establish transparency policies",                                     "Communicate-P"),
            ("CM.PO-P2",  "Establish processes for disclosure of privacy notices",               "Communicate-P"),
            ("CM.PO-P3",  "Establish communication policies throughout the data life cycle",     "Communicate-P"),
            ("CM.PO-P4",  "Establish processes for receiving and responding to privacy complaints","Communicate-P"),
            ("CM.AW-P1",  "Establish mechanisms for communicating data processing purposes",      "Communicate-P"),
            ("CM.AW-P2",  "Provide mechanisms for individuals to obtain privacy notices",         "Communicate-P"),
            ("CM.AW-P3",  "Establish mechanisms for communicating consequences of processing",    "Communicate-P"),
            ("CM.AW-P4",  "Make data processing practices understandable to individuals",        "Communicate-P"),
            ("CM.AW-P5",  "Establish mechanisms for obtaining consent from individuals",         "Communicate-P"),
            ("CM.AW-P6",  "Communicate choices available and consequences of exercising them",   "Communicate-P"),
            # ── Protect-P ───────────────────────────────────────────────────────
            ("PR.PO-P1",  "Create and maintain a baseline configuration of IT/ICS systems",      "Protect-P"),
            ("PR.PO-P2",  "Implement a System Development Life Cycle for privacy",               "Protect-P"),
            ("PR.PO-P3",  "Establish configuration change control processes",                    "Protect-P"),
            ("PR.PO-P4",  "Conduct, maintain, and test backups of information",                  "Protect-P"),
            ("PR.PO-P5",  "Meet policy and regulations for the physical operating environment",  "Protect-P"),
            ("PR.PO-P6",  "Destroy data according to policy",                                    "Protect-P"),
            ("PR.PO-P7",  "Improve protection processes based on lessons learned",               "Protect-P"),
            ("PR.PO-P8",  "Share effectiveness of protection technologies",                      "Protect-P"),
            ("PR.PO-P9",  "Maintain incident response, business continuity, and recovery plans", "Protect-P"),
            ("PR.PO-P10", "Test response and recovery plans",                                    "Protect-P"),
            ("PR.AC-P1",  "Manage identities and credentials for authorized individuals and devices","Protect-P"),
            ("PR.AC-P2",  "Manage and protect physical access to assets",                        "Protect-P"),
            ("PR.AC-P3",  "Manage remote access",                                                "Protect-P"),
            ("PR.AC-P4",  "Manage access permissions with least privilege and separation of duties","Protect-P"),
            ("PR.AC-P5",  "Protect network integrity",                                           "Protect-P"),
            ("PR.AC-P6",  "Proof and bind individuals and devices to credentials",               "Protect-P"),
            ("PR.DS-P1",  "Protect PII at rest",                                                 "Protect-P"),
            ("PR.DS-P2",  "Protect PII in transit",                                              "Protect-P"),
            ("PR.DS-P3",  "Formally manage assets throughout removal, transfers, and disposition","Protect-P"),
            ("PR.DS-P4",  "Maintain adequate capacity to ensure availability",                   "Protect-P"),
            ("PR.DS-P5",  "Implement protections against data leaks",                            "Protect-P"),
            ("PR.DS-P6",  "Use integrity checking mechanisms for PII, software, and firmware",   "Protect-P"),
            ("PR.DS-P7",  "Separate development and testing environments from production",       "Protect-P"),
            ("PR.DS-P8",  "Use integrity checking mechanisms to verify hardware integrity",      "Protect-P"),
        ]
        npf_row = await conn.execute(
            text("SELECT id FROM compliance_frameworks WHERE short_name='npf' LIMIT 1")
        )
        npf_id = npf_row.scalar()
        if npf_id:
            for ctrl_id, title, domain in _NPF_CONTROLS:
                await conn.execute(text(_upsert_sql(
                    "INSERT INTO framework_controls "
                    "(framework_id, control_id, title, domain) "
                    "VALUES (:fw, :cid, :title, :dom) "
                    "ON CONFLICT DO NOTHING",
                    dialect_name
                )), {"fw": npf_id, "cid": ctrl_id, "title": title, "dom": domain})

        # ── Phase 33 — OrgEnabledFramework seed ─────────────────────────────────
        # All existing frameworks start enabled (INSERT OR IGNORE — never overwrites admin toggles)
        await conn.execute(text(_upsert_sql(
            "INSERT INTO org_enabled_frameworks (framework_id, is_enabled, enabled_by, enabled_at) "
            "SELECT id, 1, 'system:seed', CURRENT_TIMESTAMP FROM compliance_frameworks "
            "ON CONFLICT DO NOTHING",
            dialect_name
        )))

        # ── Phase 33 — DataAttributeDefinition seed ──────────────────────────────
        _data_attr_seeds = [
            # key, label, short_label, jurisdiction, regulation, privacy_review, co_review, notify, sort
            ("pii",              "Personally Identifiable Information", "PII",
             "US",   "Privacy Act, NIST SP 800-122",          1, 0, 1, 10),
            ("phi",              "Protected Health Information",        "PHI",
             "US",   "HIPAA Privacy Rule",                    1, 0, 1, 20),
            ("ephi",             "Electronic Protected Health Information", "ePHI",
             "US",   "HIPAA Security Rule",                   1, 0, 1, 30),
            ("gdpr",             "GDPR Personal Data",                  "GDPR",
             "EU",   "EU General Data Protection Regulation", 1, 0, 1, 40),
            ("ccpa",             "CCPA Consumer Personal Information",  "CCPA",
             "US-CA","California Consumer Privacy Act",        1, 0, 1, 45),
            ("cui",              "Controlled Unclassified Information", "CUI",
             "US",   "NIST SP 800-171, CMMC, DFARS 252.204-7012", 0, 1, 0, 50),
            ("financial",        "Financial Data",                      "Financial",
             "US",   "SOX, PCI DSS, GLBA",                   0, 1, 0, 60),
            ("public_facing",    "Public Facing System",                "Public",
             None,  None,                                     0, 0, 0, 70),
            ("federal_connection","Federal System Connection",          "Fed-Connect",
             "US",   "FISMA, FedRAMP",                        0, 1, 0, 80),
            ("federal",          "Federal Information System",          "Federal",
             "US",   "FISMA, NIST SP 800-53",                 0, 1, 0, 90),
        ]
        for key, label, short, jur, reg, priv, co, notify, sort in _data_attr_seeds:
            await conn.execute(text(_upsert_sql(
                "INSERT INTO data_attribute_definitions "
                "(key, label, short_label, jurisdiction, regulation, "
                " triggers_privacy_review, triggers_co_review, triggers_notification, sort_order) "
                "VALUES (:key,:label,:short,:jur,:reg,:priv,:co,:notify,:sort) "
                "ON CONFLICT DO NOTHING",
                dialect_name
            )), {"key": key, "label": label, "short": short, "jur": jur, "reg": reg,
                "priv": priv, "co": co, "notify": notify, "sort": sort})

        # ── Phase 33 — Migrate existing System boolean flags → SystemDataAttribute ─
        # Idempotent: INSERT OR IGNORE skips already-migrated rows.
        _flag_map = [
            ("has_pii",              "pii"),
            ("has_phi",              "phi"),
            ("has_ephi",             "ephi"),
            ("has_gdpr_data",        "gdpr"),
            ("has_financial_data",   "financial"),
            ("is_public_facing",     "public_facing"),
            ("has_cui",              "cui"),
            ("connects_to_federal",  "federal_connection"),
            ("is_federal",           "federal"),
        ]
        # col and attr_key are from the hardcoded _flag_map tuple above — no user input.
        for col, attr_key in _flag_map:
            await conn.execute(text(_upsert_sql(
                f"INSERT INTO system_data_attributes "
                f"(system_id, attribute_key, added_by, added_at) "
                f"SELECT id, '{attr_key}', 'migration:p33', CURRENT_TIMESTAMP "
                f"FROM systems WHERE {col} = 1 AND deleted_at IS NULL "
                f"ON CONFLICT DO NOTHING",
                dialect_name
            )))


class SystemSettings(Base):
    """Key-value store for site-wide admin settings (chat_enabled, etc.)."""
    __tablename__ = "system_settings"

    key        = Column(String, primary_key=True)
    value      = Column(Text, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class OrgSettings(Base):
    """Key-value store for per-organization feature flags and settings."""
    __tablename__ = "org_settings"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    org_id     = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    key        = Column(String, nullable=False)
    value      = Column(Text, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("org_id", "key", name="uq_org_settings_key"),)


class UserFeedSubscription(Base):
    """Per-user RSS feed subscription preferences."""
    __tablename__ = "user_feed_subscriptions"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    remote_user = Column(String, nullable=False, index=True)
    feed_key   = Column(String, nullable=False)   # e.g. "krebs", "thn", "cisa_alerts"
    enabled    = Column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("remote_user", "feed_key", name="uq_user_feed"),)


class SspReview(Base):
    """Admin-only SSP upload + AI analysis record."""
    __tablename__ = "ssp_reviews"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename      = Column(String, nullable=False)
    file_path     = Column(String, nullable=False)
    uploaded_by   = Column(String, nullable=False)
    uploaded_at   = Column(DateTime, default=_now)
    system_name   = Column(String, nullable=True)
    impact_level  = Column(String, nullable=True)
    status        = Column(String, default="processing")   # processing|complete|error
    error_message = Column(Text, nullable=True)
    overall_score = Column(Float, default=0.0)             # 0-100 weighted score
    # Counts
    total_controls   = Column(Integer, default=0)
    adequate         = Column(Integer, default=0)
    medium_gap       = Column(Integer, default=0)
    high_gap         = Column(Integer, default=0)
    critical_gap     = Column(Integer, default=0)
    not_found        = Column(Integer, default=0)
    # Full analysis stored as JSON
    analysis_json    = Column(Text, nullable=True)         # JSON list of per-control findings


class RemovedUserReservation(Base):
    """
    Phase 6 — B2: Prevents re-use of a removed user's username/email for 1 year.
    override_granted=True allows a principal-tier admin to bypass the hold.
    """
    __tablename__ = "removed_user_reservations"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    username         = Column(String, nullable=False, index=True)
    email            = Column(String, nullable=True, index=True)
    removed_at       = Column(DateTime, nullable=False)
    hold_until       = Column(DateTime, nullable=False)    # removed_at + 365 days
    removed_by       = Column(String, nullable=False)
    override_granted = Column(Boolean, default=False)
    override_by      = Column(String, nullable=True)
    override_at      = Column(DateTime, nullable=True)
    override_reason  = Column(String, nullable=True)


class IngestJob(Base):
    """Bulk import job for users or systems — preview then commit."""
    __tablename__ = "ingest_jobs"

    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ingest_type    = Column(String, nullable=False)          # users|systems
    status         = Column(String, default="preview")       # preview|committed|error
    filename       = Column(String, nullable=True)
    row_count      = Column(Integer, default=0)              # total parsed rows
    error_count    = Column(Integer, default=0)              # rows skipped (missing required)
    unknown_fields = Column(Text, nullable=True)             # JSON list of unrecognized headers
    data_json      = Column(Text, nullable=True)             # JSON list of normalized rows
    created_by     = Column(String, nullable=True)
    created_at     = Column(DateTime, default=_now)
    committed_by   = Column(String, nullable=True)
    committed_at   = Column(DateTime, nullable=True)
    commit_results = Column(Text, nullable=True)             # JSON summary after commit


# ── Phase 5 — Standards Feeds + Auto-Fail Engine ──────────────────────────────

class NistPublication(Base):
    """
    Metadata cache for NIST publications ingested from the NIST publications feed.
    doc_id: e.g. "SP800-53r5", "SP800-37r2", "FIPS199"
    status: active | draft | withdrawn
    """
    __tablename__ = "nist_publications"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    doc_id       = Column(String, nullable=False, unique=True, index=True)   # normalized ID
    title        = Column(String, nullable=True)
    series       = Column(String, nullable=True)                              # "SP800", "FIPS", etc.
    pub_date     = Column(String, nullable=True)                              # ISO date
    status       = Column(String, default="active")                          # active|draft|withdrawn
    url          = Column(String, nullable=True)
    raw_json     = Column(Text, nullable=True)                               # full API response
    last_fetched = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=_now)


class NvdCve(Base):
    """
    NVD CVE feed cache. Updated by scheduled ingest job.
    cve_id: e.g. "CVE-2024-12345"
    """
    __tablename__ = "nvd_cves"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    cve_id            = Column(String, nullable=False, unique=True, index=True)
    description       = Column(Text, nullable=True)
    cvss_score        = Column(String, nullable=True)                         # "9.8"
    cvss_vector       = Column(String, nullable=True)                         # CVSS:3.1/AV:N/...
    cvss_severity     = Column(String, nullable=True)                         # CRITICAL|HIGH|MEDIUM|LOW
    affected_products = Column(Text, nullable=True)                           # JSON list of CPE strings
    published_date    = Column(String, nullable=True)                         # ISO date
    modified_date     = Column(String, nullable=True)                         # ISO date
    patched_date      = Column(String, nullable=True)                         # ISO date (if known)
    raw_json          = Column(Text, nullable=True)
    last_fetched      = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=_now)


class CisaKevEntry(Base):
    """
    Persistent cache of CISA Known Exploited Vulnerabilities catalog.
    Synced via POST /admin/connectors/kev/sync.  Used for cross-referencing
    against system inventory items to surface relevant patching obligations.
    """
    __tablename__ = "cisa_kev_entries"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    cve_id          = Column(String, nullable=False, unique=True, index=True)  # CVE-YYYY-NNNNN
    vendor_project  = Column(String, nullable=True)
    product         = Column(String, nullable=True)
    vulnerability_name = Column(String, nullable=True)
    short_description  = Column(Text, nullable=True)
    date_added      = Column(String, nullable=True)   # ISO date YYYY-MM-DD
    due_date        = Column(String, nullable=True)   # required remediation date
    required_action = Column(Text, nullable=True)
    ransomware_use  = Column(String, nullable=True)   # Known|Unknown
    notes           = Column(Text, nullable=True)
    last_synced     = Column(DateTime, default=_now)
    created_at      = Column(DateTime, default=_now)


class ControlParameter(Base):
    """
    Per-system baseline parameter tracking for NIST controls.
    Links a specific control parameter (e.g. AC-2 account review frequency) to its
    required value, current enforced value, and source of the requirement.
    """
    __tablename__ = "control_parameters"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    system_id       = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    control_id      = Column(String, nullable=False)                          # e.g. "ac-2"
    parameter_key   = Column(String, nullable=False)                          # e.g. "review_frequency_days"
    required_value  = Column(String, nullable=True)                           # from baseline
    current_value   = Column(String, nullable=True)                           # as configured
    source          = Column(String, nullable=True)                           # nist_baseline|org_policy|ssp
    last_checked    = Column(DateTime, nullable=True)
    drift_detected  = Column(Boolean, default=False)
    notes           = Column(Text, nullable=True)
    created_by      = Column(String, nullable=True)
    created_at      = Column(DateTime, default=_now)
    updated_at      = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint("system_id", "control_id", "parameter_key",
                                                  name="uq_ctrl_param"),
    )


class AutoFailEvent(Base):
    """
    Records each auto-fail trigger evaluation. When a trigger fires,
    this record is created and optionally a POA&M is opened or re-opened.
    trigger_type: parameter_drift|review_overdue|document_expired|evidence_stale|
                  config_drift|patch_sla_breach|governance_drift
    """
    __tablename__ = "auto_fail_events"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=True, index=True)
    trigger_type  = Column(String, nullable=False, index=True)
    control_id    = Column(String, nullable=True)                              # related control
    resource_type = Column(String, nullable=True)                              # document|evidence|config|cve
    resource_id   = Column(String, nullable=True)                              # FK to relevant record
    title         = Column(String, nullable=False)                             # human-readable summary
    details       = Column(Text, nullable=True)                               # JSON provenance data
    severity      = Column(String, default="Moderate")                        # Critical|High|Moderate|Low
    poam_id       = Column(String, ForeignKey("poam_items.id"), nullable=True) # created/linked POA&M
    status        = Column(String, default="open")                            # open|resolved|suppressed
    resolved_at   = Column(DateTime, nullable=True)
    resolved_by   = Column(String, nullable=True)
    created_at    = Column(DateTime, default=_now)
    updated_at    = Column(DateTime, default=_now, onupdate=_now)


class FeedSource(Base):
    """
    LIST4-ITEM3: Admin-configurable advisory feed sources with per-source health tracking.
    Seeded with FEED_ALLOWLIST on first run; admin can toggle enabled/sort_order.
    """
    __tablename__ = "feed_sources"

    key          = Column(String, primary_key=True)       # e.g. "krebs"
    name         = Column(String, nullable=False)
    url          = Column(String, nullable=False, unique=True)
    enabled      = Column(Boolean, default=True)
    sort_order   = Column(Integer, default=0)
    last_fetched = Column(DateTime, nullable=True)
    last_error   = Column(String, nullable=True)          # last error message (if any)
    item_count   = Column(Integer, default=0)             # items in last successful fetch
    error_count  = Column(Integer, default=0)             # consecutive error count (reset on success)
    created_at   = Column(DateTime, default=_now)
    updated_at   = Column(DateTime, default=_now, onupdate=_now)


# Default curated feed allowlist — seeded once in _migrate_db
FEED_ALLOWLIST: dict = {
    "krebs":       {"name": "Krebs on Security",         "url": "https://krebsonsecurity.com/feed",                           "enabled": True,  "sort_order": 1},
    "darkreading": {"name": "Dark Reading",               "url": "https://www.darkreading.com/rss.xml",                        "enabled": True,  "sort_order": 2},
    "bleeping":    {"name": "BleepingComputer",           "url": "https://www.bleepingcomputer.com/feed/",                     "enabled": True,  "sort_order": 3},
    "thn":         {"name": "The Hacker News",            "url": "https://feeds.feedburner.com/TheHackersNews",                "enabled": True,  "sort_order": 4},
    "cisa_alerts": {"name": "CISA Alerts",                "url": "https://www.cisa.gov/uscert/ncas/alerts.xml",                "enabled": True,  "sort_order": 5},
    "cisa_adv":    {"name": "CISA Advisories",            "url": "https://www.cisa.gov/uscert/ncas/advisories.xml",            "enabled": True,  "sort_order": 6},
    "sans":        {"name": "SANS ISC",                   "url": "https://isc.sans.edu/rssfeed_full.xml",                     "enabled": True,  "sort_order": 7},
    "sophos":      {"name": "Sophos News",                "url": "https://news.sophos.com/en-us/feed/",                        "enabled": True,  "sort_order": 8},
    "google":      {"name": "Google Security Blog",       "url": "https://feeds.feedburner.com/GoogleOnlineSecurityBlog",      "enabled": True,  "sort_order": 9},
    "nist":        {"name": "NIST Cybersecurity Insights","url": "https://www.nist.gov/blogs/cybersecurity-insights/rss.xml",  "enabled": True,  "sort_order": 10},
    "govinfo":     {"name": "GovInfoSecurity",            "url": "https://www.govinfosecurity.com/rssFeeds.php",               "enabled": False, "sort_order": 11},
    "cso":         {"name": "CSO Online",                 "url": "https://www.csoonline.com/feed",                            "enabled": False, "sort_order": 12},
    "cisco":       {"name": "Cisco Security Blog",        "url": "https://blogs.cisco.com/security/feed",                     "enabled": False, "sort_order": 13},
    "secledger":   {"name": "The Security Ledger",        "url": "https://feeds.feedblitz.com/thesecurityledger",             "enabled": False, "sort_order": 14},
    # Community & message boards (public RSS, no auth)
    "r_netsec":    {"name": "Reddit /r/netsec",           "url": "https://www.reddit.com/r/netsec/.rss",                      "enabled": True,  "sort_order": 15},
    "r_cyber":     {"name": "Reddit /r/cybersecurity",    "url": "https://www.reddit.com/r/cybersecurity/.rss",               "enabled": False, "sort_order": 16},
    "r_nist":      {"name": "Reddit /r/NISTControls",     "url": "https://www.reddit.com/r/NISTControls/.rss",                "enabled": True,  "sort_order": 17},
    "r_devops":    {"name": "Reddit /r/devopssecurity",   "url": "https://www.reddit.com/r/devopssecurity/.rss",              "enabled": False, "sort_order": 18},
    "fulldisclosure": {"name": "Full Disclosure",         "url": "https://seclists.org/rss/fulldisclosure.rss",               "enabled": True,  "sort_order": 19},
    "packetstorm": {"name": "Packet Storm Security",      "url": "https://rss.packetstormsecurity.com/news/",                 "enabled": True,  "sort_order": 20},
    "talos":       {"name": "Cisco Talos Intelligence",   "url": "https://blog.talosintelligence.com/feeds/posts/default",    "enabled": True,  "sort_order": 21},
    "unit42":      {"name": "Palo Alto Unit 42",          "url": "https://unit42.paloaltonetworks.com/feed/",                 "enabled": False, "sort_order": 22},
    "securelist":  {"name": "Securelist (Kaspersky)",     "url": "https://securelist.com/feed/",                              "enabled": False, "sort_order": 23},
    "projectzero": {"name": "Google Project Zero",        "url": "https://googleprojectzero.blogspot.com/feeds/posts/default","enabled": False, "sort_order": 24},
    "msrc":        {"name": "Microsoft Security Response","url": "https://msrc.microsoft.com/blog/feed",                     "enabled": True,  "sort_order": 25},
    "schneier":    {"name": "Schneier on Security",       "url": "https://www.schneier.com/feed/atom",                        "enabled": True,  "sort_order": 26},
}


# ── Phase 25 — Daily Workflow Stack ───────────────────────────────────────────

class DailyLogbook(Base):
    """Phase 25 — Daily operational task log per user/system/date."""
    __tablename__ = "daily_logbooks"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    remote_user        = Column(String, nullable=False, index=True)
    system_id          = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    log_date           = Column(String, nullable=False)                         # ISO date YYYY-MM-DD
    task_flags         = Column(Text, nullable=True)                            # JSON {"1":bool…"8":bool}
    notes              = Column(Text, nullable=True)
    snap_open_poams    = Column(Integer, default=0)
    snap_overdue_poams = Column(Integer, default=0)
    snap_open_risks    = Column(Integer, default=0)
    snap_open_obs      = Column(Integer, default=0)
    snap_open_incidents = Column(Integer, default=0)
    created_at         = Column(DateTime, default=_now)
    updated_at         = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("remote_user", "system_id", "log_date", name="uq_daily_logbook"),)


class DeepWorkRotation(Base):
    """Phase 25 — Tracks each user's current rotation day per system+role."""
    __tablename__ = "deep_work_rotations"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    remote_user         = Column(String, nullable=False, index=True)
    system_id           = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    role_variant        = Column(String, nullable=False)                        # isso|issm|sca|…
    current_day         = Column(Integer, default=1)                            # 1-25
    last_work_date      = Column(String, nullable=True)                         # ISO date
    paused              = Column(Boolean, default=False)
    quarterly_overrides = Column(Text, nullable=True)                           # JSON
    created_at          = Column(DateTime, default=_now)
    updated_at          = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("remote_user", "system_id", "role_variant", name="uq_deep_work_rotation"),)


class DeepWorkCompletion(Base):
    """Phase 25 — Record of each completed rotation day."""
    __tablename__ = "deep_work_completions"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    rotation_id    = Column(Integer, ForeignKey("deep_work_rotations.id"), nullable=False, index=True)
    remote_user    = Column(String, nullable=False, index=True)
    system_id      = Column(String, ForeignKey("systems.id"), nullable=False)
    rotation_day   = Column(Integer, nullable=False)
    completed_date = Column(String, nullable=False)                             # ISO date
    notes          = Column(Text, nullable=True)
    evidence_path  = Column(String, nullable=True)
    evidence_name  = Column(String, nullable=True)
    created_at     = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("rotation_id", "rotation_day", "completed_date",
                         name="uq_dw_completion_day_date"),
    )


class ChangeReviewRecord(Base):
    """Phase 25 — Task 2: Daily change control review record."""
    __tablename__ = "change_review_records"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    remote_user     = Column(String, nullable=False, index=True)
    system_id       = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    review_date     = Column(String, nullable=False)                            # ISO date
    ticket_refs     = Column(Text, nullable=True)
    high_risk_count = Column(Integer, default=0)
    all_approved    = Column(Boolean, default=True)
    backout_exists  = Column(Boolean, default=True)
    untracked_found = Column(Boolean, default=False)
    obs_id          = Column(String, ForeignKey("observations.id"), nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("remote_user", "system_id", "review_date",
                         name="uq_change_review_user_sys_date"),
    )


class BackupCheckRecord(Base):
    """Phase 25 — Task 4: Daily backup health check."""
    __tablename__ = "backup_check_records"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    remote_user  = Column(String, nullable=False, index=True)
    system_id    = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    check_date   = Column(String, nullable=False)                               # ISO date
    result       = Column(String, default="pass")                               # pass|fail|partial
    ephi_systems = Column(Text, nullable=True)
    job_health   = Column(String, default="ok")                                 # ok|degraded|failed
    issue_raised = Column(Boolean, default=False)
    notes        = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=_now)

    __table_args__ = (UniqueConstraint("remote_user", "system_id", "check_date", name="uq_backup_check"),)


class AccessSpotCheck(Base):
    """Phase 25 — Task 5: Daily access spot-check (HIPAA)."""
    __tablename__ = "access_spot_checks"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    remote_user           = Column(String, nullable=False, index=True)
    system_id             = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    check_date            = Column(String, nullable=False)                      # ISO date
    records_sampled       = Column(Integer, default=0)
    anomaly_found         = Column(Boolean, default=False)
    terminated_user_found = Column(Boolean, default=False)
    anomaly_description   = Column(Text, nullable=True)
    notes                 = Column(Text, nullable=True)
    created_at            = Column(DateTime, default=_now)

    __table_args__ = (UniqueConstraint("remote_user", "system_id", "check_date", name="uq_access_spot_check"),)


class Vendor(Base):
    """Phase 25 — Vendor + BAA registry (Task 7 / Day 12)."""
    __tablename__ = "vendors"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    name          = Column(String, nullable=False)
    service_type  = Column(String, default="other")  # cloud|saas|contractor|data_processor|other
    handles_ephi  = Column(Boolean, default=False)
    has_baa       = Column(Boolean, default=False)
    baa_expiry    = Column(String, nullable=True)                               # ISO date
    contact_name  = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    status        = Column(String, default="active")                            # active|inactive|terminated
    notes         = Column(Text, nullable=True)
    created_by    = Column(String, nullable=True)
    created_at    = Column(DateTime, default=_now)
    updated_at    = Column(DateTime, default=_now, onupdate=_now)


class InterconnectionRecord(Base):
    """Phase 25 — Rotation Day 23: ISA and interconnection tracking."""
    __tablename__ = "interconnection_records"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    system_id            = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    partner_name         = Column(String, nullable=False)
    data_types           = Column(Text, nullable=True)                          # JSON list
    isa_exists           = Column(Boolean, default=False)
    isa_expiry           = Column(String, nullable=True)                        # ISO date
    monitoring_confirmed = Column(Boolean, default=False)
    encrypted_in_transit = Column(Boolean, default=False)
    auth_method          = Column(String, nullable=True)
    notes                = Column(Text, nullable=True)
    last_reviewed        = Column(String, nullable=True)                        # ISO date
    reviewed_by          = Column(String, nullable=True)
    created_at           = Column(DateTime, default=_now)
    updated_at           = Column(DateTime, default=_now, onupdate=_now)


class DataFlowRecord(Base):
    """Phase 25 — Rotation Day 20: Data flow + integration mapping."""
    __tablename__ = "data_flow_records"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    system_id            = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    integration_name     = Column(String, nullable=False)
    auth_method          = Column(String, nullable=True)
    encrypted_in_transit = Column(Boolean, default=False)
    encrypted_at_rest    = Column(Boolean, default=False)
    logging_confirmed    = Column(Boolean, default=False)
    termination_steps    = Column(Text, nullable=True)
    data_types           = Column(Text, nullable=True)                          # JSON list
    last_reviewed        = Column(String, nullable=True)                        # ISO date
    reviewed_by          = Column(String, nullable=True)
    notes                = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=_now)
    updated_at           = Column(DateTime, default=_now, onupdate=_now)


class PrivacyAssessment(Base):
    """Phase 25 — Rotation Day 22: PTA / PIA records."""
    __tablename__ = "privacy_assessments"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    system_id        = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    assess_type      = Column(String, default="pta")                            # pta|pia
    data_elements    = Column(Text, nullable=True)                              # JSON list
    purpose          = Column(Text, nullable=True)
    disclosures      = Column(Text, nullable=True)
    retention_policy = Column(Text, nullable=True)
    access_controls  = Column(Text, nullable=True)
    last_reviewed    = Column(String, nullable=True)                            # ISO date
    reviewer         = Column(String, nullable=True)
    status           = Column(String, default="draft")                          # draft|current|needs_review
    notes            = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=_now)
    updated_at       = Column(DateTime, default=_now, onupdate=_now)


class RestoreTestRecord(Base):
    """Phase 25 — Rotation Day 9: Backup restore test records."""
    __tablename__ = "restore_test_records"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    system_id           = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    test_date           = Column(String, nullable=False)                        # ISO date
    scope               = Column(Text, nullable=True)
    result              = Column(String, default="pass")                        # pass|fail|partial
    time_to_restore_min = Column(Integer, nullable=True)
    validated_by        = Column(String, nullable=True)
    notes               = Column(Text, nullable=True)
    evidence_path       = Column(String, nullable=True)
    created_by          = Column(String, nullable=True)
    created_at          = Column(DateTime, default=_now)


class GeneratedReport(Base):
    """Phase 25 — Tracks background-generated compliance report files."""
    __tablename__ = "generated_reports"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    system_id    = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    remote_user  = Column(String, nullable=False, index=True)
    report_type  = Column(String, nullable=False)
    filename     = Column(String, nullable=True)
    file_path    = Column(String, nullable=True)
    file_size    = Column(Integer, nullable=True)
    status       = Column(String, default="generating")                         # generating|ready|error
    error_msg    = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=_now)


class ReportTemplate(Base):
    """Phase 38 — Admin-uploaded DOCX report templates with Jinja2-style {{variables}}."""
    __tablename__ = "report_templates"

    id             = Column(Integer,  primary_key=True, autoincrement=True)
    name           = Column(String,   nullable=False)
    description    = Column(Text,     nullable=True)
    template_type  = Column(String,   nullable=False, default="custom")
    # custom | executive_summary | sca_pack | bcdr_pack | audit_report | poam_export
    file_path      = Column(String,   nullable=False)   # path under uploads/report_templates/
    original_name  = Column(String,   nullable=False)   # filename as uploaded
    file_size      = Column(Integer,  nullable=True)
    variables_json = Column(Text,     nullable=True)    # JSON list of detected {{variable}} names
    is_active      = Column(Boolean,  default=True,  nullable=False)
    org_id         = Column(String,   ForeignKey("organizations.id"), nullable=True, index=True)
    # NULL = available to all orgs
    created_by     = Column(String,   nullable=False)
    created_at     = Column(DateTime, default=_now)
    updated_at     = Column(DateTime, nullable=True)
    deleted_at     = Column(DateTime, nullable=True)
    deleted_by     = Column(String,   nullable=True)


class EvidenceFile(Base):
    """Phase 29 — Per-system evidence locker: uploaded files with control tags."""
    __tablename__ = "evidence_files"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    filename      = Column(String, nullable=False)          # stored filename (uuid-based)
    original_name = Column(String, nullable=False)          # original upload filename
    file_path     = Column(String, nullable=False)          # relative path under data/evidence/
    file_size     = Column(Integer, nullable=True)
    mime_type     = Column(String, nullable=True)
    description   = Column(Text, nullable=True)
    control_ids   = Column(Text, nullable=True)             # JSON array of control IDs
    tags          = Column(String, nullable=True)           # comma-separated
    uploaded_by   = Column(String, nullable=False)
    uploaded_at   = Column(DateTime, default=_now)
    is_locked     = Column(Boolean, default=False)          # locked = cannot delete


# ---------------------------------------------------------------------------
# Compliance Framework Crosswalk  (Phase 30)
# ---------------------------------------------------------------------------

class ComplianceFramework(Base):
    """
    Catalog of compliance/regulatory entries mapped to NIST 800-53r5.

    kind:
      catalog    — authoritative control source (NIST SP 800-53r5)
      baseline   — risk-scoped control subset (Low / Moderate / High)
      overlay    — tailoring layer applied on top of a baseline (FedRAMP, Privacy, ICS, CMMC)
      framework  — structured security management model (CSF 2.0, ISO 27001, SOC 2 TSC)
      regulation — law or regulatory requirement (FISMA, HIPAA, GDPR, PCI DSS)

    category — applicability domain:
      federal | contractor | healthcare | financial | privacy | industry | regulatory
    """
    __tablename__ = "compliance_frameworks"

    id           = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    name         = Column(String,  nullable=False, unique=True)
    short_name   = Column(String,  nullable=False, unique=True)
    version      = Column(String,  nullable=True)
    kind         = Column(String,  nullable=False, default="framework")   # catalog|baseline|overlay|framework|regulation
    category     = Column(String,  nullable=False)                        # federal|contractor|healthcare|financial|privacy|industry|regulatory
    published_by = Column(String,  nullable=True)
    description  = Column(Text,    nullable=True)
    source_url   = Column(String,  nullable=True)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=_now)


class FrameworkControl(Base):
    """Individual control or requirement within a compliance framework."""
    __tablename__ = "framework_controls"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    framework_id  = Column(String,  ForeignKey("compliance_frameworks.id"), nullable=False, index=True)
    control_id    = Column(String,  nullable=False)   # e.g. "PR.AC-1", "AC.L1-3.1.1", "A.8.1"
    title         = Column(String,  nullable=True)
    description   = Column(Text,    nullable=True)
    domain        = Column(String,  nullable=True)    # e.g. "PROTECT", "Access Control", "Annex A"
    level         = Column(String,  nullable=True)    # e.g. "L1"/"L2"/"L3", "LOW"/"MOD"/"HIGH"
    created_at    = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("framework_id", "control_id", name="uq_framework_ctrl"),
    )


class ControlCrosswalk(Base):
    """Maps a framework control to one or more NIST SP 800-53r5 control IDs."""
    __tablename__ = "control_crosswalks"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    framework_control_id = Column(Integer, ForeignKey("framework_controls.id"), nullable=False, index=True)
    nist_control_id      = Column(String,  nullable=False, index=True)   # e.g. "ac-2"
    mapping_type         = Column(String,  default="direct")             # direct|partial|inferred
    confidence           = Column(String,  default="high")               # high|medium|low
    source               = Column(String,  default="nist_official")      # nist_official|cis|community
    notes                = Column(Text,    nullable=True)
    created_at           = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("framework_control_id", "nist_control_id", name="uq_crosswalk"),
    )


class SystemFramework(Base):
    """Marks which compliance frameworks apply to a given system."""
    __tablename__ = "system_frameworks"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    system_id               = Column(String,  ForeignKey("systems.id"), nullable=False, index=True)
    framework_id            = Column(String,  ForeignKey("compliance_frameworks.id"), nullable=False)
    sub_category            = Column(String,  nullable=True)   # e.g. "Moderate" for FedRAMP, "Level 2" for CMMC
    applicability_rationale = Column(Text,    nullable=True)
    added_by                = Column(String,  nullable=True)
    added_at                = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("system_id", "framework_id", name="uq_sys_framework"),
    )


# ---------------------------------------------------------------------------
# Authorization Package Tracking  (Phase 31)
# ---------------------------------------------------------------------------

class AuthPackageType(Base):
    """
    Catalog of authorization / certification package types across industries.
    Seeded at startup; admin can add custom entries.
    category: federal|healthcare|financial|privacy|contractor|other
    phases_json: JSON list of phase dicts [{label, docs: [str]}] — for federal types
    sub_categories_json: JSON list of allowed sub_category strings
    """
    __tablename__ = "auth_package_types"

    id                  = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    name                = Column(String,  nullable=False, unique=True)   # "Authority to Operate"
    short_name          = Column(String,  nullable=False, unique=True)   # "ATO"
    category            = Column(String,  nullable=False)                # federal|healthcare|financial|privacy|contractor|other
    description         = Column(Text,    nullable=True)
    phases_json         = Column(Text,    nullable=True)                 # JSON — phase structure (federal types)
    sub_categories_json = Column(Text,    nullable=True)                 # JSON list of sub_category options
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=_now)


class SystemAuthPackage(Base):
    """
    Links a system to an authorization/certification package it is pursuing or has achieved.
    One system can have multiple package types (e.g., ATO + SOC 2 + HIPAA).
    """
    __tablename__ = "system_auth_packages"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    system_id       = Column(String,  ForeignKey("systems.id"), nullable=False, index=True)
    package_type_id = Column(String,  ForeignKey("auth_package_types.id"), nullable=False)
    sub_category    = Column(String,  nullable=True)    # e.g. "Moderate", "Level 2", "r2"
    status          = Column(String,  default="in_progress")  # in_progress|achieved|expired|withdrawn
    started_at      = Column(DateTime, nullable=True)
    achieved_at     = Column(DateTime, nullable=True)
    expires_at      = Column(DateTime, nullable=True)
    notes           = Column(Text,    nullable=True)
    created_by      = Column(String,  nullable=True)
    created_at      = Column(DateTime, default=_now)
    updated_at      = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("system_id", "package_type_id", "sub_category", name="uq_sys_auth_pkg"),
    )


class OrgEnabledFramework(Base):
    """
    Org-level ceiling for which compliance frameworks are in use.
    Admin enables/disables here; per-system selection is constrained to enabled frameworks.
    Disabling a framework immediately suppresses all SystemControl records sourced from it
    across every system.  Re-enabling restores them.

    Single-tenant: one record per framework.
    Multi-tenant (future): add org_id column.
    """
    __tablename__ = "org_enabled_frameworks"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    framework_id = Column(String, ForeignKey("compliance_frameworks.id"), nullable=False, unique=True)
    is_enabled   = Column(Boolean, default=True)
    enabled_by   = Column(String, nullable=True)
    enabled_at   = Column(DateTime, default=_now)
    disabled_at  = Column(DateTime, nullable=True)
    disabled_by  = Column(String, nullable=True)
    disable_note = Column(String, nullable=True)


class DataAttributeDefinition(Base):
    """
    Admin-configurable registry of data sensitivity / regulatory attribute types.
    Replaces the flat boolean columns on System (has_pii, has_phi, has_gdpr_data, …).
    New regulations and jurisdictions are added here without schema changes.
    """
    __tablename__ = "data_attribute_definitions"

    key                     = Column(String, primary_key=True)   # e.g. 'pii', 'phi', 'gdpr', 'cui'
    label                   = Column(String, nullable=False)      # "Personally Identifiable Information"
    short_label             = Column(String, nullable=False)      # "PII"
    description             = Column(Text,   nullable=True)
    jurisdiction            = Column(String, nullable=True)       # US | EU | CA | global | …
    regulation              = Column(String, nullable=True)       # "Privacy Act, NIST SP 800-122"
    triggers_privacy_review = Column(Boolean, default=False)      # routes system to privacy_officer queue
    triggers_co_review      = Column(Boolean, default=False)      # adds system to _co_review_system_ids
    triggers_notification   = Column(Boolean, default=True)       # in-app alert to privacy_officer on set
    sort_order              = Column(Integer, default=0)
    is_active               = Column(Boolean, default=True)
    created_at              = Column(DateTime, default=_now)


class SystemDataAttribute(Base):
    """
    Flexible per-system data sensitivity tags, replacing boolean columns.
    Each row links a system to an active DataAttributeDefinition.
    """
    __tablename__ = "system_data_attributes"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    attribute_key = Column(String, ForeignKey("data_attribute_definitions.key"), nullable=False)
    notes         = Column(Text,   nullable=True)
    added_by      = Column(String, nullable=True)
    added_at      = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("system_id", "attribute_key", name="uq_sys_data_attr"),
    )


class ExternalEngagement(Base):
    """
    Links an external-role platform user (vendor, contracting_officer) to a specific
    system with scoped read access.  Separate from SystemAssignment (internal team only).

    A vendor user filling an *internal* role (e.g. contractor acting as ISSO) should
    still get an ExternalEngagement record — their `internal_role` field captures what
    internal function they're performing, while their platform role remains 'vendor'
    for access-scoping purposes.
    """
    __tablename__ = "external_engagements"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    system_id     = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    remote_user   = Column(String, nullable=False, index=True)  # platform username
    role_type     = Column(String, nullable=False)              # vendor|contracting_officer
    internal_role = Column(String, nullable=True)               # filled internal role, if any (isso|developer|…)
    scope_note    = Column(Text,   nullable=True)               # what they're scoped to
    granted_by    = Column(String, nullable=True)
    granted_at    = Column(DateTime, default=_now)
    expires_at    = Column(DateTime, nullable=True)             # engagement end date
    status        = Column(String, default="active")            # active|revoked

    __table_args__ = (
        UniqueConstraint("system_id", "remote_user", name="uq_ext_engagement"),
    )


class ExecutiveObservation(Base):
    """
    An observation (non-binding comment) added by a CISO or executive on a system's
    authorization package or overall compliance posture.  These are advisory only —
    the AO retains sole authority to issue/deny ATOs.
    """
    __tablename__ = "executive_observations"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    system_id   = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    remote_user = Column(String, nullable=False)   # executive or CISO who wrote it
    body        = Column(Text, nullable=False)
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)


class PackageSignature(Base):
    """ISSO → ISSM → AO signing chain + advisory concurrences on a Submission.

    Blocking stages:  isso → issm → ao  (each requires the prior stage to exist)
    Advisory stages:  privacy_officer | risk_manager | contracting_officer
                      (recorded but never block AO decision)
    """
    __tablename__ = "package_signatures"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False, index=True)
    stage         = Column(String, nullable=False)
    # isso | issm | ao | privacy_officer | risk_manager | contracting_officer
    signed_by     = Column(String, nullable=False)
    signed_at     = Column(DateTime, default=_now)
    comment       = Column(Text, nullable=True)
    decision      = Column(String, nullable=True)
    # ao: authorized|denied  |  advisory: concur|non_concur
    is_advisory   = Column(Boolean, default=False)
    file_path     = Column(String, nullable=True)   # uploaded signed document
    file_name     = Column(String, nullable=True)
    file_size     = Column(Integer, nullable=True)
    __table_args__ = (
        UniqueConstraint("submission_id", "stage", name="uq_pkg_sig_stage"),
    )


# ---------------------------------------------------------------------------
# Agnostic Control Catalog  (Phase 34)
# ---------------------------------------------------------------------------

class CatalogControl(Base):
    """
    Unified, framework-agnostic control catalog.  Every control from every
    framework (NIST 800-53, ISO 27001, CMMC, CIS, CSF, HIPAA, …) lives here
    as a first-class row.  Replaces the NIST-centric FrameworkControl table;
    NIST 800-53r5 controls are seeded here from the OSCAL JSON on startup.

    No single framework is privileged — NIST is just one entry in
    compliance_frameworks.  Cross-framework navigation is done via
    ControlRelationship; baseline membership via BaselineControl.
    """
    __tablename__ = "catalog_controls"

    id                = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    framework_id      = Column(String,  ForeignKey("compliance_frameworks.id"), nullable=False, index=True)
    control_id        = Column(String,  nullable=False)      # native ID: "ac-2", "A.5.18", "PR.AC-1"
    title             = Column(String,  nullable=True)
    description       = Column(Text,    nullable=True)       # full requirement / statement text
    domain            = Column(String,  nullable=True)       # framework-native family/category/annex
    subdomain         = Column(String,  nullable=True)       # optional second-level grouping
    level             = Column(String,  nullable=True)       # tier: "L1"/"L2", "LOW"/"MOD"/"HIGH", "IG1"
    parameters_json   = Column(Text,    nullable=True)       # JSON ODPs; rich for catalogs, null for frameworks
    enhancements_json = Column(Text,    nullable=True)       # JSON sub-controls / control enhancements
    is_withdrawn      = Column(Boolean, default=False)
    source_url        = Column(String,  nullable=True)
    created_at        = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("framework_id", "control_id", name="uq_catalog_ctrl"),
    )


class ControlRelationship(Base):
    """
    Bidirectional mapping between any two CatalogControl rows.
    Replaces the NIST-centric ControlCrosswalk; relationships can exist
    between any pair of frameworks without NIST as a mandatory hub.

    relationship: equivalent | partial | addresses | supersedes | conflicts
    direction:    bidirectional | a_satisfies_b | b_satisfies_a
    confidence:   high | medium | low
    source:       nist_official | iso_official | community | ai_inferred
    """
    __tablename__ = "control_relationships"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    control_a_id = Column(String,  ForeignKey("catalog_controls.id"), nullable=False, index=True)
    control_b_id = Column(String,  ForeignKey("catalog_controls.id"), nullable=False, index=True)
    relationship = Column(String,  nullable=False, default="equivalent")
    direction    = Column(String,  nullable=False, default="bidirectional")
    confidence   = Column(String,  nullable=False, default="high")
    source       = Column(String,  default="nist_official")
    notes        = Column(Text,    nullable=True)
    created_at   = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("control_a_id", "control_b_id", "relationship", name="uq_ctrl_rel"),
    )


class BaselineControl(Base):
    """
    Maps a baseline ComplianceFramework to its member CatalogControl rows.
    Replaces hardcoded baseline JSON files; any framework with kind=baseline
    (NIST Low/Mod/High, CMMC L1/L2/L3, CIS IG1/IG2/IG3, …) defines its
    control set here.
    """
    __tablename__ = "baseline_controls"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    baseline_id        = Column(String,  ForeignKey("compliance_frameworks.id"), nullable=False, index=True)
    catalog_control_id = Column(String,  ForeignKey("catalog_controls.id"),      nullable=False, index=True)
    is_required        = Column(Boolean, default=True)
    tailoring_notes    = Column(Text,    nullable=True)
    created_at         = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("baseline_id", "catalog_control_id", name="uq_baseline_ctrl"),
    )


class DeploymentProfile(Base):
    """
    Admin-configured deployment profiles — named bundles of frameworks,
    terminology, and role guidance for different compliance contexts.
    Built-in presets can be activated/deactivated but not deleted.
    """
    __tablename__ = "deployment_profiles"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    slug            = Column(String, nullable=False, unique=True)   # e.g. "federal_nist"
    name            = Column(String, nullable=False)
    description     = Column(Text, nullable=True)
    is_builtin      = Column(Boolean, default=True)                 # built-in presets
    is_active       = Column(Boolean, default=False)                # currently in use
    primary_catalog = Column(String, nullable=True)                 # default for new systems
    framework_sns   = Column(Text, nullable=True)                   # JSON list of short_names
    terminology     = Column(Text, nullable=True)                   # JSON terminology overrides
    suggested_roles = Column(Text, nullable=True)                   # JSON list of role strings
    created_at      = Column(DateTime, default=_now)
    updated_at      = Column(DateTime, default=_now, onupdate=_now)
    activated_by    = Column(String, nullable=True)
    activated_at    = Column(DateTime, nullable=True)


class SystemScan(Base):
    """Phase 35 — SCAP scan job for a System."""
    __tablename__ = "system_scans"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id       = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    scan_type       = Column(String, nullable=False, default="oscap")
    target_host     = Column(String, nullable=True)
    target_port     = Column(Integer, default=22)
    target_user     = Column(String, default="root")
    datastream_path = Column(String, nullable=False)
    datastream_name = Column(String, nullable=True)
    profile_id      = Column(String, nullable=False)
    profile_title   = Column(String, nullable=True)
    status          = Column(String, nullable=False, default="queued")  # queued|running|complete|failed
    arf_path        = Column(String, nullable=True)
    html_path       = Column(String, nullable=True)
    exit_code       = Column(Integer, nullable=True)
    error_msg       = Column(Text, nullable=True)
    pass_count      = Column(Integer, default=0)
    fail_count      = Column(Integer, default=0)
    error_count     = Column(Integer, default=0)
    notchecked_count    = Column(Integer, default=0)
    notapplicable_count = Column(Integer, default=0)
    started_at      = Column(DateTime, nullable=True)
    completed_at    = Column(DateTime, nullable=True)
    created_by      = Column(String, nullable=True)
    created_at      = Column(DateTime, default=_now)


class ScanFinding(Base):
    """Phase 35 — Individual SCAP rule result within a SystemScan."""
    __tablename__ = "scan_findings"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    scan_id      = Column(String, ForeignKey("system_scans.id"), nullable=False, index=True)
    rule_id      = Column(String, nullable=False)
    short_id     = Column(String, nullable=True)
    title        = Column(String, nullable=True)
    result       = Column(String, nullable=False)   # pass|fail|error|notchecked|notapplicable|informational
    severity     = Column(String, default="Informational")
    nist_controls = Column(Text, nullable=True)     # JSON list ["AC-2","SI-3"]
    description  = Column(Text, nullable=True)
    fix_text     = Column(Text, nullable=True)
    ident        = Column(String, nullable=True)    # CCE/CVE identifier
    poam_item_id = Column(String, ForeignKey("poam_items.id"), nullable=True)


class DailyWorkAssignment(Base):
    """Deterministically-generated daily control/POA&M review task for a user."""
    __tablename__ = "daily_work_assignments"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    remote_user     = Column(String, nullable=False, index=True)
    system_id       = Column(String, ForeignKey("systems.id"), nullable=False)
    system_abbr     = Column(String, nullable=True)
    system_name     = Column(String, nullable=True)
    control_id      = Column(String, nullable=True)   # None for POA&M tasks
    control_title   = Column(String, nullable=True)
    task_type       = Column(String, nullable=False)  # "control_review" | "poam_check"
    assignment_date = Column(String, nullable=False)  # ISO date YYYY-MM-DD
    status          = Column(String, nullable=False, default="pending")  # pending/done/skipped
    completed_at    = Column(DateTime, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)


class ImmutableAuditEntry(Base):
    """IL4 non-repudiation audit log — append-only, no updates, no deletes.

    Covers NIST 800-53 AU-2, AU-3, AU-8, AU-9, AU-10, AU-12.
    All fields are set at creation time and never modified.
    """
    __tablename__ = "immutable_audit_log"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    timestamp    = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    remote_user  = Column(String, nullable=True, index=True)
    remote_ip    = Column(String, nullable=True)
    method       = Column(String, nullable=True)   # GET POST PUT DELETE PATCH
    path         = Column(String, nullable=True)
    status_code  = Column(Integer, nullable=True)
    event_type   = Column(String, nullable=False)  # request|auth|data_access|export|admin|error
    resource_type = Column(String, nullable=True)
    resource_id  = Column(String, nullable=True)
    details      = Column(Text, nullable=True)     # JSON
    session_id   = Column(String, nullable=True)
    auth_method  = Column(String, nullable=True)   # password|cac_piv|token
    mfa_verified = Column(Boolean, nullable=True)
    # Integrity chain — each entry records hash of previous entry for tamper detection
    prev_hash    = Column(String, nullable=True)
    entry_hash   = Column(String, nullable=True)


class TrainingClick(Base):
    """Tracks employee clicks on external training resource links (Skill Builder widget)."""
    __tablename__ = "training_clicks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    remote_user = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False)   # niccs | dod_cyber | sans_aces
    clicked_at  = Column(DateTime, nullable=False, default=datetime.utcnow)


class InterviewSession(Base):
    """Control interview session — one per stakeholder meeting."""
    __tablename__ = "interview_sessions"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    system_id        = Column(String, ForeignKey("systems.id"), nullable=False, index=True)
    created_by       = Column(String, nullable=False)
    title            = Column(String, nullable=True)
    stakeholder_type = Column(String, nullable=True)   # dev|ops|program_office|system_owner|facilities|hr|bcdr|sca|all
    stakeholder_name = Column(String, nullable=True)   # name of person/team interviewed
    status           = Column(String, default="open")  # open|submitted|reviewed
    session_type     = Column(String, default="control_interview")
    created_at       = Column(DateTime, default=_now, index=True)
    submitted_at     = Column(DateTime, nullable=True)
    reviewed_by      = Column(String, nullable=True)
    reviewed_at      = Column(DateTime, nullable=True)
    notes            = Column(Text, nullable=True)


class InterviewQuestion(Base):
    """Auto-generated question within an interview session."""
    __tablename__ = "interview_questions"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    session_id       = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    control_id       = Column(String, nullable=False)
    control_family   = Column(String, nullable=True)
    control_title    = Column(String, nullable=True)
    question_number  = Column(Integer, nullable=False)   # 1-based within this control
    question_text    = Column(Text, nullable=False)
    stakeholder_target = Column(String, nullable=True)   # who this Q targets
    sort_order       = Column(Integer, default=0)
    overlay_framework  = Column(String, nullable=True)   # e.g. "fedramp_high"; NULL for base qs
    parent_control_id  = Column(String, nullable=True)   # e.g. "AC-7" when overlay_framework set
    question_type      = Column(String, nullable=True, default="text")   # "text"|"impl_status"|"responsible_role"
    question_options   = Column(Text,   nullable=True)                    # JSON array of option strings


class InterviewResponse(Base):
    """Response to a single interview question, with full typing audit data."""
    __tablename__ = "interview_responses"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    session_id       = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question_id      = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    response_text    = Column(Text, nullable=True)
    first_keystroke_at = Column(DateTime, nullable=True)
    last_keystroke_at  = Column(DateTime, nullable=True)
    keystroke_count  = Column(Integer, default=0)
    char_count       = Column(Integer, default=0)
    paste_attempts   = Column(Integer, default=0)
    focus_count      = Column(Integer, default=0)
    time_on_field_s  = Column(Float, nullable=True)
    submitted_at     = Column(DateTime, nullable=True)


class InterviewAuditEvent(Base):
    """Fine-grained audit trail: every keystroke burst, paste attempt, focus/blur, submit."""
    __tablename__ = "interview_audit_events"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question_id  = Column(Integer, nullable=True)
    remote_user  = Column(String, nullable=True)
    event_type   = Column(String, nullable=False)   # first_keystroke|keystroke_burst|paste_attempt|focus|blur|submit|load
    event_data   = Column(Text, nullable=True)      # JSON: char_count, delta, field_id, etc.
    occurred_at  = Column(DateTime, default=_now, index=True)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_db(engine)


_DB_ENCRYPTION_KEY: str = ""   # set by make_engine when db_encryption=true


def _configure_sqlite(dbapi_conn, _connection_record):
    """Apply SQLite performance and safety PRAGMAs on every new connection.
    When DB encryption is enabled, the SQLCipher key PRAGMA is applied first.
    """
    if _DB_ENCRYPTION_KEY:
        dbapi_conn.execute(f"PRAGMA key='{_DB_ENCRYPTION_KEY}'")
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")   # safe with WAL, 3-5× faster than FULL
    dbapi_conn.execute("PRAGMA cache_size=-20000")    # 20 MB page cache
    dbapi_conn.execute("PRAGMA temp_store=MEMORY")    # temp tables in RAM
    dbapi_conn.execute("PRAGMA mmap_size=268435456")  # 256 MB memory-mapped I/O
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


def make_engine(config: dict):
    global _DB_ENCRYPTION_KEY
    sec = config.get("security", {})
    if sec.get("db_encryption", False):
        key_env = sec.get("db_encryption_key_env", "BLACKSITE_DB_KEY")
        _DB_ENCRYPTION_KEY = os.environ.get(key_env, "")
        if not _DB_ENCRYPTION_KEY:
            raise RuntimeError(
                f"security.db_encryption=true but ${key_env} is not set. "
                "Set the environment variable to the database encryption key."
            )
        # Verify pysqlcipher3 is available (early patch already applied at module load)
        try:
            from pysqlcipher3 import dbapi2 as _  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "pysqlcipher3 not installed but db_encryption=true. "
                "Run: pip install pysqlcipher3 && sudo apt install libsqlcipher-dev"
            )

    eng = create_async_engine(get_db_url(config), echo=False)
    if eng.dialect.name == "sqlite":
        event.listen(eng.sync_engine, "connect", _configure_sqlite)
    return eng


def make_session_factory(engine) -> async_sessionmaker:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
