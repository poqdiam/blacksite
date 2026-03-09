# BLACKSITE — System Context Reference for LLM
## Routes, Roles, Data Models, and GRC Workflows

This document describes BLACKSITE's architecture, user roles, key routes, and GRC workflows.
It is the primary LLM context document for answering "how does BLACKSITE work?" questions.

---

## System Overview

BLACKSITE is a web-based GRC (Governance, Risk, and Compliance) platform for managing:
- System Security Plans (SSP) per NIST RMF
- Plan of Action and Milestones (POA&M)
- Risk registers
- ATO (Authorization to Operate) packages
- Continuous monitoring and daily operational workflows
- Multi-system portfolio management for ISSMs and AOs

**Stack**: FastAPI + SQLite (WAL mode) + Jinja2 templates + HTMX
**Auth**: Reverse proxy (Caddy/Authelia) injects `Remote-User` header; BLACKSITE reads it for session
**Port**: 8100 (local), served at blacksite.borisov.network via Caddy

---

## Role Taxonomy

### Platform Tiers (company-wide)
| Tier | Roles | Access Level |
|------|-------|-------------|
| principal | All system roles | Full access + admin |
| executive | ao, ciso | Cross-portfolio visibility |
| manager | issm, system_owner, pmo | Portfolio/program management |
| analyst | isso, sca | System-level operations |

### System Roles (per-system assignment)
| Role | Abbreviation | Primary Function |
|------|-------------|-----------------|
| Authorizing Official | ao | Signs ATO; accepts risk |
| AO Designated Representative | aodr | Reviews packages on AO behalf |
| Chief Information Security Officer | ciso | Program oversight |
| Info System Security Manager | issm | Manages ISSOs; portfolio view |
| Info System Security Officer | isso | Day-to-day security operations |
| Security Control Assessor | sca | Independent assessment |
| System Owner | system_owner | Business accountability |
| Project Management Office | pmo | Schedule and resources |
| Incident Responder | incident_responder | IR procedures |
| BCDR Coordinator | bcdr_coordinator | Continuity and disaster recovery |
| Data Owner | data_owner | Data classification and privacy |
| Penetration Tester | pen_tester | Security testing |
| Auditor | auditor | Compliance review |

### Role-Task Mapping (Daily Workflow)
| Role | Daily Tasks |
|------|------------|
| isso | 1,2,3,4,5,6,7,8 (all 8) |
| issm | 1,2,6,8 |
| sca | 3,6,8 |
| system_owner | 2,6,8 |
| pmo | 6,7,8 |
| pen_tester | 1,3,8 |
| auditor | 3,6,8 |
| incident_responder | 1,4,8 |
| bcdr_coordinator | 4,8 |
| data_owner | 5,7,8 |

**Daily Task Definitions**:
1. Security event triage (review alerts, incidents, observations)
2. Change review (ticket-based change control)
3. Control status check (any controls drifted or failed)
4. Backup/recovery verification
5. Access spot check (HIPAA-required periodic review)
6. POA&M milestone check
7. Vendor/BAA status review
8. Logbook sign-off

---

## Key Routes

### Authentication / Session
- All routes require `Remote-User` header (injected by Caddy/Authelia)
- `GET /` → redirects to `/dashboard` based on role
- `GET /dashboard` → role-specific dashboard
- `GET /view-as/{username}` → admin view-as (HMAC-verified cookie)
- `GET /exit-view-as` → return to own session

### Admin Routes
- `GET /admin` → admin panel (admin only)
- `GET /admin/users` → user management
- `GET /admin/audit` → audit log with filters (actor, action, rtype, rid, outcome, q, days)
- `GET /admin/ingest` → data ingestion (JSON/CSV/XLSX)
- `POST /admin/ingest/upload` → upload file for preview
- `POST /admin/ingest/preview/{id}/commit` → commit ingestion
- `GET /admin/ssp` → SSP analyzer history
- `POST /admin/ssp/upload` → upload SSP for analysis
- `GET /admin/system-settings` → chat enable/disable, system settings

### System Routes
- `GET /systems` → list all assigned systems
- `GET /systems/{id}` → system detail (6 tabs: Overview, Controls, Daily Ops, RMF, ATO, Reports)
- `POST /systems` → create system (admin)
- `PATCH /systems/{id}` → update system

### SSP Routes
- `GET /ssp/{id}` → mode picker (full appendices vs controls-only)
- `GET /ssp/{id}?mode=full` → full SSP with appendices
- `GET /ssp/{id}?mode=controls` → controls-only view

### POA&M Routes
- `GET /poam/{id}` → POA&M item detail
- `GET /poam/list` → all POA&Ms (with status filter)
- `POST /poam/create` → create POA&M item
- `POST /poam/{id}/update` → update status, fields
- `POST /poam/{id}/evidence` → upload closure evidence

**POA&M ID Format**: `{SYSABBR}{YYYYMM}-{NNNN}AC{NN}` (e.g., `BSV022826-1001AC01`)

### Daily Workflow Routes
- `GET /systems/{id}/daily` → daily hub (task cards + rotation widget)
- `POST /systems/{id}/daily/save` → save task completion + logbook
- `GET /systems/{id}/daily/history` → 30-day logbook calendar
- `GET /systems/{id}/daily/change-review` → Task 2 sub-form
- `GET /systems/{id}/daily/backup-check` → Task 4 sub-form
- `GET /systems/{id}/daily/access-spotcheck` → Task 5 sub-form (HIPAA)
- `GET /systems/{id}/rotation` → current rotation day (25-day deep work cycle)
- `POST /systems/{id}/rotation/complete` → complete day, advance cycle
- `GET /issm/daily` → ISSM portfolio roll-up

### Risk Routes
- `GET /risks` → risk register
- `POST /risks/create` → create risk item
- `POST /risks/{id}/accept` → AO risk acceptance

### ATO Routes
- `GET /ato` → ATO dashboard
- `GET /ato/{id}` → system ATO package
- `POST /ato/{id}/{key}/upload` → upload ATO document
- `POST /ato/{id}/{key}/generate` → generate ATO document (background task)
- `POST /ao/decisions/{id}` → AO decision (approve/authorize with duration)

### Report Routes
- `GET /systems/{id}/reports` → generated reports list
- `POST /systems/{id}/reports/generate` → trigger report generation
- `GET /systems/{id}/reports/{rid}/download` → download report

### Compliance Record Routes
- `GET/POST /systems/{id}/vendors` → vendor + BAA registry
- `GET/POST /systems/{id}/interconnections` → ISA records
- `GET/POST /systems/{id}/dataflows` → data flow records
- `GET/POST /systems/{id}/privacy-assessments` → PTA/PIA records
- `GET/POST /systems/{id}/restore-tests` → restore test records

### API Routes
- `GET /api/version` → build stamp (env, branch, sha, build_time)
- `GET /api/feeds/user` → user's RSS feed subscriptions
- `PATCH /api/preferences` → update user display preferences
- `POST /api/heartbeat` → session keepalive
- `GET /api/notifications` → notification inbox
- `POST /api/notifications/mark-read` → mark notifications read

---

## Key Data Models

### UserProfile
```
id, username (= Remote-User header value), display_name, role (system role),
company_tier, is_admin (bool), is_frozen (bool), pref_font_size, pref_density,
pref_rows_per_page, created_at, last_seen
```

### System (InformationSystem)
```
id (UUID), name, abbreviation, description, boundary, overall_impact,
fips_category (LOW/MODERATE/HIGH), is_eis (bool), is_hipaa (bool),
owner, auth_date, ato_date, ato_expiry, cat_status, rmf_step,
created_by, created_at, updated_at
```

### SystemControl
```
id, system_id (FK), control_id (e.g. AC-2), status, implementation_status,
inherited_from, notes, last_reviewed, reviewed_by, created_at
```

### PoamItem
```
id, system_id (FK), poam_id (auto-generated format), control_id, title,
description, status, severity, scheduled_completion, actual_completion,
responsible_party, resources_required, milestones (JSON), risk_level,
approval_stage, residual_risk, signoff_trail (JSON), created_by, created_at
```

### AuditLog
```
id, remote_user, action, resource_type, resource_id, details (JSON),
remote_ip, outcome (ok/denied/error), timestamp
```

### DailyLogbook
```
id, remote_user, system_id, log_date, task_flags (JSON {1:bool..8:bool}),
notes, snap_open_poams, snap_overdue_poams, snap_open_risks, snap_open_obs,
snap_open_incidents, created_at
```

### DeepWorkRotation (25-day cycle)
```
id, remote_user, system_id, role_variant, current_day (1-25),
last_work_date, paused (bool), quarterly_overrides (JSON), created_at
```

### Vendor (BAA tracking)
```
id, system_id, name, service_type, handles_ephi (bool), has_baa (bool),
baa_expiry, contact_name, contact_email, status, notes
```

---

## GRC Workflow: POA&M Lifecycle in BLACKSITE

1. **Discovery**: Finding identified during assessment (SCA) or monitoring (ISSO)
2. **Creation**: `POST /poam/create` — control_id, description, severity, milestone
3. **ID Assignment**: Auto-generated `{SYSABBR}{YYYYMM}-{NNNN}AC{NN}`
4. **ISSO Work**: Status = in_progress; milestone updates; evidence uploads
5. **Closure Request**: ISSO sets status = pending_verification; uploads closure evidence
6. **SCA Review**: SCA verifies closure; signs off or rejects
7. **AO Review**: AO approves closure or accepts residual risk
8. **Closed**: Final status = closed; closure date recorded
9. **Monitoring**: Closed POA&Ms reviewed in continuous monitoring cycle

**Status Ownership (POAM_PUSH_POWER)**:
- open → ISSO can update
- in_progress → ISSO updates, ISSM can view
- pending_verification → SCA action required
- pending_ao_decision → AO action required
- closed / accepted_risk → read-only

---

## GRC Workflow: ATO Package in BLACKSITE

1. **System Created**: ISSO creates system record, sets FIPS category
2. **SSP Drafted**: Controls selected, narratives written
3. **SAP Prepared**: Assessment plan uploaded as ATO document
4. **Assessment Conducted**: SCA uploads SAR with findings
5. **POA&Ms Created**: All findings tracked
6. **ATO Package Compiled**: SSP + SAR + POA&M + Executive Summary
7. **AO Review**: AO views package, reviews risk summary
8. **AO Decision**: Approve with duration (1yr/3yr/5yr/ongoing/custom)
9. **ATO Letter**: Generated or uploaded; ato_date and ato_expiry set
10. **Monitor**: Monthly vuln scans, POA&M updates, annual review

---

## Common BLACKSITE Questions and Answers

**Q: How do I add a new user?**
A: Admin → Users → Provision User (requires executive or admin role). Fill display name, assign system roles via ProgramRoleAssignment.

**Q: Why is a control showing "inherited"?**
A: The control is provided by a common control provider (e.g., the cloud platform). The ISSO documents the inheritance source and any gap.

**Q: What is the difference between a risk and an observation?**
A: An observation is a factual finding from an assessment. A risk is a threat-vulnerability pair with likelihood/impact. A finding becomes a POA&M; a risk may become a risk acceptance.

**Q: When does an ATO expire?**
A: When ato_expiry date is reached OR when a significant change occurs that invalidates the authorization (e.g., new data types, major architecture change, security breach).

**Q: What triggers re-authorization?**
A: Significant system changes, expiration of ATO term, AO discretion, or FISMA/FedRAMP continuous monitoring findings requiring re-assessment.
</content>
</invoke>