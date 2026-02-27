"""
BLACKSITE — Database models (SQLAlchemy + SQLite)
"""
from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, create_engine, Index, text, event
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
    created_at              = Column(DateTime, default=_now)
    updated_at              = Column(DateTime, default=_now, onupdate=_now)
    created_by              = Column(String, nullable=True)   # Remote-User


class PoamItem(Base):
    """Plan of Action & Milestones (NIST CA-5)"""
    __tablename__ = "poam_items"

    id                   = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    system_id            = Column(String, ForeignKey("systems.id"), nullable=True, index=True)
    assessment_id        = Column(String, ForeignKey("assessments.id"), nullable=True, index=True)
    control_id           = Column(String, nullable=True)        # e.g. "ac-2"
    weakness_name        = Column(String, nullable=False)
    weakness_description = Column(Text, nullable=True)
    detection_source     = Column(String, nullable=True)        # assessment|scan|audit|pentest|self_report
    severity             = Column(String, default="Moderate")   # Critical|High|Moderate|Low|Informational
    responsible_party    = Column(String, nullable=True)
    resources_required   = Column(Text, nullable=True)
    scheduled_completion = Column(String, nullable=True)        # ISO date
    status               = Column(String, default="open")       # open|in_progress|closed|risk_accepted|false_positive
    remediation_plan     = Column(Text, nullable=True)
    completion_date      = Column(String, nullable=True)        # ISO date (actual)
    comments             = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=_now)
    updated_at           = Column(DateTime, default=_now, onupdate=_now)
    created_by           = Column(String, nullable=True)


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
    role                  = Column(String, default="employee")  # employee|auditor|bcdr|system_owner
    notifications_email   = Column(Boolean, default=True)
    notifications_quiz    = Column(Boolean, default=True)
    quiz_domains          = Column(Text, nullable=True)         # JSON list e.g. ["D1","D3"]
    created_at            = Column(DateTime, default=_now)
    updated_at            = Column(DateTime, default=_now, onupdate=_now)


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
    ]
    # Performance indexes — CREATE INDEX IF NOT EXISTS is idempotent
    index_migrations = [
        "CREATE INDEX IF NOT EXISTS ix_control_results_assessment_id ON control_results (assessment_id)",
        "CREATE INDEX IF NOT EXISTS ix_poam_items_system_id           ON poam_items (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_poam_items_assessment_id       ON poam_items (assessment_id)",
        "CREATE INDEX IF NOT EXISTS ix_risks_system_id                ON risks (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_system_assignments_system_id   ON system_assignments (system_id)",
        "CREATE INDEX IF NOT EXISTS ix_system_assignments_remote_user ON system_assignments (remote_user)",
        "CREATE INDEX IF NOT EXISTS ix_audit_log_remote_user          ON audit_log (remote_user)",
        "CREATE INDEX IF NOT EXISTS ix_assessments_system_id          ON assessments (system_id)",
    ]
    async with engine.begin() as conn:
        for table, col, col_def in col_migrations:
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            cols = [row[1] for row in result.fetchall()]
            if col not in cols:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
        for idx_sql in index_migrations:
            await conn.execute(text(idx_sql))


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
