# BLACKSITE GRC Platform — System Metrics and Scalability Report

Generated: 2026-02-28
Platform: BLACKSITE v12 (Phase 12 complete — FedRAMP alignment, Observations, Inventory, Artifacts, Connections)

---

## Current Codebase Metrics

### Lines of Code (wc -l)

| File | Lines |
|---|---|
| app/main.py | 7,231 |
| app/models.py | 758 |
| app/rss_feed.py | 231 |
| **Total** | **8,220** |

### Routes and Endpoints

| Metric | Count | Method |
|---|---|---|
| Total `@app.` route decorators | 135 | grep -c "@app\." app/main.py |
| JSON/API endpoints (JSONResponse) | 35 | grep -c "response_class=JSONResponse\|return JSONResponse" |
| HTML page routes | ~85 | Estimated (135 minus JSON/redirect/API) |
| Distinct URL path patterns | ~90 | From docstring + code review |

### Templates

| Metric | Count |
|---|---|
| HTML templates | 55 |
| Base template (shared layout) | 1 (base.html) |
| Macro file (shared components) | 1 (macros.html) |
| Page-specific templates | 53 |

Notable templates: admin.html, ato_dashboard.html, ato_system.html (4-accordion FedRAMP), issm_dashboard.html, bcdr_dashboard.html, system_owner_dashboard.html, ao_decisions.html, sca_workspace.html, posture.html, observations.html, inventory.html, connections.html, artifacts.html, eis_assessment.html

### Database Models

| Metric | Count |
|---|---|
| SQLAlchemy model classes (class.*Base) | 28 |
| DB tables (one-to-one with models) | 28 |

#### Full Table Inventory by Phase

| Table | Phase | Purpose |
|---|---|---|
| candidates | 1 | SSP candidate tracking |
| assessments | 1 | SSP assessment records with scores |
| control_results | 1 | Per-control AI grading results |
| quiz_responses | 1 | Assessment quiz answers |
| daily_quiz_activity | 1 | Daily quiz streak/score tracking |
| controls_meta | 1 | NIST catalog version metadata |
| systems | 3 | IT system catalog (FIPS 199 aligned) |
| poam_items | 3 | DHS Attachment H POA&M items |
| risks | 3 | Risk register |
| user_profiles | 3 | RBAC role assignments and preferences |
| audit_log | 3 | NIST AU-2/AU-12 audit trail |
| security_events | 3/13 | SIEM middleware event log |
| system_assignments | 4 | User-to-system access control bindings |
| control_edits | 4 | Control narrative edit history |
| system_controls | 5 | Per-system control implementation plan |
| submissions | 5 | ATO authorization package submissions |
| rmf_records | 6 | Per-system RMF 7-step tracking |
| ato_documents | 7 | ATO artifact workflow (52 document types) |
| ato_document_versions | 7 | Immutable ATO document version snapshots |
| ato_workflow_events | 7 | ATO workflow transition log |
| system_teams | 10 | Recovery/response teams per system |
| team_memberships | 10 | User-to-team assignment |
| bcdr_events | 10 | BCDR drill/incident/recovery events |
| bcdr_signoffs | 10 | Required sign-off tracking per BCDR event |
| observations | 12 | Pre-POA&M findings staging (FedRAMP gap) |
| inventory_items | 12 | Hardware/software/firmware inventory |
| system_connections | 12 | Boundary connection/ISA records |
| artifacts | 12 | Evidence artifacts with SHA-256 integrity |

### ATO Document Types

52 total ATO document types in the ATO_DOC_TYPES registry, organized into 4 categories:

| Category | Count | Description |
|---|---|---|
| core | 18 | Standard ATO package documents (FIPS199/SSP/SAP/SAR/etc.) |
| authorization | 14 | FedRAMP authorization package appendices |
| preparation | 12 | FedRAMP readiness assessment templates and guides |
| conmon | 7 | Continuous monitoring deliverables |

### Technology Stack

| Component | Technology | Details |
|---|---|---|
| Web framework | FastAPI | Async, Starlette-based; lifespan context manager |
| ORM | SQLAlchemy 2.x | Async mode (create_async_engine + AsyncSession) |
| Database | SQLite via aiosqlite | WAL mode; fully async I/O |
| Template engine | Jinja2 | Via FastAPI Jinja2Templates; custom fromjson filter |
| HTTP client | httpx | Used for CISA KEV fetch in ticker endpoint |
| File I/O | aiofiles | Async SSP upload writes |
| Auth (external) | Authelia | Reverse proxy; injects Remote-User/Remote-Groups headers |
| TLS/Proxy | Caddy | forward_auth to Authelia; DNS-01 Cloudflare ACME |
| Process manager | systemd | blacksite.service on port 8100 |
| Password hashing | argon2id | Via Authelia container subprocess (docker exec) |
| Config | PyYAML | config.yaml; employees/quiz/storage/db config |
| NIST catalog | JSON files | SP 800-53r5; 1,196 controls loaded into memory dict at startup |

---

## Performance Characteristics

### SQLite Configuration (applied per connection in _configure_sqlite)

```
PRAGMA journal_mode=WAL        -- WAL mode: concurrent readers + 1 writer
PRAGMA synchronous=NORMAL      -- Safe with WAL; 3-5x faster than FULL
PRAGMA cache_size=-20000       -- 20 MB page cache per connection
PRAGMA temp_store=MEMORY       -- Temp tables in RAM
PRAGMA mmap_size=268435456     -- 256 MB memory-mapped I/O
PRAGMA foreign_keys=ON         -- Enforce FK constraints
```

### Async Architecture

The application is fully async end-to-end:

- FastAPI + Uvicorn: async request handling; no thread blocking on HTTP
- aiosqlite: all DB queries use `await session.execute(...)`; no GIL contention on I/O wait
- aiofiles: SSP uploads written without blocking the event loop
- Background tasks: SSP processing (parse + assess) runs in FastAPI BackgroundTasks via `run_in_executor` (thread pool) so parsing CPU work does not block the event loop

### Caching

| Cache | TTL | Scope |
|---|---|---|
| NIST catalog (CATALOG dict) | Process lifetime (no expiry) | In-memory; loaded once at startup via update_if_needed + load_catalog |
| Security ticker (_ticker_cache) | 60 minutes | In-process dict; reused across requests until ts + 3600 seconds elapses |
| Provision tokens (_provision_tokens) | 5 minutes | In-process dict; TTL-pruned on each new token creation |

No Redis or external cache layer. All session state is either stateless (Authelia JWT cookies) or stored in SQLite.

### Estimated Response Times (p50 / p95) on 4-core server

| Route | Operation | p50 | p95 | Notes |
|---|---|---|---|---|
| GET /dashboard | 3 async DB queries (quiz activity/assessments/assigned systems) | ~25ms | ~60ms | Scales with POA&M/system count |
| GET /admin | 8 async DB queries (assessments/systems/POA&Ms/risks/audit) | ~40ms | ~90ms | More queries; still fast on WAL |
| GET /poam | 4-6 async DB queries with filters + pagination | ~30ms | ~70ms | Indexed on system_id/status |
| GET /systems/{id} | 10 async DB queries (system/assessments/POA&Ms/risks/audit/controls/assignments/RMF/inventory/connections/artifacts) | ~45ms | ~100ms | Most query-heavy page |
| GET /controls | In-memory CATALOG filtering + pagination | ~8ms | ~20ms | No DB query; pure Python |
| GET /issm/dashboard | N+1 queries per ISSO (pkg_count/open_poams/overdue/quiz) | ~80ms | ~200ms | Scales O(N) with ISSO count |
| GET /ato/{id} | 2-3 DB queries (system/ATO docs/role check) | ~20ms | ~50ms | |
| POST /upload | File I/O + DB inserts + background task launch | ~60ms | ~150ms | SSP processing async in background |
| SSP processing (background) | Parse SSP + AI assess all 1,196 controls | ~30-120s | N/A | Depends on SSP size and control count |
| GET /api/ticker | DB queries + CISA KEV HTTP fetch (cached 60min) | ~10ms cached / ~500ms uncached | ~1.5s uncached | External HTTP call is the bottleneck |
| GET /api/alerts | 6 DB COUNT queries | ~20ms | ~50ms | Indexed queries |

### SIEM Middleware Overhead

Every response through the SIEM middleware may trigger an additional async DB write to security_events for:
- Any HTTP 4xx/5xx responses
- Any path containing /admin, login, auth, switch-role, shell, exit-shell

This adds approximately 5-15ms per logged request for the DB write. Non-logged requests (2xx on non-admin routes) pass through with <1ms middleware overhead.

### Security Headers Middleware Overhead

SecurityHeadersMiddleware adds 6 response headers to every non-static response. Overhead is negligible (<0.5ms).

---

## Scalability Analysis

### SQLite Concurrent Write Limits

WAL mode allows:
- **Concurrent reads**: Unlimited; readers do not block each other or writers
- **Concurrent writes**: Only 1 writer at a time; additional write attempts block until the lock is released
- **Write lock contention**: SIEM middleware writes on every logged request; under high traffic this becomes the primary write bottleneck

Write-intensive paths that cause contention:
1. SIEM middleware (security_events INSERT on every admin/error request)
2. Audit log (audit_log INSERT on every CREATE/UPDATE/DELETE/EXPORT)
3. last_login UPDATE in _full_ctx (fires on every HTML page render for authenticated users)
4. Background SSP processing (bulk INSERT of control_results; hundreds to thousands of rows)

### Realistic User Ceiling (Current Stack)

| Scenario | Concurrent Users | Systems | Assessment Volume | Notes |
|---|---|---|---|---|
| Comfortable | 5-15 | 1-10 | <5 SSPs/day | No write contention; p50 well under 100ms |
| Workable | 15-30 | 10-30 | 5-20 SSPs/day | Some WAL write queuing; p95 may hit 200-400ms during bursts |
| Stressed | 30-50 | 30-50 | 20-50 SSPs/day | SIEM write contention noticeable; audit_log grows rapidly |
| Breaking point | 50+ | 50+ | 50+ SSPs/day | SQLite WAL write serialization causes timeout errors; security_events table bloat |

### What Breaks First

In order of failure:
1. **SIEM middleware write contention** — every admin page hit writes to security_events; under concurrent admin sessions this serializes. Mitigation: move SIEM writes to BackgroundTasks.
2. **last_login UPDATE on every HTML render** — fires in _full_ctx for every authenticated page; creates write lock on every request. Mitigation: debounce to once-per-session or use a separate async task.
3. **audit_log INSERT on every mutation** — compound with SIEM, creates sustained write pressure. Mitigation: batch writes or move to async queue.
4. **security_events table bloat** — unlimited growth; no TTL or archival. At 50 req/min this generates ~72,000 rows/day. Mitigation: add periodic cleanup or rolling window table.
5. **SQLite file I/O saturation** — at very high volume, even WAL reads can be slow if the WAL file itself grows large between checkpoints. Mitigation: explicit PRAGMA wal_checkpoint(TRUNCATE) on a timer.
6. **CISA KEV fetch blocking** — /api/ticker fetches from cisa.gov with an 8s timeout. On cache miss under concurrent load, all waiting requests block on the same external HTTP call. Mitigation: run fetch in a background task; serve stale data.

### Performance Indexes (defined in _migrate_db)

11 explicit indexes created at startup:
- ix_control_results_assessment_id
- ix_poam_items_system_id
- ix_poam_items_assessment_id
- ix_risks_system_id
- ix_system_assignments_system_id
- ix_system_assignments_remote_user
- ix_audit_log_remote_user
- ix_assessments_system_id
- ix_ato_documents_system_id
- ix_ato_doc_versions_document_id
- ix_ato_workflow_events_document_id

Additionally, ix_sysctl_system_ctrl (unique compound index on system_controls.system_id + control_id) is defined on the model.

---

## Migration Path to PostgreSQL + Redis + Multi-Worker

### Phase 1: PostgreSQL (Unlocks Concurrent Writers)

Changes required:
1. Replace `sqlite+aiosqlite:///` URL with `postgresql+asyncpg://` in get_db_url()
2. Remove `_configure_sqlite` and the `event.listen` call in make_engine()
3. Replace raw `text()` SQL in _migrate_db with proper Alembic migrations
4. Remove SQLite-specific PRAGMAs (WAL/synchronous/cache_size/mmap_size/temp_store/foreign_keys)
5. Replace `PRAGMA table_info(table)` column introspection with `information_schema.columns` or Alembic autogenerate
6. Test: UniqueConstraint on system_controls(system_id, control_id) is portable
7. Estimated effort: 1-2 days

Gains: True concurrent writes; read replicas possible; connection pooling via asyncpg

### Phase 2: Redis (Cache + Session + Queue)

Changes required:
1. Add aioredis dependency
2. Move ticker cache (_ticker_cache dict) to Redis with SETEX 3600
3. Move provision tokens (_provision_tokens dict) to Redis with TTL 300
4. Move CISA KEV fetch to a scheduled background job (APScheduler or Celery beat); serve from Redis cache
5. Move SIEM writes and audit_log writes to a Redis queue (LPUSH); add a consumer worker to batch-insert
6. Move last_login update to a Redis queue or debounce with SETNX key per user per hour
7. Estimated effort: 2-3 days

Gains: Eliminates write contention bottlenecks; CISA fetch decoupled from request path

### Phase 3: Multi-Worker (Horizontal Scale)

Changes required:
1. Switch from single systemd service to Uvicorn with `--workers N` or Gunicorn + Uvicorn workers
2. Ensure all in-process state is externalized (done in Phase 2): _ticker_cache, _provision_tokens
3. Ensure NIST CATALOG dict is either loaded per-worker at startup (acceptable; it is read-only) or served from Redis (optional optimization)
4. Confirm SSP background processing is safe with multiple workers (each worker has its own BackgroundTasks thread pool; no shared state issues)
5. Estimated effort: 0.5 days (mostly config)

Gains: Linear horizontal CPU scaling; fault isolation between workers

### Phase 4: Full Cloud Stack (Enterprise Grade)

Additional components:
- PostgreSQL with read replicas (AWS RDS Multi-AZ or equivalent)
- Redis Cluster for cache and Celery broker
- Celery workers for SSP processing (decouple from web workers)
- CDN (CloudFront/Cloudflare) for /static/ assets
- Kubernetes HPA for web tier auto-scaling
- Object storage (S3) for SSP uploads and artifacts (replace local filesystem at uploads/)
- Dedicated audit/SIEM pipeline (ship security_events to Elasticsearch or Splunk)

Estimated capacity at full cloud stack: 500-2000 concurrent users; 100+ systems; unlimited assessment volume.

---

## Deployment Speed

### Current Deployment (Systemd, Single Server, Python venv)

| Step | Estimated Time |
|---|---|
| git clone (source only) | ~5s |
| pip install -r requirements.txt | 60-120s (first install; wheels vary) |
| Copy config.yaml with DB path and app settings | ~30s |
| systemctl enable + start blacksite.service | ~5s |
| DB init (init_db + _migrate_db at startup) | ~3s (SQLite) |
| NIST catalog load (JSON parse, ~1,196 controls) | ~1-2s |
| **Cold start to first request served** | **~2-4 minutes total** |
| **Warm restart (systemctl restart)** | **~5-10s** |

### Zero-Downtime Deployment Options

Current stack has no zero-downtime mechanism. Options:

1. **Systemd ExecStartPre** (simplest): validate config before stopping old process; minimizes downtime window to <5s restart
2. **Uvicorn --workers with graceful shutdown**: `kill -HUP` triggers graceful worker restart without dropping connections; works with PostgreSQL (not with SQLite WAL which has file locking)
3. **Blue/green via Caddy upstream switching**: run two instances on ports 8100 and 8102; update Caddy upstream; zero-downtime cutover
4. **Container (Docker)**: `docker compose up -d --no-deps --build blacksite` with health check; old container stays up until new one passes health check

### Container-Ready Assessment

The application is container-ready with minor changes:

Ready now:
- Config via config.yaml (can be mounted as volume)
- DB path configurable (config.get("db.path"))
- Static files via /static mount
- No hardcoded localhost assumptions (port from systemd/ENV)
- Health check endpoint at GET /health (returns JSON)

Requires changes for containers:
- Authelia provisioning subprocess (`docker exec authelia`) will fail in a container unless the host Docker socket is mounted (security risk) or the provisioning step is decoupled
- Upload/artifact storage uses local filesystem (uploads/ directory); needs volume mount or S3 migration for multi-container
- NIST catalog stored in controls/ directory; needs volume mount or embedding in image
- No Dockerfile exists yet in the repository; requires creation

---

## Security Posture

### Authentication and Authorization

| Layer | Implementation |
|---|---|
| Authentication | Authelia (external SSO); injects Remote-User header after one_factor gate |
| Session | Authelia JWT cookie (not managed by BLACKSITE) |
| Authorization | Custom RBAC in _get_user_role() + _require_role() |
| Role source | UserProfile.role column (SQLite) or CONFIG.app.admin_users list |
| Role hierarchy | ROLE_CAN_VIEW_DOWN dict; 6 levels: admin > ao > ciso > issm > isso > sca/employee |
| Role shell | bsv_role_shell cookie; admin or higher roles can shell into lower roles |
| Account states | active | frozen | removed; frozen accounts get 403 on all main routes via _full_ctx |
| Anonymous access | Blocked at route level (Remote-User header check); returns 401 |

### RBAC Summary

| Item | Count |
|---|---|
| Total roles | 14 (admin + 13 non-admin) |
| Shell-capable roles (can shell down) | 6 (admin/ao/ciso/issm/isso/sca) |
| Valid shell target roles | 13 (all non-admin roles in _VALID_SHELL_ROLES) |
| Observation-capable roles (_OBS_ROLES) | 6 (issm/isso/sca/auditor/system_owner/admin) |
| ATO document owner roles | 3 (system_owner/auditor/admin per doc type) |
| SSP upload roles | 2 (admin/sca) |

### Audit Logging (NIST AU-2/AU-12)

- AuditLog table: records CREATE/UPDATE/DELETE/VIEW/LOGIN/EXPORT actions
- Fields: timestamp/remote_user/action/resource_type/resource_id/details (JSON)
- Indexed on: timestamp (for range queries); remote_user (via migration)
- Audit export: /admin/audit/export as CSV or JSON; 90-day window default; itself logged as EXPORT
- Access: admin/issm/auditor can view via /admin/audit; admin-only export

### SIEM (Security Event Log)

- SecurityEvent table captures: http/login/failed_auth/access_denied/frozen_access/anomaly events
- SIEM middleware fires on: all 4xx/5xx responses + /admin/* paths + auth/shell paths
- Severity levels: info/low/medium/high/critical
- Fields: timestamp/event_type/severity/remote_ip/remote_user/method/path/status_code/user_agent/details
- Access: admin-only via /admin/siem; 24h stats dashboard + paginated event table

### Security Headers (SecurityHeadersMiddleware)

Applied to all non-/static/ responses:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'
```

Note: 'unsafe-inline' in script-src and style-src weakens CSP. Refactoring to nonce-based CSP would improve posture.

### Data Protection

| Control | Status |
|---|---|
| Encryption in transit | Caddy TLS (DNS-01 via Cloudflare; certificates auto-renewed) |
| Encryption at rest | Not implemented in application layer; depends on filesystem/disk encryption |
| File integrity | SHA-256 hash on artifact uploads (Artifact.integrity_hash column) |
| SSP file storage | Local filesystem at uploads/; no encryption; access controlled by OS permissions |
| Secrets management | SOPS-encrypted .secrets.env for all external credentials (Cloudflare API token, SMTP, etc.) |
| NIST catalog | Loaded from local JSON files; no external network calls at runtime (except CISA KEV optional fetch) |
| User passwords | argon2id via Authelia; BLACKSITE never sees or stores passwords |

---

## Large-Scale Environment Assessment

### Current Stack Capacity

**Suitable for**: Small agency or department GRC program

| Dimension | Capacity |
|---|---|
| Concurrent active users | 5-50 |
| Registered systems | 1-30 |
| POA&M items | Up to ~10,000 (indexed; still fast) |
| Assessments | Up to ~1,000 (control_results grows 1,196 rows per assessment) |
| Control results rows | Up to ~500,000 before query times noticeably degrade |
| Audit log retention | Configurable; 7-day vacuum recommended per CLAUDE.md notes |
| ISSO workload | Up to ~20 ISSOs visible in /issm/dashboard before N+1 query becomes slow |

### With PostgreSQL

**Suitable for**: Mid-size agency or multi-office deployment

| Dimension | Capacity |
|---|---|
| Concurrent active users | 50-500 |
| Registered systems | 10-100 |
| POA&M items | Millions (PostgreSQL MVCC eliminates write contention) |
| ISSM dashboard | 50-200 ISSOs (N+1 should be refactored to JOIN query) |
| Background SSP processing | Multiple simultaneous via asyncpg connection pool |

### With Full Cloud Stack (PostgreSQL + Redis + Kubernetes + CDN)

**Suitable for**: Enterprise or multi-agency deployment

| Dimension | Capacity |
|---|---|
| Concurrent active users | 500-5,000+ |
| Registered systems | 100-1,000+ |
| Assessment throughput | 100+ SSPs/day via Celery worker pool |
| CISA KEV | Cached in Redis; served from memory; zero latency |
| Artifact storage | S3 with presigned URLs; no local disk dependency |
| Zero-downtime deploy | Rolling pods in Kubernetes; health check at /health |

### Specific Architectural Changes Needed for Scale

1. **Refactor ISSM dashboard N+1 query** — Currently executes 2-4 DB queries per ISSO in a Python loop. Replace with single JOIN query grouping by remote_user.
2. **Move SIEM writes to background task** — `BackgroundTasks.add_task(...)` instead of inline await in middleware; eliminates write latency from request path.
3. **Debounce last_login update** — Currently fires on every _full_ctx call. Add per-user per-hour in-process set or Redis SETNX guard.
4. **Add pagination to /issm/dashboard** — Currently loads all ISSOs; add limit/offset.
5. **Implement audit_log TTL** — No automatic pruning; add a scheduled task or Alembic migration with partitioning (PostgreSQL) or periodic DELETE (SQLite).
6. **Decouple SSP processing to Celery** — SSP parsing (run_in_executor) uses the uvicorn thread pool; under concurrent uploads this exhausts threads. Celery worker pool handles backpressure.
7. **Add rate limiting** — No rate limiting on /upload or /api/* endpoints; under attack, SIEM log fills fast and upload directory grows unbounded.
8. **Externalize artifact storage** — Local uploads/ directory cannot be shared across multiple Uvicorn workers or container replicas; S3 or equivalent needed.

---

## Deployment Checklist

### Fresh Deploy Estimate

**Total time: 5-10 minutes** (excluding pip install network time)

```
# 1. Clone repository
git clone <repo> /opt/blacksite
cd /opt/blacksite

# 2. Create venv and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # ~60-120s

# 3. Configure
cp config.yaml.example config.yaml   # edit: db.path, app.name, employees, quiz settings
# config.yaml key sections: db.path, app.name, app.brand, app.admin_users, app.authelia_logout_url, employees[], quiz.pass_threshold, quiz.question_count, storage.uploads_dir

# 4. Install systemd service
sudo cp blacksite.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable blacksite
sudo systemctl start blacksite
# Service starts uvicorn on 0.0.0.0:8100

# 5. Verify
curl http://localhost:8100/health   # expected: {"status":"ok"} or similar
systemctl status blacksite          # should show active (running)
```

### First-Run Automatic Actions (on startup)

1. `init_db(engine)` — runs `Base.metadata.create_all` (creates all 28 tables if not present)
2. `_migrate_db(engine)` — applies all column and index migrations idempotently
3. NIST catalog loaded into `CATALOG` dict (requires controls/*.json or fetches from NIST)
4. Removed users older than 1 year are purged from user_profiles
5. uploads/ results/ controls/ static/ directories created if missing

### Data Migration Considerations

- SQLite to PostgreSQL: use `pgloader` or manual CSV export/import; migrate in order respecting FK constraints (systems before poam_items, etc.)
- Column migrations in _migrate_db use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` pattern; safe to run on existing DB
- No Alembic integration; schema changes are manual in `_migrate_db`; track via code diff

### Required Environment Variables and Config

| Variable | Source | Purpose |
|---|---|---|
| config.yaml: db.path | File | SQLite file path (e.g., blacksite.db) |
| config.yaml: app.admin_users | File | List of Authelia usernames with admin access |
| config.yaml: employees | File | List of {username, name, email} for email forwarding |
| config.yaml: app.authelia_logout_url | File | Authelia logout redirect URL |
| config.yaml: storage.uploads_dir | File | Upload directory path (default: uploads/) |
| Remote-User header | Authelia proxy | Authenticated username; BLACKSITE requires this header |
| Remote-Groups header | Authelia proxy | Optional; not currently used in RBAC logic |
| Docker socket (optional) | Runtime | Only needed for /admin/users/provision (Authelia argon2 hash generation) |

### Port and Service Configuration

| Item | Value |
|---|---|
| Default port | 8100 |
| Health check | GET /health |
| blacksite-co (alternate instance) | Port 8101 (manual; needs systemd per pending-manual-tasks) |
| Caddy upstream | blacksite.borisov.network -> localhost:8100 |
| Authelia gate | one_factor; bypasses /api/*, /auth/*, /local/*, /hacsfiles/*, /.well-known/* |
