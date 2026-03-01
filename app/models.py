"""
BLACKSITE — Database models (SQLAlchemy + SQLite)
"""
from __future__ import annotations

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
    # Phase 17 — categorization workflow
    categorization_status   = Column(String, default="draft")  # draft|pending_review|approved
    categorization_approved_by = Column(String, nullable=True)
    categorization_note     = Column(Text, nullable=True)
    # EIS flag (added via migration, Phase 12-era)
    is_eis                  = Column(Boolean, default=False)
    # Phase 20 — AO decision detail
    ato_duration            = Column(String, nullable=True)    # 1_year|3_year|5_year|ongoing|custom
    ato_notes               = Column(Text, nullable=True)      # AO decision rationale
    ato_signed_by           = Column(String, nullable=True)    # AO username
    ato_signed_at           = Column(DateTime, nullable=True)  # timestamp of AO signature


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
    control_id           = Column(String, nullable=False)       # e.g. "ac-1"
    control_family       = Column(String, nullable=False)       # e.g. "AC"
    control_title        = Column(String, nullable=True)
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

    __table_args__ = (
        Index("ix_sysctl_system_ctrl", "system_id", "control_id", unique=True),
    )


class Submission(Base):
    """Authorization package / ATO submission tracking."""
    __tablename__ = "submissions"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id        = Column(String, ForeignKey("systems.id"), nullable=False)
    submission_type  = Column(String, default="initial")
    # initial|reauthorization|significant_change|annual_review
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
    created_at  = Column(DateTime, default=datetime.utcnow)


class TeamMembership(Base):
    """Membership linking a user to a SystemTeam."""
    __tablename__ = "team_memberships"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    team_id      = Column(Integer, ForeignKey("system_teams.id"), nullable=False)
    remote_user  = Column(String, nullable=False)
    role_in_team = Column(String, default="member")       # lead|member|observer
    assigned_by  = Column(String, nullable=True)
    assigned_at  = Column(DateTime, default=datetime.utcnow)


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
    triggered_at = Column(DateTime, default=datetime.utcnow)
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

    id        = Column(Integer, primary_key=True, autoincrement=True)
    room      = Column(String(120), nullable=False, index=True)
    # room values: "@group"  OR  sorted pair "alice:dan"
    from_user = Column(String(120), nullable=False)
    body      = Column(Text, nullable=False)
    sent_at   = Column(DateTime, default=_now)


class AdminChatReceipt(Base):
    """Tracks last-read message ID per user per room for unread counts."""
    __tablename__ = "admin_chat_receipts"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    room         = Column(String(120), nullable=False)
    username     = Column(String(120), nullable=False)
    last_read_id = Column(Integer, default=0)


# ── Database setup ─────────────────────────────────────────────────────────────

def get_db_url(config: dict) -> str:
    db_path = config.get("db", {}).get("path", "blacksite.db")
    return f"sqlite+aiosqlite:///{db_path}"


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
        # Phase 17 — categorization workflow
        ("systems",         "categorization_status",      "TEXT DEFAULT 'draft'"),
        ("systems",         "categorization_approved_by", "TEXT DEFAULT NULL"),
        ("systems",         "categorization_note",        "TEXT DEFAULT NULL"),
        # Phase 6 — H6: UI preference columns on UserProfile
        ("user_profiles",   "pref_font_size",              "TEXT DEFAULT '14px'"),
        ("user_profiles",   "pref_density",                "TEXT DEFAULT 'comfortable'"),
        ("user_profiles",   "pref_rows_per_page",          "INTEGER DEFAULT 25"),
        # Phase 20 — Platform tier, AO decision detail, ATO doc file storage
        ("user_profiles",   "company_tier",               "TEXT DEFAULT 'analyst'"),
        ("systems",         "ato_duration",               "TEXT DEFAULT NULL"),
        ("systems",         "ato_notes",                  "TEXT DEFAULT NULL"),
        ("systems",         "ato_signed_by",              "TEXT DEFAULT NULL"),
        ("systems",         "ato_signed_at",              "DATETIME DEFAULT NULL"),
        ("ato_documents",   "file_path",                  "TEXT DEFAULT NULL"),
        ("ato_documents",   "file_size",                  "INTEGER DEFAULT NULL"),
        ("ato_documents",   "source_type",                "TEXT DEFAULT NULL"),
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
        "CREATE INDEX IF NOT EXISTS ix_assessments_system_id          ON assessments (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_ato_documents_system_id        ON ato_documents (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_ato_doc_versions_document_id   ON ato_document_versions (document_id)",
        "CREATE INDEX IF NOT EXISTS ix_ato_workflow_events_document_id ON ato_workflow_events (document_id)",
    ]
    # Phase 10: new tables (CREATE TABLE IF NOT EXISTS is idempotent)
    new_tables = [
        """CREATE TABLE IF NOT EXISTS system_teams (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id   TEXT NOT NULL REFERENCES systems(id),
            name        TEXT NOT NULL,
            team_type   TEXT DEFAULT 'general',
            description TEXT,
            created_by  TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS team_memberships (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id      INTEGER NOT NULL REFERENCES system_teams(id),
            remote_user  TEXT NOT NULL,
            role_in_team TEXT DEFAULT 'member',
            assigned_by  TEXT,
            assigned_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS bcdr_events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id    TEXT REFERENCES systems(id),
            team_id      INTEGER REFERENCES system_teams(id),
            event_type   TEXT,
            title        TEXT,
            status       TEXT DEFAULT 'open',
            triggered_by TEXT,
            triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            target_rto   INTEGER,
            target_rpo   INTEGER,
            closed_at    DATETIME
        )""",
        """CREATE TABLE IF NOT EXISTS bcdr_signoffs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id     INTEGER NOT NULL REFERENCES bcdr_events(id),
            remote_user  TEXT NOT NULL,
            role_in_team TEXT,
            required     BOOLEAN DEFAULT 1,
            signed_off   BOOLEAN DEFAULT 0,
            signed_at    DATETIME,
            notes        TEXT
        )""",
        # Phase 12 new tables
        """CREATE TABLE IF NOT EXISTS observations (
            id               TEXT PRIMARY KEY,
            system_id        TEXT REFERENCES systems(id),
            title            TEXT NOT NULL,
            source           TEXT,
            obs_type         TEXT,
            severity         TEXT DEFAULT 'Moderate',
            description      TEXT,
            control_ids      TEXT,
            scope_tags       TEXT,
            status           TEXT DEFAULT 'open',
            promoted_to_poam TEXT REFERENCES poam_items(id),
            assigned_to      TEXT,
            due_date         TEXT,
            created_by       TEXT,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS inventory_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id     TEXT NOT NULL REFERENCES systems(id),
            item_type     TEXT NOT NULL,
            name          TEXT NOT NULL,
            vendor        TEXT,
            version       TEXT,
            quantity      INTEGER DEFAULT 1,
            location      TEXT,
            ip_address    TEXT,
            serial_number TEXT,
            notes         TEXT,
            added_by      TEXT,
            added_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS system_connections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id     TEXT NOT NULL REFERENCES systems(id),
            conn_type     TEXT,
            name          TEXT NOT NULL,
            description   TEXT,
            remote_system TEXT,
            data_types    TEXT,
            protocol      TEXT,
            port          TEXT,
            direction     TEXT,
            has_isa       BOOLEAN DEFAULT 0,
            isa_doc_id    TEXT,
            added_by      TEXT,
            added_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS artifacts (
            id              TEXT PRIMARY KEY,
            system_id       TEXT NOT NULL REFERENCES systems(id),
            control_id      TEXT,
            artifact_type   TEXT,
            title           TEXT NOT NULL,
            description     TEXT,
            file_path       TEXT,
            source          TEXT,
            integrity_hash  TEXT,
            collected_at    DATETIME,
            freshness_days  INTEGER DEFAULT 365,
            owner           TEXT,
            approval_status TEXT DEFAULT 'pending',
            approved_by     TEXT,
            approved_at     DATETIME,
            created_by      TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        # Phase 13
        """CREATE TABLE IF NOT EXISTS security_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type  TEXT,
            severity    TEXT DEFAULT 'info',
            remote_ip   TEXT,
            remote_user TEXT,
            method      TEXT,
            path        TEXT,
            status_code INTEGER,
            user_agent  TEXT,
            details     TEXT
        )""",
        # LIST4-ITEM3: Admin-configurable feed sources
        """CREATE TABLE IF NOT EXISTS feed_sources (
            key          TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            url          TEXT NOT NULL UNIQUE,
            enabled      BOOLEAN DEFAULT 1,
            sort_order   INTEGER DEFAULT 0,
            last_fetched DATETIME,
            last_error   TEXT,
            item_count   INTEGER DEFAULT 0,
            error_count  INTEGER DEFAULT 0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        # Phase 6 — B2: Removed user reservations (1-year hold)
        """CREATE TABLE IF NOT EXISTS removed_user_reservations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            username         TEXT NOT NULL,
            email            TEXT,
            removed_at       DATETIME NOT NULL,
            hold_until       DATETIME NOT NULL,
            removed_by       TEXT NOT NULL,
            override_granted BOOLEAN DEFAULT 0,
            override_by      TEXT,
            override_at      DATETIME,
            override_reason  TEXT
        )""",
        # Phase 18 — POA&M closure evidence file uploads
        """CREATE TABLE IF NOT EXISTS poam_evidence (
            id           TEXT PRIMARY KEY,
            poam_item_id TEXT NOT NULL REFERENCES poam_items(id),
            filename     TEXT NOT NULL,
            file_path    TEXT NOT NULL,
            file_size    INTEGER,
            uploaded_by  TEXT,
            uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            description  TEXT
        )""",
        # Phase 20 — Platform tier + system role assignments + notifications
        """CREATE TABLE IF NOT EXISTS program_role_assignments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user  TEXT NOT NULL REFERENCES user_profiles(remote_user),
            system_id    TEXT REFERENCES systems(id),
            program_role TEXT NOT NULL,
            status       TEXT DEFAULT 'active',
            requested_by TEXT,
            requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            approved_by  TEXT,
            approved_at  DATETIME,
            revoked_by   TEXT,
            revoked_at   DATETIME,
            note         TEXT,
            UNIQUE (remote_user, program_role, system_id)
        )""",
        """CREATE TABLE IF NOT EXISTS duty_assignments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user TEXT NOT NULL REFERENCES user_profiles(remote_user),
            system_id   TEXT NOT NULL REFERENCES systems(id),
            duty        TEXT NOT NULL,
            assigned_by TEXT,
            assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            active      BOOLEAN DEFAULT 1,
            expires_at  DATETIME,
            note        TEXT,
            UNIQUE (remote_user, duty, system_id)
        )""",
        """CREATE TABLE IF NOT EXISTS notifications (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user  TEXT NOT NULL REFERENCES user_profiles(remote_user),
            notif_type   TEXT NOT NULL,
            title        TEXT NOT NULL,
            body         TEXT,
            action_url   TEXT,
            related_id   INTEGER,
            related_type TEXT,
            is_read      BOOLEAN DEFAULT 0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            read_at      DATETIME
        )""",
        # Phase 25 — Daily Workflow Stack
        """CREATE TABLE IF NOT EXISTS daily_logbooks (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user         TEXT NOT NULL,
            system_id           TEXT NOT NULL REFERENCES systems(id),
            log_date            TEXT NOT NULL,
            task_flags          TEXT,
            notes               TEXT,
            snap_open_poams     INTEGER DEFAULT 0,
            snap_overdue_poams  INTEGER DEFAULT 0,
            snap_open_risks     INTEGER DEFAULT 0,
            snap_open_obs       INTEGER DEFAULT 0,
            snap_open_incidents INTEGER DEFAULT 0,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (remote_user, system_id, log_date)
        )""",
        """CREATE TABLE IF NOT EXISTS deep_work_rotations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user         TEXT NOT NULL,
            system_id           TEXT NOT NULL REFERENCES systems(id),
            role_variant        TEXT NOT NULL,
            current_day         INTEGER DEFAULT 1,
            last_work_date      TEXT,
            paused              BOOLEAN DEFAULT 0,
            quarterly_overrides TEXT,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (remote_user, system_id, role_variant)
        )""",
        """CREATE TABLE IF NOT EXISTS deep_work_completions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            rotation_id    INTEGER NOT NULL REFERENCES deep_work_rotations(id),
            remote_user    TEXT NOT NULL,
            system_id      TEXT NOT NULL REFERENCES systems(id),
            rotation_day   INTEGER NOT NULL,
            completed_date TEXT NOT NULL,
            notes          TEXT,
            evidence_path  TEXT,
            evidence_name  TEXT,
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS change_review_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user     TEXT NOT NULL,
            system_id       TEXT NOT NULL REFERENCES systems(id),
            review_date     TEXT NOT NULL,
            ticket_refs     TEXT,
            high_risk_count INTEGER DEFAULT 0,
            all_approved    BOOLEAN DEFAULT 1,
            backout_exists  BOOLEAN DEFAULT 1,
            untracked_found BOOLEAN DEFAULT 0,
            obs_id          TEXT REFERENCES observations(id),
            notes           TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS backup_check_records (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user  TEXT NOT NULL,
            system_id    TEXT NOT NULL REFERENCES systems(id),
            check_date   TEXT NOT NULL,
            result       TEXT DEFAULT 'pass',
            ephi_systems TEXT,
            job_health   TEXT DEFAULT 'ok',
            issue_raised BOOLEAN DEFAULT 0,
            notes        TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (remote_user, system_id, check_date)
        )""",
        """CREATE TABLE IF NOT EXISTS access_spot_checks (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_user           TEXT NOT NULL,
            system_id             TEXT NOT NULL REFERENCES systems(id),
            check_date            TEXT NOT NULL,
            records_sampled       INTEGER DEFAULT 0,
            anomaly_found         BOOLEAN DEFAULT 0,
            terminated_user_found BOOLEAN DEFAULT 0,
            anomaly_description   TEXT,
            notes                 TEXT,
            created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (remote_user, system_id, check_date)
        )""",
        """CREATE TABLE IF NOT EXISTS vendors (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id     TEXT NOT NULL REFERENCES systems(id),
            name          TEXT NOT NULL,
            service_type  TEXT DEFAULT 'other',
            handles_ephi  BOOLEAN DEFAULT 0,
            has_baa       BOOLEAN DEFAULT 0,
            baa_expiry    TEXT,
            contact_name  TEXT,
            contact_email TEXT,
            status        TEXT DEFAULT 'active',
            notes         TEXT,
            created_by    TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS interconnection_records (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id            TEXT NOT NULL REFERENCES systems(id),
            partner_name         TEXT NOT NULL,
            data_types           TEXT,
            isa_exists           BOOLEAN DEFAULT 0,
            isa_expiry           TEXT,
            monitoring_confirmed BOOLEAN DEFAULT 0,
            encrypted_in_transit BOOLEAN DEFAULT 0,
            auth_method          TEXT,
            notes                TEXT,
            last_reviewed        TEXT,
            reviewed_by          TEXT,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS data_flow_records (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id            TEXT NOT NULL REFERENCES systems(id),
            integration_name     TEXT NOT NULL,
            auth_method          TEXT,
            encrypted_in_transit BOOLEAN DEFAULT 0,
            encrypted_at_rest    BOOLEAN DEFAULT 0,
            logging_confirmed    BOOLEAN DEFAULT 0,
            termination_steps    TEXT,
            data_types           TEXT,
            last_reviewed        TEXT,
            reviewed_by          TEXT,
            notes                TEXT,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS privacy_assessments (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id        TEXT NOT NULL REFERENCES systems(id),
            assess_type      TEXT DEFAULT 'pta',
            data_elements    TEXT,
            purpose          TEXT,
            disclosures      TEXT,
            retention_policy TEXT,
            access_controls  TEXT,
            last_reviewed    TEXT,
            reviewer         TEXT,
            status           TEXT DEFAULT 'draft',
            notes            TEXT,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS restore_test_records (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id           TEXT NOT NULL REFERENCES systems(id),
            test_date           TEXT NOT NULL,
            scope               TEXT,
            result              TEXT DEFAULT 'pass',
            time_to_restore_min INTEGER,
            validated_by        TEXT,
            notes               TEXT,
            evidence_path       TEXT,
            created_by          TEXT,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS generated_reports (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id    TEXT NOT NULL REFERENCES systems(id),
            remote_user  TEXT NOT NULL,
            report_type  TEXT NOT NULL,
            filename     TEXT,
            file_path    TEXT,
            file_size    INTEGER,
            status       TEXT DEFAULT 'generating',
            error_msg    TEXT,
            generated_at DATETIME,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    async with engine.begin() as conn:
        for create_sql in new_tables:
            await conn.execute(text(create_sql))
        for table, col, col_def in col_migrations:
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            cols = [row[1] for row in result.fetchall()]
            if col not in cols:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
        for idx_sql in index_migrations:
            await conn.execute(text(idx_sql))
        # Seed default feed sources (INSERT OR IGNORE — never overwrites admin changes)
        for key, cfg in FEED_ALLOWLIST.items():
            await conn.execute(text(
                "INSERT OR IGNORE INTO feed_sources (key, name, url, enabled, sort_order) "
                "VALUES (:key, :name, :url, :enabled, :sort_order)"
            ), {"key": key, "name": cfg["name"], "url": cfg["url"],
                "enabled": 1 if cfg["enabled"] else 0, "sort_order": cfg["sort_order"]})


class SystemSettings(Base):
    """Key-value store for site-wide admin settings (chat_enabled, etc.)."""
    __tablename__ = "system_settings"

    key        = Column(String, primary_key=True)
    value      = Column(Text, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


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


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_db(engine)


def _configure_sqlite(dbapi_conn, _connection_record):
    """Apply SQLite performance and safety PRAGMAs on every new connection."""
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")   # safe with WAL, 3-5× faster than FULL
    dbapi_conn.execute("PRAGMA cache_size=-20000")    # 20 MB page cache
    dbapi_conn.execute("PRAGMA temp_store=MEMORY")    # temp tables in RAM
    dbapi_conn.execute("PRAGMA mmap_size=268435456")  # 256 MB memory-mapped I/O
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


def make_engine(config: dict):
    eng = create_async_engine(get_db_url(config), echo=False)
    event.listen(eng.sync_engine, "connect", _configure_sqlite)
    return eng


def make_session_factory(engine) -> async_sessionmaker:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
