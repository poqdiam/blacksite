# BLACKSITE — Multi-Node Scaling Design Memo

**Date:** 2026-03-01
**Platform:** BLACKSITE (TheKramerica Security Assessment Platform)
**Version:** Phase 21 architecture
**DB:** `blacksite.db` (SQLite, WAL mode, 256 MB mmap, 20 MB page cache)
**Author:** Engineering

---

## 1. Record Types Driving Load and Storage

The current schema holds 35 tables. The subset below accounts for the vast majority of row volume and I/O pressure at scale.

| Table | Growth Driver | Est. Rows / System / Year | Projected at 500 Systems |
|---|---|---|---|
| `security_events` | Every HTTP request + auth event; written on every page load | 50,000–200,000 / year (active system) | 25M–100M total / year |
| `system_controls` | 1,196 controls × systems count; bulk-imported on each system | 1,196 | ~600,000 static; grows with each NIST import |
| `control_results` | All control checks from every `assessment` uploaded | ~1,200 / assessment | Unbounded; 10 assessments/system = 6M+ |
| `audit_log` | Written for every CREATE / UPDATE / DELETE / LOGIN / EXPORT | 2,000–10,000 / year / active user | Accumulates without TTL |
| `poam_items` | One row per weakness; many fields are long `Text` blobs | 50–500 / system / year | 25,000–250,000 |
| `ato_document_versions` | Immutable snapshot on each `AtoDocument` state transition | 5–15 snapshots / doc × ~10 doc types / system | Grows with every review cycle |
| `ato_workflow_events` | Immutable workflow transition log | ~20 events / system / year | 10,000 / year at 500 systems |
| `observations` | Pre-POA&M findings inbox; promoted or aged out | 100–500 / system / year | Persistent if not pruned |
| `artifacts` | Evidence artifacts with `description` and `file_path` | 200–1,000 / system | 100,000–500,000 |
| `admin_chat_messages` | Real-time chat; no TTL or archival currently | Unbounded | Dominant at high user counts |

**Primary pressure point:** `security_events` is by far the highest-velocity table. At 11 non-admin users (per `config.yaml`), writes are modest today. At 50+ concurrent users the table will exceed 1M rows within months, making it the first bottleneck for SQLite's single-writer lock.

**Secondary pressure point:** `system_controls` × `control_results` creates the widest read fan-out. The AAMF notional system alone holds 1,196 `system_controls` rows. At 500 systems this is ~600,000 rows with heavy TEXT columns (`narrative`, `implementation_type`), placing GRC dashboard queries in the multi-second range without partitioning.

---

## 2. Multi-Node Model

### Recommended Architecture: Vertical Partitioning (Functional Sharding) + Single Write Primary

Do not shard by hash or range at this stage. The access patterns do not support it cleanly — most queries join `systems` to `poam_items`, `system_controls`, and `artifacts` in a single transaction, so horizontal sharding would turn every routine page load into a distributed join.

**Recommended topology:**

```
Node A  — GRC Core (systems, poam_items, system_controls, risks,
                     rmf_records, submissions, ato_documents,
                     ato_document_versions, ato_workflow_events,
                     observations, artifacts, assessments,
                     control_results, candidates)

Node B  — Event / Audit  (security_events, audit_log,
                           admin_chat_messages, admin_chat_receipts,
                           notifications)

Node C  — Identity / Config  (user_profiles, program_role_assignments,
                               duty_assignments, system_assignments,
                               system_settings, user_feed_subscriptions,
                               controls_meta, ingest_jobs, ssp_reviews)
```

Routing logic is compile-time, not runtime: each `SessionLocal` is replaced by three named factories (`grc_session`, `event_session`, `identity_session`) bound to their respective database files. No proxy layer or connection router is needed. The `make_engine` / `make_session_factory` functions in `models.py` already accept a `config` dict — the `db.path` key is extended to `db.grc_path`, `db.event_path`, `db.identity_path`.

**Sharding key (if Node A must be split further):** `system_id` (UUID). Every high-volume GRC table — `poam_items`, `system_controls`, `observations`, `artifacts`, `ato_documents` — carries `system_id`. A consistent hash on `system_id` into N buckets (starting with 2) keeps all per-system rows co-located, eliminating cross-shard joins for the common case.

**Node creation trigger criteria:**

- Node A exceeds 2 GB (SQLite's practical performance cliff with WAL and 256 MB mmap)
- `system_controls` + `control_results` query P95 latency exceeds 500 ms
- Node B `security_events` insert latency causes measurable backpressure on request handlers

---

## 3. Overhead Estimate

| Concern | Estimate | Notes |
|---|---|---|
| Engineering effort (initial split) | 3–4 weeks | Refactor `SessionLocal` references in `main.py` (>1,500 lines); update `init_db` lifespan; add per-node migration path |
| Engineering effort (sharding Node A) | 6–8 additional weeks | Router logic, `system_id`-aware session dispatch, cross-shard reporting queries |
| Ops complexity | Medium | Three `blacksite.db`-equivalent files to back up, monitor, and VACUUM independently; `backup-all.sh` must cover all three |
| Data consistency risk | Low–Medium | Vertical split introduces no distributed transactions; sharding introduces split-brain risk on `system_id` reassignment or cross-node foreign key checks |
| Reporting complexity | High if sharded | Cross-system aggregate queries (e.g., org-wide POAM dashboard, AO decisions page) will require application-level fan-out and merge; no SQLite equivalent of `UNION ALL` across attached databases in async sessions |

The session enforcement middleware (`_LAST_ACTIVITY` dict in `main.py`) and in-process settings cache (`_SYSTEM_SETTINGS_CACHE`) are currently global in-process state. These become incorrect under multi-process or multi-node deployment without a shared cache layer (Redis or equivalent). This is a prerequisite dependency, not a consequence.

---

## 4. Threshold Strategy

**Recommendation: growth-triggered with fixed floor, not fixed-count.**

A fixed threshold (e.g., "split at 100,000 rows in `security_events`") is brittle — row count does not directly predict query latency or WAL contention. The meaningful signal is I/O wait and lock contention.

**Trigger thresholds to monitor:**

| Metric | Warning | Action |
|---|---|---|
| `blacksite.db` file size | 500 MB | Begin Node B split planning |
| `blacksite.db` file size | 1.5 GB | Execute Node B split |
| `security_events` row count | 5M | Truncate rows older than 90 days (add `retention_days` to `config.yaml`) |
| `/health` endpoint P95 latency | > 300 ms sustained | Investigate WAL checkpoint stall; consider Node A split |
| `PRAGMA wal_size` | > 50 MB | Force checkpoint; if recurring, split Node A |
| `system_controls` row count | > 500,000 | Node A `system_id` sharding justified |

**Implementation:** Add a `GET /api/metrics/db` endpoint (admin-only) that returns `PRAGMA page_count`, `PRAGMA freelist_count`, WAL size, and row counts for the top five tables. Wire these into the existing `system_metrics.md` monitoring baseline. The `config.yaml` `db.path` key becomes the sole change point for routing; no application logic changes are needed until the functional split is executed.

---

## 5. Migration and Rollback Plan

### Migration: Single SQLite to Vertical Partition (Node B split first)

This is the lowest-risk first step — `security_events` and `audit_log` have no foreign key dependencies on GRC tables pointing inward; they are pure append logs.

1. **Prepare.** Add `db.event_path: "blacksite_events.db"` to `config.yaml`. Add a second `make_engine` call in the `lifespan` context in `main.py` bound to `event_path`.

2. **Create schema on Node B.** Call `init_db` with the event engine; `Base.metadata.create_all` scoped to `security_events`, `audit_log`, `admin_chat_messages`, `admin_chat_receipts`, `notifications`.

3. **Dual-write period (one release cycle).** Route all inserts to both the original `blacksite.db` and the new event engine. Reads go to the original. This confirms the new engine is healthy before cutover.

4. **Data migration.** Run a one-time script: `INSERT INTO blacksite_events.security_events SELECT * FROM blacksite.security_events`. Use batches of 50,000 rows to avoid locking. Total migration window at 5M rows: approximately 10–20 minutes offline or zero-downtime with dual-write already active.

5. **Cutover.** Flip reads to Node B. Remove dual-write. Run `DROP TABLE security_events` on `blacksite.db` after one week of confirmed clean operation.

6. **Repeat** for Node C (identity tables) and Node A split if warranted.

### Rollback Procedure

Because dual-write is maintained through the cutover window, rollback is a single-line config change:

1. Revert `config.yaml` to `db.path: "blacksite.db"` only; remove `db.event_path`.
2. Restart the service: `sudo systemctl restart blacksite` (or `nohup` re-launch on port 8100 per current deployment).
3. The original `blacksite.db` retains all rows written during dual-write; no data is lost.
4. Archive the partial `blacksite_events.db` for audit purposes; do not delete.

The rollback window is bounded by the dual-write period. If dual-write is skipped, rollback requires replaying the migration script in reverse (copy rows from Node B back to `blacksite.db`), which adds approximately 30–60 minutes of downtime risk. Do not skip dual-write.
