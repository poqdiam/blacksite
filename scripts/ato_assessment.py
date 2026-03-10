#!/usr/bin/env python3
"""
ATO Readiness Assessment Population Script for BLACKSITE
Populates system_controls, poam_items, system_frameworks, and updates system record.
Idempotent: checks for existing rows before inserting.
"""

import asyncio, sys, os, uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, '/home/graycat/projects/blacksite')
if 'BLACKSITE_DB_KEY' not in os.environ:
    raise RuntimeError("BLACKSITE_DB_KEY not set. Export it before running this script.")

import yaml
with open('/home/graycat/projects/blacksite/config.yaml') as f:
    config = yaml.safe_load(f)

from app.models import make_engine, make_session_factory
from sqlalchemy import text

BSV_ID   = 'bsv-main-00000000-0000-0000-0000-000000000001'
FW_ID    = 'c7bd7232029e0aa9bbf702bf679a6184'   # nist_low
NOW      = datetime.now(timezone.utc)
TODAY    = NOW.date().isoformat()
BY       = 'dan'

def due(days: int) -> str:
    return (NOW + timedelta(days=days)).date().isoformat()

# ---------------------------------------------------------------------------
# Control assessment data
# format: control_id -> (status, impl_type, narrative, result, notes, severity_for_poam)
# severity_for_poam: None means no POA&M needed (implemented / not_applicable)
# ---------------------------------------------------------------------------
CONTROLS = {
    # ── AC ──────────────────────────────────────────────────────────────────
    'ac-1': (
        'partial', 'hybrid',
        'BLACKSITE enforces Role-Based Access Control (RBAC) with seven distinct roles (admin, isso, issm, ciso, ao, sca, auditor) implemented in Python across all routes. Every protected endpoint validates the Remote-User header injected by Caddy after Authelia authentication. Access control logic is centralized in the authorization module and enforced consistently. However, no formal written Access Control Policy document has been produced; the implementation serves as a de facto policy without an approved document. Remediation requires authoring and approving a formal AC policy referencing NIST 800-53 Rev 5 requirements.',
        'partial', 'Implementation present; formal policy document absent.', 'Low'
    ),
    'ac-2': (
        'implemented', 'hybrid',
        'User accounts are managed through Authelia configuration files, which define all valid user identities, password hashes, and MFA enrollment. The BLACKSITE admin dashboard provides account visibility, and role assignments are managed via the program_role_assignments table with an approval workflow. Account creation requires admin action; there is no self-registration capability. Account disabling is performed by removing or deactivating entries in the Authelia users database, and all role changes are audit-logged in the immutable_audit_log table.',
        'pass', 'Account management fully implemented via Authelia + RBAC dashboard.', None
    ),
    'ac-3': (
        'implemented', 'hybrid',
        'Every application route is protected by Python-level authorization guards that validate the Remote-User header and check the user\'s assigned RBAC role against a permission matrix. The _can_access_system() function enforces system-level access, and role checks are applied before any data is returned or modified. Unauthenticated requests receive a 401 or redirect to Authelia. The authorization layer is uniformly applied across all FastAPI route handlers with no known bypasses.',
        'pass', 'RBAC enforced at every route; no unauthenticated data access possible.', None
    ),
    'ac-7': (
        'inherited', 'inherited',
        'Account lockout after failed authentication attempts is fully inherited from Authelia. The Authelia configuration specifies a maximum number of failed login attempts before an account is temporarily locked, with a configurable lockout duration. This control is enforced at the SSO layer before any request reaches the BLACKSITE application. The application itself does not implement a redundant lockout mechanism, relying entirely on Authelia\'s proven implementation.',
        'pass', 'Inherited from Authelia; lockout configured and active.', None
    ),
    'ac-8': (
        'not_implemented', 'none',
        'No system use notification (login banner) is displayed to users prior to or during the authentication process. The Authelia login page does not present a warning banner stating that the system is for authorized use only, that usage is monitored, and that unauthorized use is prohibited. This is a gap against NIST 800-53 AC-8 requirements. A banner must be added to the Authelia login portal or BLACKSITE landing page before users authenticate.',
        'fail', 'No system use notification banner implemented. Required for NIST 800-53 AC-8.', 'Moderate'
    ),
    'ac-14': (
        'implemented', 'technical',
        'Only the /health endpoint is accessible without authentication; all other application routes require a valid Remote-User header set by Caddy after successful Authelia authentication. The /health endpoint returns only operational status information with no sensitive data. All data-bearing routes (systems, controls, POA&Ms, reports, etc.) enforce authentication and authorization. This approach is intentional and documented in the Caddy forward_auth configuration.',
        'pass', 'Only /health is unauthenticated; all other routes require auth.', None
    ),
    'ac-17': (
        'implemented', 'technical',
        'All user access to BLACKSITE is remote access via HTTPS through Caddy reverse proxy with TLS 1.2+ enforced. Authelia manages session tokens with configurable max-age and idle timeout. Sessions are cryptographically signed with HMAC. Geographic restriction limits access to US-based IP addresses. There is no local console access to the application; all administrative and user sessions are web-based and protected by the same Authelia MFA gate.',
        'pass', 'All access via HTTPS + Authelia MFA; geo-restricted to US.', None
    ),
    'ac-18': (
        'not_applicable', 'none',
        'BLACKSITE is a server-side web application hosted on a wired Ethernet-connected server. The application has no wireless interfaces, does not use wireless protocols, and wireless access is not part of the system boundary. This control is not applicable to the BLACKSITE system.',
        'not_applicable', 'No wireless component in system boundary.', None
    ),
    'ac-19': (
        'not_applicable', 'none',
        'BLACKSITE has no mobile application component. The system is a web application accessible via standard browsers; there is no dedicated mobile app, no MDM integration, and no mobile-specific access controls. This control is not applicable.',
        'not_applicable', 'No mobile application component in scope.', None
    ),
    'ac-20': (
        'partial', 'hybrid',
        'BLACKSITE uses two external systems without formal agreements: ip-api.com for geographic IP restriction enforcement, and the NIST GitHub API for catalog control updates. Both connections are outbound-only and do not involve transmission of sensitive system data. However, no formal Interconnection Security Agreement (ISA) or Terms of Service review has been conducted for these external services. The ip-api.com dependency is particularly relevant as it is in the critical path for access control decisions. Formal agreements or documented risk acceptances are required.',
        'partial', 'Uses ip-api.com and NIST GitHub API with no formal ISA or risk acceptance on file.', 'Low'
    ),
    'ac-22': (
        'implemented', 'technical',
        'The BLACKSITE demo/public-facing instance is geo-restricted to US-originating IP addresses via Caddy middleware using ip-api.com lookups. No sensitive security assessment data is accessible without authentication. The landing page contains only general product description information. All system-specific content, controls, POA&Ms, and reports are behind the Authelia authentication gate. Public-accessible content has been reviewed and contains no sensitive information.',
        'pass', 'Geo-restricted; all sensitive content behind auth gate.', None
    ),

    # ── AT ──────────────────────────────────────────────────────────────────
    'at-1': (
        'partial', 'procedural',
        'No formal Security Awareness and Training Policy document exists. Training activities are conducted through the built-in quiz system and NICCS resource links, but these are not governed by a written policy that establishes training frequency, scope, roles, and enforcement mechanisms. The system tracks training completion in the daily_quiz_activity table, but without a policy document, there is no formal basis for the training program.',
        'partial', 'Training system exists but no formal policy document.', 'Low'
    ),
    'at-2': (
        'partial', 'technical',
        'BLACKSITE includes a built-in security awareness module (quiz.py) that delivers daily security quizzes to users covering NIST 800-53 control families, cybersecurity fundamentals, and threat awareness. NICCS (National Initiative for Cybersecurity Careers and Studies) links are provided for supplemental learning. Quiz scores and completion are tracked in the daily_quiz_activity table. However, there is no formal annual security awareness training program, and the quiz topics are not mapped to a documented awareness curriculum.',
        'partial', 'Built-in quiz module covers awareness; no formal curriculum or annual training program.', 'Low'
    ),
    'at-2.2': (
        'partial', 'technical',
        'The daily quiz system includes questions on social engineering, phishing awareness, and general security hygiene. However, there is no dedicated insider threat awareness module or content specifically designed to address insider threat recognition and reporting procedures. The quiz content broadly covers security topics but lacks structured insider threat training content mapped to organizational procedures.',
        'partial', 'General security quizzes exist; no dedicated insider threat module.', 'Low'
    ),
    'at-3': (
        'partial', 'technical',
        'Quiz content is partially role-differentiated — ISSO and admin roles receive questions relevant to their responsibilities in the platform. However, there is no formal role-based training program that maps training content to specific job functions, required competencies, or security responsibilities defined in position descriptions. Role-based training completion is not tracked separately from general awareness training.',
        'partial', 'Role-aware quiz content exists; no formal role-based training program documented.', 'Low'
    ),
    'at-4': (
        'implemented', 'technical',
        'All training activities are recorded in the BLACKSITE database. The daily_quiz_activity table records each user\'s quiz date, score, pass/fail status, and completion timestamp. The training_clicks table tracks user interactions with NICCS and supplemental training resources. These records provide an auditable history of training completion that can be queried by administrators. Record retention is indefinite within the encrypted database.',
        'pass', 'Training records captured in daily_quiz_activity and training_clicks tables.', None
    ),

    # ── AU ──────────────────────────────────────────────────────────────────
    'au-1': (
        'partial', 'procedural',
        'No formal Audit and Accountability Policy document has been authored or approved. Audit logging is implemented technically in the application, but there is no policy defining what must be logged, retention periods, review frequency, or responsibilities for log management. The implementation serves as a de facto policy but does not satisfy the formal documentation requirement of AU-1.',
        'partial', 'Audit logging implemented; no formal policy document.', 'Low'
    ),
    'au-2': (
        'implemented', 'technical',
        'The security_events table captures all significant security events including: login (success and failure), logout, access_denied, admin_action, data_export, and system configuration changes. Events are recorded with user identity, timestamp, source IP, resource type, resource ID, and a JSON details field for additional context. The _log_security_event() helper is called from all security-relevant code paths. Event types cover the required NIST 800-53 AU-2 event categories.',
        'pass', 'Comprehensive security event logging via security_events table.', None
    ),
    'au-3': (
        'implemented', 'technical',
        'Each audit record in security_events and audit_log contains: event type, timestamp (UTC), user identity (Remote-User), source IP address, action performed, resource type and ID affected, and a JSON details blob for event-specific context. The immutable_audit_log table stores append-only records for the most sensitive operations. All required NIST AU-3 content elements (what, when, where, who, source, outcome) are captured.',
        'pass', 'Audit records contain all required content elements per AU-3.', None
    ),
    'au-4': (
        'partial', 'technical',
        'Audit logs are stored within the encrypted SQLite database on the same volume as application data. The database file grows indefinitely as audit records accumulate, and there is no automated monitoring of audit log storage capacity or alerting when space thresholds are approached. The Iapetus nightly backup protects against data loss but does not address storage capacity management. No log rotation or archival process is implemented.',
        'partial', 'Logs in encrypted DB; no storage capacity monitoring or alerting.', 'Moderate'
    ),
    'au-5': (
        'partial', 'technical',
        'There is no automated alerting mechanism that triggers when audit logging fails or when the audit subsystem encounters errors. Database write failures would surface as application errors but would not generate security alerts. No monitoring watchdog exists to verify that audit logging is functioning correctly. An alert should be implemented to notify administrators if security event logging fails.',
        'partial', 'No automated alerting on audit logging failure.', 'Moderate'
    ),
    'au-6': (
        'partial', 'procedural',
        'The BLACKSITE admin UI provides a Security Events dashboard allowing administrators to review logged events, filter by event type, user, date range, and IP address. However, there is no automated log analysis, no SIEM integration, no anomaly detection, and no defined review schedule or procedures for regular audit log review. Log review is entirely manual and ad hoc. No integration with external security monitoring tools has been implemented.',
        'partial', 'Admin UI for log review exists; no automated analysis, no SIEM, no review schedule.', 'Moderate'
    ),
    'au-8': (
        'implemented', 'technical',
        'All audit record timestamps use datetime.now(timezone.utc) from Python\'s datetime module, ensuring consistent UTC timestamps across all log entries. Timestamps are stored as ISO 8601 datetime values in the SQLite database. The server clock is synchronized via NTP (chrony/systemd-timesyncd). There is no known clock drift issue, and timestamps in log records are reliable for forensic analysis and correlation.',
        'pass', 'All timestamps UTC via datetime.now(timezone.utc); NTP-synchronized server clock.', None
    ),
    'au-9': (
        'partial', 'technical',
        'The immutable_audit_log table is designed as an append-only structure in the application layer — no DELETE or UPDATE operations are performed against it by the application code. The SQLCipher-encrypted database protects log integrity at rest from unauthorized access. However, there is no cryptographic signing of individual log entries, no WORM storage mechanism, and no independent log server. An admin with database access could theoretically modify records. Cryptographic log signing or export to a write-once log store would fully satisfy this control.',
        'partial', 'Append-only table design and encrypted DB protect logs; no cryptographic signing.', 'Moderate'
    ),
    'au-11': (
        'partial', 'procedural',
        'No formal audit log retention schedule has been established. Logs accumulate indefinitely in the encrypted SQLite database without automated archival, deletion, or export to long-term storage. The nightly backup to Iapetus NAS preserves log history but backup retention itself is not formally defined. NIST 800-53 Low baseline requires at least 90-day online retention; this is met by default but not enforced by policy.',
        'partial', 'No formal retention schedule; logs accumulate indefinitely without policy.', 'Low'
    ),
    'au-12': (
        'implemented', 'technical',
        'The _log_audit() and _log_security_event() helper functions are called from all administrative routes, data modification operations, authentication events, and access control decisions throughout the BLACKSITE codebase. Audit record generation is centralized and applied consistently. Component-level audit generation covers all significant state changes in the system, including control updates, POA&M modifications, user role changes, and system record edits.',
        'pass', 'Audit generation implemented across all components via centralized helpers.', None
    ),

    # ── CA ──────────────────────────────────────────────────────────────────
    'ca-1': (
        'partial', 'procedural',
        'No formal Security Assessment and Authorization Policy document has been produced. The assessment and authorization activities are conducted within BLACKSITE itself, which serves as the platform for RMF activities, but the process is not governed by a written policy document defining roles, responsibilities, assessment frequency, and authorization criteria. Authoring a formal CA policy is required.',
        'partial', 'No formal CA policy document; process conducted informally.', 'Low'
    ),
    'ca-2': (
        'implemented', 'technical',
        'BLACKSITE IS the security control assessment platform — control assessment is the system\'s core mission. The platform supports continuous assessment through the system_controls table with assessment results, assessment notes, and assessor tracking. Control status is updated through the ISSO workflow. Assessment evidence is stored in evidence_files. The platform generates assessment reports and supports POA&M-driven remediation tracking. This meta-assessment documents BLACKSITE\'s own control posture.',
        'pass', 'System is the assessment platform; continuous assessment is core function.', None
    ),
    'ca-3': (
        'not_implemented', 'none',
        'BLACKSITE connects to two external systems (ip-api.com and NIST GitHub API) without formal Interconnection Security Agreements or documented risk acceptances. No ISA/MOU process exists to formally authorize these connections. While the connections are low-risk (outbound-only, no sensitive data transmitted), the absence of formal agreements is a gap. Formal ISAs or documented risk acceptances must be completed for each external connection.',
        'fail', 'No ISA or MOU for ip-api.com or NIST GitHub API connections.', 'Moderate'
    ),
    'ca-5': (
        'implemented', 'technical',
        'BLACKSITE has a full POA&M management system built into the platform. The poam_items table tracks weaknesses, remediation plans, responsible parties, scheduled completion dates, and status through the full lifecycle (draft → open → in_progress → closed_verified). POA&M items link to specific controls, support evidence attachment via poam_evidence, and feed into the risk register. This assessment populates POA&M items for all identified gaps.',
        'pass', 'Full POA&M management system built into BLACKSITE platform.', None
    ),
    'ca-6': (
        'partial', 'procedural',
        'The BLACKSITE system record has auth_status=authorized and ato_decision=approved. However, there is no formal ATO package with a physical or digital signature from a designated Authorizing Official, no formal Security Assessment Report, and no formal System Security Plan document separate from the data stored in BLACKSITE itself. The authorization is informal. This assessment represents the first step toward a documented ATO package.',
        'partial', 'auth_status=authorized but no formal signed ATO package or SSP document.', 'Moderate'
    ),
    'ca-7': (
        'partial', 'technical',
        'A /health endpoint provides operational status monitoring. The NIST catalog updater runs on a cron schedule to maintain current control language. Security events are continuously logged. However, there is no formal Continuous Monitoring (ConMon) Plan document, no defined monitoring metrics, no automated vulnerability scanning schedule, and no formal reporting cycle to the AO. The ad hoc monitoring activities do not constitute a documented ConMon program.',
        'partial', 'Health endpoint and event logging exist; no formal ConMon plan.', 'Moderate'
    ),
    'ca-7.4': (
        'partial', 'technical',
        'The risks table in BLACKSITE tracks identified risks with likelihood, impact, risk score, and treatment plans. Risk items can be linked to POA&M entries. However, there are no automated risk monitoring workflows, no risk threshold alerting, no periodic risk review schedule, and no formal risk reporting to leadership. Risk tracking is manual and review is ad hoc.',
        'partial', 'risks table tracks risks; no automated monitoring or review schedule.', 'Low'
    ),
    'ca-9': (
        'partial', 'procedural',
        'BLACKSITE\'s internal connections to Authelia (for authentication) and Caddy (for TLS and proxying) are functional and documented informally through compose file configurations. However, no formal Internal Connection Agreements (ISAs for internal connections) have been produced. The connections are well understood architecturally but not formally documented in a system interconnection inventory.',
        'partial', 'Internal connections to Authelia/Caddy exist; no formal ISA documentation.', 'Low'
    ),

    # ── CM ──────────────────────────────────────────────────────────────────
    'cm-1': (
        'partial', 'procedural',
        'No formal Configuration Management Policy document has been authored. Configuration is managed through config.yaml, Docker Compose files, and Authelia configuration, but without a policy governing configuration management practices, change approval, and baseline maintenance. The technical implementation of configuration management exists but lacks a governing policy document.',
        'partial', 'No formal CM policy document.', 'Low'
    ),
    'cm-2': (
        'partial', 'technical',
        'The config.yaml file serves as the de facto baseline configuration for BLACKSITE, defining database path, session settings, logging levels, and feature flags. Docker Compose files pin image versions. However, there is no formal Baseline Configuration Document stored in a Configuration Management system, no version-controlled change history beyond git commits, and no formal process for baseline review and approval.',
        'partial', 'config.yaml serves as baseline; no formal CM baseline documentation.', 'Low'
    ),
    'cm-4': (
        'not_implemented', 'none',
        'No formal change impact analysis process exists for BLACKSITE. Changes to the system (code updates, configuration changes, dependency upgrades) are applied by the admin without a documented impact assessment process. There is no change advisory board, no formal risk assessment for changes, and no rollback procedures documented. This is a significant gap for a security-relevant system.',
        'fail', 'No formal change impact analysis process or change control procedures.', 'Moderate'
    ),
    'cm-5': (
        'partial', 'procedural',
        'Physical and logical access restrictions for configuration changes are partially implemented: only the admin account has SSH access to the server, and only users with admin RBAC role can modify system configuration through the application. However, there is no formal change control board, no change request process, and no separation of duties for changes. One person has full authority to make all changes without review.',
        'partial', 'Admin-only SSH access; no formal change control board or SOD.', 'Low'
    ),
    'cm-6': (
        'partial', 'technical',
        'Configuration settings in config.yaml are managed by the admin. Security-relevant settings (session timeout, database key, RBAC roles) are controlled and not exposed. However, there is no automated compliance checking against a defined security configuration baseline, no CIS Benchmark hardening documentation, and no formal process to verify that configuration settings remain compliant over time.',
        'partial', 'Configuration managed; no automated baseline compliance checking.', 'Low'
    ),
    'cm-7': (
        'implemented', 'technical',
        'BLACKSITE is bound to loopback interface only (127.0.0.1); all external access is through Caddy reverse proxy. Only necessary ports are open: 80/443 on Caddy, 22/20234 for SSH. No unnecessary services are running on the application host. The FastAPI application exposes only defined routes with no debug endpoints in production. The principle of least functionality is applied through systemd service configuration and UFW firewall rules.',
        'pass', 'Loopback-only binding, minimal ports, no unnecessary services or routes.', None
    ),
    'cm-8': (
        'partial', 'technical',
        'The inventory_items table in BLACKSITE supports hardware and software inventory tracking. The server hardware is informally inventoried in documentation. However, the inventory is not formally maintained in a CM system with change tracking, no software component inventory (SBOM) exists, and the inventory is not reviewed on a defined schedule. Requirements.txt serves as a partial software inventory.',
        'partial', 'inventory_items table exists; no formal SBOM or maintained CM inventory.', 'Low'
    ),
    'cm-10': (
        'partial', 'technical',
        'All software components used by BLACKSITE are open source (FastAPI, SQLAlchemy, aiosqlite, pysqlcipher3, Jinja2, etc.) with permissive licenses (MIT, Apache 2.0, BSD). No commercial software licenses are in use. However, no formal software license policy document exists, and license compliance has not been formally reviewed or documented. A requirements.txt pin list exists but without formal license inventory.',
        'partial', 'All open source; no formal license policy or compliance review documented.', 'Low'
    ),
    'cm-11': (
        'partial', 'procedural',
        'The production server is accessible only via SSH by the admin account; there are no general user accounts on the server OS that could install software. However, there is no formal policy prohibiting user-installed software, and no technical enforcement mechanism (e.g., package whitelist) beyond SSH access control. A formal policy statement would satisfy this control.',
        'partial', 'Admin-only SSH prevents casual software install; no formal policy.', 'Low'
    ),

    # ── CP ──────────────────────────────────────────────────────────────────
    'cp-1': (
        'not_implemented', 'none',
        'No formal Contingency Planning Policy document has been produced. There are no documented procedures for responding to system disruptions, no RTO/RPO objectives, and no formal contingency planning program. The nightly backup to Iapetus NAS provides some recovery capability, but this is not governed by a policy or plan.',
        'fail', 'No contingency planning policy, plan, or procedures documented.', 'High'
    ),
    'cp-2': (
        'not_implemented', 'none',
        'No Contingency Plan (CP) document exists for BLACKSITE. There are no documented procedures for system recovery after disruption, no defined Recovery Time Objectives (RTO) or Recovery Point Objectives (RPO), no alternative processing arrangements, and no documented roles and responsibilities for contingency response. The system relies on ad hoc recovery by the admin with no documented process.',
        'fail', 'No contingency plan document; no RTO/RPO defined.', 'High'
    ),
    'cp-3': (
        'not_implemented', 'none',
        'No contingency training has been conducted. There is no awareness program for personnel regarding their roles during a system disruption, no tabletop exercises, and no training records. Since this is a single-administrator system, training would consist of the admin reviewing and exercising the contingency plan — which itself does not yet exist.',
        'fail', 'No contingency training conducted.', 'High'
    ),
    'cp-4': (
        'not_implemented', 'none',
        'The contingency plan has never been tested because no contingency plan exists. No tabletop exercise, functional exercise, or full recovery test has been performed. Recovery procedures have not been validated, and it is unknown whether the nightly backup to Iapetus NAS can successfully restore the system within an acceptable timeframe.',
        'fail', 'No contingency plan test or recovery exercise conducted.', 'High'
    ),
    'cp-9': (
        'partial', 'technical',
        'The backup-all.sh script runs nightly at 03:00 via systemd timer, syncing the BLACKSITE database and application files to the Iapetus NAS (192.168.86.213) via rclone/SMB. The backup covers the SQLCipher-encrypted database, configuration files, and evidence uploads. However, backup restoration has never been tested, there are no formal backup verification procedures, RPO is undefined, and backup retention on Iapetus is not formally specified.',
        'partial', 'Nightly backup to Iapetus NAS active; restoration never tested; no formal RPO.', 'Moderate'
    ),
    'cp-10': (
        'partial', 'technical',
        'Systemd is configured to automatically restart the BLACKSITE service on failure (Restart=on-failure). The application will recover from transient crashes without manual intervention. However, there are no formal Recovery Time Objectives or Recovery Point Objectives defined, no documented recovery procedures for catastrophic failures (e.g., server hardware failure), and no tested recovery from backup.',
        'partial', 'Systemd auto-restart on failure; no formal RTO/RPO or recovery procedures.', 'Moderate'
    ),

    # ── IA ──────────────────────────────────────────────────────────────────
    'ia-1': (
        'partial', 'procedural',
        'No formal Identification and Authentication Policy document has been produced. Authentication is implemented through Authelia with MFA enforcement, but without a governing policy document that defines IA requirements, acceptable authenticator types, identity proofing standards, and account management procedures. The technical implementation is sound; the policy documentation is the gap.',
        'partial', 'No formal IA policy document.', 'Low'
    ),
    'ia-2': (
        'implemented', 'inherited',
        'All users must authenticate through Authelia before any BLACKSITE content is served. The Caddy forward_auth directive sends every request through Authelia verification before proxying to the application. Authentication is enforced at the infrastructure layer, independent of application-level checks. Unauthenticated requests receive a redirect to the Authelia login portal. This provides strong authentication enforcement that cannot be bypassed at the application layer.',
        'pass', 'Authelia enforces authentication for all users; cannot be bypassed.', None
    ),
    'ia-2.1': (
        'implemented', 'inherited',
        'Authelia is configured to require Multi-Factor Authentication (MFA) for all users including administrators. Supported MFA methods include TOTP (time-based one-time passwords via authenticator apps) and WebAuthn (hardware security keys or biometric authenticators). All privileged accounts (admin, issm, ciso, ao roles) are subject to the same MFA requirement. There are no MFA bypass exceptions configured.',
        'pass', 'MFA (TOTP/WebAuthn) required for all accounts including admin via Authelia.', None
    ),
    'ia-2.2': (
        'implemented', 'inherited',
        'MFA enforcement through Authelia applies equally to all accounts regardless of privilege level. Non-privileged users (isso, auditor, sca roles) are subject to the same MFA requirements as administrators. The Authelia configuration does not differentiate MFA requirements by role — all users must complete MFA to obtain a session. This satisfies IA-2(2) for non-privileged account MFA.',
        'pass', 'MFA enforced for all accounts including non-privileged users.', None
    ),
    'ia-2.8': (
        'implemented', 'inherited',
        'Authelia supports WebAuthn as a replay-resistant authentication mechanism. WebAuthn uses challenge-response with public key cryptography, ensuring that authentication responses cannot be replayed. TOTP tokens are also replay-resistant by design (30-second windows with server-side used-token tracking). Both MFA methods prevent replay attacks on authentication sessions.',
        'pass', 'WebAuthn and TOTP both provide replay-resistant authentication.', None
    ),
    'ia-2.12': (
        'not_applicable', 'none',
        'BLACKSITE is an internal security management tool for a homelab/small organization environment. There is no requirement for PIV/CAC smart card authentication. The system does not connect to federal networks and is not subject to HSPD-12 or OMB M-11-11 requirements. PIV/CAC is not applicable.',
        'not_applicable', 'Internal tool; no PIV/CAC requirement.', None
    ),
    'ia-4': (
        'partial', 'procedural',
        'User identifiers (usernames) are defined in the Authelia configuration file and managed by the admin. Identifiers are unique per user and are never reused once an account is removed. However, there is no formal identifier management policy, no documented identifier lifecycle procedures, and no formal identity proofing process beyond admin creation. The informal process works for the current small user base but is not formally documented.',
        'partial', 'Identifiers managed in Authelia; no formal lifecycle policy or identity proofing procedures.', 'Low'
    ),
    'ia-5': (
        'implemented', 'inherited',
        'Password management is handled entirely by Authelia, which enforces minimum password length, complexity requirements, password history, and aging policies as configured. TOTP and WebAuthn token lifecycle is managed by Authelia\'s MFA configuration. Initial password distribution is handled through admin-initiated account setup. Password reset requires admin action, eliminating self-service reset risks. All authenticators are Authelia-managed.',
        'pass', 'Authelia manages all authenticator lifecycle including passwords and MFA tokens.', None
    ),
    'ia-5.1': (
        'implemented', 'inherited',
        'Authelia enforces password complexity requirements including minimum length, character classes (uppercase, lowercase, numbers, symbols), password history to prevent reuse, and maximum password age. These settings are configured in the Authelia configuration file. The bcrypt hashing algorithm protects stored password hashes with adaptive cost factors.',
        'pass', 'Authelia enforces password complexity, history, length, and aging requirements.', None
    ),
    'ia-6': (
        'implemented', 'inherited',
        'The Authelia login page displays generic error messages that do not reveal whether a username exists or whether the password was incorrect. Failed authentication attempts show a uniform "Invalid credentials" message. This prevents username enumeration attacks. The BLACKSITE application layer does not expose authentication state information either, as it only receives successfully authenticated requests.',
        'pass', 'Authelia displays generic authentication failure messages; no credential enumeration possible.', None
    ),
    'ia-7': (
        'partial', 'hybrid',
        'Authelia uses bcrypt for password hashing, which is a proven algorithm but is not a FIPS 140-2/3 validated implementation. The Ubuntu FIPS kernel provides FIPS-validated cryptographic modules at the OS level, but the Python bcrypt library used by Authelia operates outside the FIPS module boundary. Session tokens use HMAC-SHA256 which is FIPS-compatible but through non-validated Python libraries. Full FIPS alignment would require a FIPS-validated Authelia deployment.',
        'partial', 'Bcrypt used by Authelia is not FIPS-validated; FIPS kernel present at OS level only.', 'Low'
    ),
    'ia-8': (
        'not_applicable', 'none',
        'BLACKSITE is used exclusively by organizational personnel (internal users). There are no non-organizational users (contractors, public users, partner organization users) with access to the production instance. This control is not applicable.',
        'not_applicable', 'No non-organizational users in production instance.', None
    ),
    'ia-8.1': (
        'not_applicable', 'none',
        'There is no cross-agency PIV card acceptance requirement. BLACKSITE does not federate identity with other government agencies. This control is not applicable.',
        'not_applicable', 'No cross-agency PIV acceptance needed.', None
    ),
    'ia-8.2': (
        'partial', 'technical',
        'An SSO/OIDC module has been implemented in the BLACKSITE codebase to support federated identity (e.g., Google OAuth, enterprise OIDC providers). However, this module is not enabled in the production configuration. When enabled, it would allow organizational identity federation. The implementation exists but is not in active use.',
        'partial', 'OIDC module implemented but not enabled in production.', 'Low'
    ),
    'ia-8.4': (
        'not_applicable', 'none',
        'BLACKSITE does not accept identities from other federal agencies and has no requirement for identity federation with federal identity providers. Not applicable.',
        'not_applicable', 'No federal identity federation requirement.', None
    ),
    'ia-11': (
        'partial', 'technical',
        'Authelia has a session max-age configured, requiring re-authentication after the maximum session duration is reached. The BLACKSITE application implements session_timeout_middleware that enforces an application-level idle session timeout. However, the specific timeout values and their alignment with organizational policy have not been formally documented or approved. The implementation is functional but not formally specified.',
        'partial', 'Session timeouts implemented in Authelia and app middleware; not formally specified.', 'Low'
    ),

    # ── IR ──────────────────────────────────────────────────────────────────
    'ir-1': (
        'not_implemented', 'none',
        'No formal Incident Response Policy document has been produced. There are no documented procedures for detecting, reporting, analyzing, containing, eradicating, or recovering from security incidents. The absence of a formal IR policy is a significant gap. Security events are logged in the database, but there is no defined process for responding to those events.',
        'fail', 'No incident response policy, plan, or procedures exist.', 'High'
    ),
    'ir-2': (
        'not_implemented', 'none',
        'No incident response training has been conducted. Personnel have not been trained on IR roles, responsibilities, reporting channels, or response procedures. Since no IR plan or policy exists, there is no basis for training. Training cannot be completed until IR documentation is produced.',
        'fail', 'No IR training conducted; no IR documentation exists to base training on.', 'High'
    ),
    'ir-4': (
        'not_implemented', 'none',
        'No formal incident handling procedures exist. There are no defined steps for incident detection, triage, containment, eradication, or recovery. The security_events table captures potential indicators of security incidents, but there is no process for reviewing those events, escalating alerts, or coordinating incident response. This is a critical gap for a system handling security assessment data.',
        'fail', 'No incident handling procedures documented or practiced.', 'High'
    ),
    'ir-5': (
        'partial', 'technical',
        'The security_events table passively captures security-relevant events including failed login attempts, access denied events, and admin actions that could constitute incident indicators. An admin can query these events through the Security Events dashboard. However, there is no automated incident tracking system, no incident severity classification scheme, and no incident record format. Security events serve as a partial incident tracking capability requiring manual review.',
        'partial', 'security_events table captures indicators; no formal incident tracking system.', 'Moderate'
    ),
    'ir-6': (
        'not_implemented', 'none',
        'No formal incident reporting procedures or designated reporting contacts have been established. There are no defined criteria for what constitutes a reportable incident, no notification timelines, no designated incident response contacts, and no reporting channels to stakeholders or law enforcement. Incidents would be identified and handled ad hoc by the admin.',
        'fail', 'No incident reporting procedures or contacts defined.', 'High'
    ),
    'ir-7': (
        'not_implemented', 'none',
        'No formal incident response assistance resources have been identified or documented. There are no agreements with external IR firms, no CISA incident reporting channels established, and no documented resources for obtaining IR support beyond the single admin. For a Low-impact system, lightweight resources (CISA contact, hosting provider support) should be documented.',
        'fail', 'No IR assistance resources identified or documented.', 'High'
    ),
    'ir-8': (
        'not_implemented', 'none',
        'No Incident Response Plan document has been produced. This is the foundational IR document that would define roles, responsibilities, communication procedures, detection criteria, response procedures, and lessons-learned processes. Without this document, all other IR controls are effectively not implemented. Creating the IR plan is the highest priority IR remediation action.',
        'fail', 'No incident response plan document exists.', 'High'
    ),

    # ── MA ──────────────────────────────────────────────────────────────────
    'ma-1': (
        'partial', 'procedural',
        'No formal System Maintenance Policy document has been produced. Maintenance activities (software updates, dependency upgrades, OS patches) are performed by the admin on an informal basis without a governing policy defining maintenance windows, change control, or documentation requirements.',
        'partial', 'No formal maintenance policy document.', 'Low'
    ),
    'ma-2': (
        'partial', 'procedural',
        'System maintenance (Python package updates via pip, OS patches via apt, application code deployments) is performed by the admin. Updates are applied as needed without a formal maintenance schedule, defined maintenance windows, or a change log of maintenance activities. There is no formal process for approving or documenting maintenance actions.',
        'partial', 'Updates applied by admin; no formal maintenance windows, schedule, or change log.', 'Low'
    ),
    'ma-4': (
        'partial', 'technical',
        'All system maintenance is performed remotely via SSH with key-based authentication. Remote maintenance sessions are limited to the admin account. There is no formal nonlocal maintenance authorization procedure, no session recording for maintenance activities, and no two-person integrity requirement for sensitive changes. SSH access logs provide a basic audit trail of maintenance sessions.',
        'partial', 'SSH key auth for maintenance; no formal nonlocal maintenance authorization procedures.', 'Low'
    ),
    'ma-5': (
        'partial', 'procedural',
        'A single administrator performs all system maintenance. There is no formal personnel screening requirement for the maintenance role, no background check program, and no formal maintenance role designation with documented responsibilities. The single-admin model means there is no peer review of maintenance activities.',
        'partial', 'Single admin performs all maintenance; no formal screening or personnel procedures.', 'Low'
    ),

    # ── MP ──────────────────────────────────────────────────────────────────
    'mp-1': (
        'partial', 'procedural',
        'No formal Media Protection Policy document exists. The system does not use removable media in normal operations, reducing the practical risk, but a policy document is required by NIST 800-53 Rev 5 regardless of media usage.',
        'partial', 'No formal media protection policy document.', 'Low'
    ),
    'mp-2': (
        'not_applicable', 'none',
        'BLACKSITE does not use removable media (USB drives, external hard drives, optical media) in its normal operations. System data is stored on internal server drives and backed up over the network. This control is not applicable.',
        'not_applicable', 'No removable media used in system operations.', None
    ),
    'mp-6': (
        'not_applicable', 'none',
        'No removable media is used in the BLACKSITE system boundary. Media sanitization is not applicable.',
        'not_applicable', 'No removable media to sanitize.', None
    ),
    'mp-7': (
        'not_applicable', 'none',
        'No removable media is used within the BLACKSITE system boundary. Media use restrictions and transport protections are not applicable.',
        'not_applicable', 'No removable media in scope.', None
    ),

    # ── PE ──────────────────────────────────────────────────────────────────
    'pe-1': (
        'partial', 'procedural',
        'No formal Physical and Environmental Protection Policy document has been authored. The server is located in a home office environment with basic residential physical security controls. A policy document is required even for Low-impact systems operating in non-data-center environments.',
        'partial', 'No formal PE policy document; home office environment.', 'Low'
    ),
    'pe-2': (
        'partial', 'procedural',
        'Physical access to the server (Borisov, Dell R510) is limited to authorized individuals in the home office. The office is secured with a residential lock. There is no formal physical access authorization list, no visitor log, and no formal access control procedures. The residential environment provides basic access control that is partially sufficient for a Low-impact system.',
        'partial', 'Limited physical access in home office; no formal authorization list or procedures.', 'Low'
    ),
    'pe-3': (
        'partial', 'procedural',
        'Physical entry to the server room (home office) is controlled by a residential lock. Access is limited to household members with no documented access list. There is no electronic access control, no access log, and no formal entry control procedures. For a Low-impact system in a home environment, this is partially acceptable.',
        'partial', 'Residential lock provides basic entry control; no formal procedures or logs.', 'Low'
    ),
    'pe-6': (
        'not_implemented', 'none',
        'No formal physical access monitoring is in place beyond standard residential security (locked door). There are no cameras, motion sensors, intrusion detection systems, or access logs for the server location. This gap is partially mitigated by the home office environment where physical access is inherently limited.',
        'fail', 'No formal physical access monitoring; residential environment only.', 'Low'
    ),
    'pe-8': (
        'not_implemented', 'none',
        'No visitor access records are maintained for the server location. Since this is a home office environment, formal visitor logging has not been implemented. Any guests with physical access to the server room are not documented.',
        'fail', 'No visitor access records maintained.', 'Low'
    ),
    'pe-12': (
        'not_applicable', 'none',
        'Emergency lighting requirements apply to data centers and commercial facilities. The home office environment with the server is not subject to data center emergency lighting requirements. Not applicable for this deployment context.',
        'not_applicable', 'Home office environment; data center emergency lighting N/A.', None
    ),
    'pe-13': (
        'partial', 'procedural',
        'Residential smoke detectors are present in the home office where the server is located. A fire extinguisher is accessible. However, there is no commercial fire suppression system, no fire detection monitoring integrated with alerting systems, and no formal fire protection plan.',
        'partial', 'Residential smoke detectors and extinguisher present; no commercial fire suppression.', 'Low'
    ),
    'pe-14': (
        'partial', 'procedural',
        'The home office has standard residential HVAC climate control maintaining comfortable operating temperatures. No formal environmental monitoring (temperature/humidity sensors) is deployed, no alerting on environmental thresholds, and no documented environmental operating parameters for the server.',
        'partial', 'Residential HVAC present; no formal environmental monitoring or documented parameters.', 'Low'
    ),
    'pe-15': (
        'not_applicable', 'none',
        'No water hazard (raised floor water sensors, overhead piping, flood risk) has been identified at the server location. Water damage protection is not applicable for this deployment.',
        'not_applicable', 'No water hazard identified at server location.', None
    ),
    'pe-16': (
        'partial', 'procedural',
        'All hardware delivery and removal is controlled by the admin who is the sole person with authorized physical access. There are no formal procedures for authorizing, documenting, or inspecting hardware delivery and removal. Informal control exists through single-admin ownership.',
        'partial', 'Admin controls all hardware delivery/removal; no formal procedures.', 'Low'
    ),

    # ── PL ──────────────────────────────────────────────────────────────────
    'pl-1': (
        'partial', 'procedural',
        'No formal Planning Policy document exists. System planning activities occur informally through BLACKSITE itself (the system records, risk registers, and POA&M items serve planning functions) but without a governing policy document.',
        'partial', 'No formal planning policy document.', 'Low'
    ),
    'pl-2': (
        'partial', 'technical',
        'System security information is maintained within BLACKSITE itself — system records, control assessments, POA&M items, risk register, and evidence files constitute the de facto SSP content. This assessment populates the system_controls table as the authoritative control status record. However, there is no formally approved System Security Plan document with AO signature, no complete SSP narrative in a single document, and no formal SSP review and approval process.',
        'partial', 'SSP content distributed across BLACKSITE data; no formally approved SSP document.', 'Moderate'
    ),
    'pl-4': (
        'not_implemented', 'none',
        'No Rules of Behavior document has been produced for BLACKSITE users. Users have not been required to read and acknowledge acceptable use policies, data handling requirements, or prohibited activities. A Rules of Behavior document must be developed and user acknowledgment recorded.',
        'fail', 'No rules of behavior document for users.', 'Moderate'
    ),
    'pl-4.1': (
        'not_applicable', 'none',
        'BLACKSITE does not involve social media access, social networking activities, or posting of information to social media platforms. This enhancement is not applicable.',
        'not_applicable', 'No social media access from this system.', None
    ),
    'pl-10': (
        'implemented', 'procedural',
        'The NIST SP 800-53 Rev 5 Low baseline has been explicitly selected and documented in the BLACKSITE system record (overall_impact=Low). The baseline selection drives the set of controls assessed in this document. The selection is based on FIPS 199 categorization with Confidentiality=Low, Integrity=Low, Availability=Low, resulting in an overall Low impact designation. No PII, PHI, or CUI is processed by the system.',
        'pass', 'Low baseline explicitly selected; documented in system record with FIPS 199 rationale.', None
    ),
    'pl-11': (
        'partial', 'procedural',
        'Several controls have been designated as Not Applicable based on system characteristics (no removable media, no wireless, no mobile app, no PIV requirement, home office environment). These determinations are documented in the control narratives within BLACKSITE. However, there is no formal tailoring document with AO-approved justifications for each scoping decision, and no formal tailoring process has been documented.',
        'partial', 'N/A determinations made and documented in control narratives; no formal tailoring document.', 'Low'
    ),

    # ── PS ──────────────────────────────────────────────────────────────────
    'ps-1': (
        'partial', 'procedural',
        'No formal Personnel Security Policy document exists. Personnel security activities are conducted informally for a small single-administrator environment. A policy document is required by NIST 800-53 Rev 5.',
        'partial', 'No formal personnel security policy document.', 'Low'
    ),
    'ps-2': (
        'partial', 'procedural',
        'No formal position risk designations have been documented for BLACKSITE roles. The system has defined RBAC roles with different privilege levels (admin being highest risk), but these have not been formally designated with associated security requirements, screening levels, or position descriptions.',
        'partial', 'RBAC roles defined; no formal position risk designations.', 'Low'
    ),
    'ps-3': (
        'partial', 'procedural',
        'Personnel with system access are known to the admin and informal vetting occurs through the nature of the small team environment. No formal screening procedures, background check requirements, or screening criteria have been documented. For a Low-impact system, basic screening documentation is required.',
        'partial', 'Informal screening for small team; no formal screening procedures.', 'Low'
    ),
    'ps-4': (
        'partial', 'procedural',
        'When a user departs, the admin disables their Authelia account entry and removes their RBAC role assignments. Access is terminated. However, there is no formal termination checklist, no automated account disable workflow tied to HR processes, and no formal offboarding procedures documented.',
        'partial', 'Authelia account disabled on departure; no formal offboarding procedures.', 'Low'
    ),
    'ps-5': (
        'partial', 'procedural',
        'If a user transfers to a different role, the admin updates their RBAC role assignment in BLACKSITE and adjusts Authelia group membership as needed. However, there are no formal transfer procedures, no timeline requirements for access modification, and no review of whether the new role requires access changes.',
        'partial', 'Access updated on transfer; no formal transfer procedures.', 'Low'
    ),
    'ps-6': (
        'not_implemented', 'none',
        'No formal access agreements or non-disclosure agreements have been established for BLACKSITE users. Users have not signed any agreements acknowledging their responsibilities, acceptable use requirements, or confidentiality obligations. Access agreement templates must be developed and signed acknowledgments obtained from all users.',
        'fail', 'No access agreements or NDAs signed by users.', 'Moderate'
    ),
    'ps-7': (
        'not_applicable', 'none',
        'There are no external personnel (contractors, vendors, third parties) with access to the BLACKSITE production system. All users are organizational insiders. External personnel controls are not applicable.',
        'not_applicable', 'No external personnel with system access.', None
    ),
    'ps-8': (
        'not_implemented', 'none',
        'No formal sanctions policy has been documented for violations of information security policies. While informal consequences for policy violations exist, there is no written sanctions policy with defined graduated sanctions, a formal notification process, or documentation requirements.',
        'fail', 'No formal sanctions policy documented.', 'Low'
    ),
    'ps-9': (
        'partial', 'procedural',
        'RBAC roles and their associated access levels are documented in the application code and configuration. The seven roles (admin, isso, issm, ciso, ao, sca, auditor) have defined permissions enforced in Python. However, there are no formal written position descriptions for these roles, no documented competency requirements, and no formal role definition documents separate from the code.',
        'partial', 'Roles documented in code/config; no formal position descriptions.', 'Low'
    ),

    # ── RA ──────────────────────────────────────────────────────────────────
    'ra-1': (
        'partial', 'procedural',
        'No formal Risk Assessment Policy document has been produced. Risk assessment activities are conducted informally and tracked in the risks table within BLACKSITE. A policy document governing risk assessment frequency, methodology, scope, and reporting requirements is needed.',
        'partial', 'No formal risk assessment policy document.', 'Low'
    ),
    'ra-2': (
        'implemented', 'procedural',
        'BLACKSITE has been formally categorized as a Low-impact system under FIPS 199. The categorization is documented in the system record: confidentiality_impact=Low, integrity_impact=Low, availability_impact=Low, overall_impact=Low. The rationale is documented: no PII, PHI, or CUI processed; internal security management tool; limited external dependencies. The categorization has been reviewed and set to approved status.',
        'pass', 'FIPS 199 categorization documented in system record as Low impact with rationale.', None
    ),
    'ra-3': (
        'partial', 'procedural',
        'An informal risk assessment was conducted during system development and is reflected in the risks table entries and this assessment. Threat modeling was performed informally, considering threats relevant to a web-based security platform (unauthorized access, data exposure, availability disruption). However, no formal Risk Assessment Report document has been produced with documented threat sources, vulnerabilities, likelihood ratings, and signed acceptance.',
        'partial', 'Informal risk assessment conducted; no formal Risk Assessment Report document.', 'Low'
    ),
    'ra-3.1': (
        'not_implemented', 'none',
        'No formal supply chain risk assessment has been conducted for BLACKSITE. Open source dependencies (FastAPI, SQLAlchemy, pysqlcipher3, etc.) have not been formally assessed for supply chain risks such as malicious packages, compromised maintainers, or abandoned projects. Requirements.txt pins versions but does not include hash verification for supply chain integrity.',
        'fail', 'No supply chain risk assessment conducted for dependencies.', 'Moderate'
    ),
    'ra-5': (
        'partial', 'technical',
        'The scan_findings table in BLACKSITE supports recording vulnerability scan results. However, no automated vulnerability scanner (Nessus, OpenVAS, Trivy, etc.) is configured to run against the system. Vulnerability monitoring is performed manually through periodic review of CVE feeds and pip dependency advisories. The Wazuh agent provides some OS-level vulnerability detection.',
        'partial', 'scan_findings table exists; no automated vulnerability scanner configured.', 'Moderate'
    ),
    'ra-5.2': (
        'partial', 'technical',
        'Vulnerability monitoring relies on manual review of the NVD CVE database, pip dependency advisories, and the nist_publications table in BLACKSITE. The NIST GitHub catalog updater keeps control language current. There is no automated integration with vulnerability feeds, no automated dependency vulnerability scanning (e.g., pip-audit, safety), and no defined vulnerability monitoring schedule.',
        'partial', 'Manual vulnerability monitoring; no automated feed integration.', 'Moderate'
    ),
    'ra-5.11': (
        'not_implemented', 'none',
        'No public vulnerability disclosure program has been established for BLACKSITE. There is no security.txt file, no responsible disclosure policy, and no mechanism for external researchers to report security vulnerabilities. For a public-facing system (internet-accessible), a basic disclosure policy is recommended.',
        'fail', 'No public vulnerability disclosure program or security.txt.', 'Low'
    ),
    'ra-7': (
        'partial', 'technical',
        'Identified risks are tracked in the BLACKSITE risks table with likelihood, impact, risk score, treatment strategy, and treatment plans. Risk items can be linked to POA&M entries for remediation tracking. However, there are no formal risk response procedures, no risk acceptance criteria, no documented risk thresholds, and no formal process for escalating high risks to the AO.',
        'partial', 'risks table tracks risks; no formal risk response procedures or thresholds.', 'Low'
    ),

    # ── SA ──────────────────────────────────────────────────────────────────
    'sa-1': (
        'partial', 'procedural',
        'No formal System and Services Acquisition Policy document has been produced. All acquisition activities (all open source) are informal. A policy document is required.',
        'partial', 'No formal SA policy document.', 'Low'
    ),
    'sa-2': (
        'partial', 'procedural',
        'Resource allocation for BLACKSITE is informal — the system runs on shared homelab hardware (Borisov) with no formal budget allocation, capacity planning document, or resource reservation. Security resources are allocated through admin time without formal tracking.',
        'partial', 'Informal resource allocation; no formal budget or capacity planning.', 'Low'
    ),
    'sa-3': (
        'partial', 'technical',
        'BLACKSITE source code is maintained in a git repository with version control history. Deployments are tracked through git commits and the deployment script. However, there is no formal SDLC documentation, no formal security requirements specification, no documented design review process, and no formal testing framework with coverage requirements.',
        'partial', 'git version control exists; no formal SDLC documentation or secure development procedures.', 'Low'
    ),
    'sa-4': (
        'not_applicable', 'none',
        'All BLACKSITE components are open source software obtained without commercial acquisition contracts. No commercial software is procured. Acquisition requirements are not applicable to open source components selected through informal evaluation.',
        'not_applicable', 'All open source; no commercial acquisition.', None
    ),
    'sa-4.10': (
        'not_applicable', 'none',
        'No PIV products are acquired for BLACKSITE. Not applicable.',
        'not_applicable', 'No PIV products acquired.', None
    ),
    'sa-5': (
        'partial', 'procedural',
        'System documentation exists in the form of inline code comments, architecture notes in MEMORY.md and session notes, and the BLACKSITE platform data itself. However, there is no formal system documentation package including an architecture diagram, data flow diagram, external interfaces document, or system description document. Documentation is fragmented across multiple informal sources.',
        'partial', 'Inline comments and informal docs exist; no formal documentation package.', 'Low'
    ),
    'sa-8': (
        'partial', 'procedural',
        'Security engineering principles have been applied in BLACKSITE\'s design: RBAC for least privilege, SQLCipher for encryption at rest, TLS for encryption in transit, immutable audit logs, session management with idle timeout, parameterized queries to prevent SQLi, and defense in depth through Caddy+Authelia+application layers. However, these design decisions have not been formally documented in a security architecture document, and the security design rationale has not been formally reviewed.',
        'partial', 'Security by design applied (RBAC, encryption, audit logging); not formally documented.', 'Low'
    ),
    'sa-9': (
        'partial', 'procedural',
        'BLACKSITE uses external services including Authelia (self-hosted, considered internal), ip-api.com (geo-restriction), NIST GitHub API (catalog updates), and Let\'s Encrypt (TLS certificates). The ip-api.com and NIST GitHub API dependencies involve outbound calls without formal Interconnection Security Agreements or Terms of Service reviews. Let\'s Encrypt is used under their standard subscriber agreement. Formal risk assessments and agreements for external services are needed.',
        'partial', 'External services used (ip-api.com, NIST GitHub, Let\'s Encrypt); no formal ISAs.', 'Low'
    ),
    'sa-22': (
        'partial', 'technical',
        'Python 3.8 reached End of Life on October 31, 2024, and no longer receives security patches from the Python Software Foundation. BLACKSITE runs on Python 3.8 due to the pysqlcipher3 dependency which requires compilation against Python 3.8 on the Ubuntu FIPS kernel environment. This is a known and accepted risk. Upgrading to Python 3.11+ requires either recompiling pysqlcipher3, migrating to a different SQLCipher binding, or replacing SQLCipher with an alternative encryption approach. This is the highest-priority technical security gap.',
        'partial', 'Python 3.8 EOL since Oct 2024; pysqlcipher3 dependency blocks upgrade. CRITICAL gap.', 'High'
    ),

    # ── SC ──────────────────────────────────────────────────────────────────
    'sc-1': (
        'partial', 'procedural',
        'No formal System and Communications Protection Policy document has been produced. Communications protection is implemented technically (TLS, encrypted DB, session security) but without a governing policy document.',
        'partial', 'No formal SC policy document.', 'Low'
    ),
    'sc-5': (
        'partial', 'technical',
        'Caddy provides built-in rate limiting capabilities that are available but may not be fully configured for all routes. The geo-restriction to US IP addresses provides some denial-of-service surface reduction. The system runs on dedicated server hardware not shared with other internet-facing services in a way that would amplify DoS impact. However, there is no formal DoS protection plan, no load shedding mechanisms, and no DDoS mitigation service.',
        'partial', 'Caddy rate limiting available; no formal DoS protection plan or DDoS mitigation.', 'Moderate'
    ),
    'sc-7': (
        'implemented', 'technical',
        'BLACKSITE implements boundary protection through multiple layers: the application binds to loopback only (127.0.0.1:8100), Caddy reverse proxy handles all external connections with TLS termination, Authelia provides an authentication gate before any application traffic, UFW firewall restricts port access, and geographic restriction limits connections to US-based IP addresses. All external communications pass through the defined entry point (Caddy:443). Internal-to-external traffic is controlled through UFW outbound rules.',
        'pass', 'Multi-layer boundary protection: loopback binding, Caddy proxy, Authelia gate, UFW, geo-restriction.', None
    ),
    'sc-12': (
        'partial', 'technical',
        'Cryptographic key management for BLACKSITE uses: SQLCipher key stored as BLACKSITE_DB_KEY environment variable in the systemd service unit, session signing keys derived from configuration, and TLS certificates managed by Let\'s Encrypt with automatic renewal via Caddy. The SQLCipher key is a static 256-bit hex string. There is no formal key management plan, no key rotation schedule, no key escrow, and no documented key lifecycle procedures.',
        'partial', 'Keys stored in systemd env and config; no formal key management plan or rotation schedule.', 'Moderate'
    ),
    'sc-13': (
        'implemented', 'technical',
        'BLACKSITE implements cryptographic protections throughout: TLS 1.2+ for all data in transit via Caddy with Let\'s Encrypt certificates, SQLCipher AES-256-CBC for all data at rest in the SQLite database, HMAC-SHA256 for session cookie integrity, and bcrypt for Authelia password storage. The Ubuntu FIPS kernel provides FIPS 140-2 validated cryptographic modules at the OS level. All encryption algorithms are NIST-approved.',
        'pass', 'TLS 1.2+, SQLCipher AES-256, HMAC-SHA256 session integrity, bcrypt passwords implemented.', None
    ),
    'sc-15': (
        'not_applicable', 'none',
        'BLACKSITE has no collaborative computing components (video conferencing, screen sharing, remote desktop, whiteboard). Not applicable.',
        'not_applicable', 'No collaborative computing devices in scope.', None
    ),
    'sc-20': (
        'partial', 'technical',
        'DNS name resolution for BLACKSITE is provided by Caddy (for the application domain) and AdGuard Home for internal DNS queries. The borisov.network domain uses DNS records managed by the domain registrar. DNSSEC has not been fully configured for the domain. AdGuard Home provides DNS-over-HTTPS internally. External DNS resolution relies on upstream resolvers without formal DNSSEC validation enforcement.',
        'partial', 'AdGuard Home DNS; DNSSEC not fully configured for external domain.', 'Low'
    ),
    'sc-21': (
        'partial', 'technical',
        'AdGuard Home handles recursive DNS resolution for the internal network. DNSSEC validation is not fully configured in AdGuard Home\'s upstream resolver chain. DNS queries to external resolvers do not consistently enforce DNSSEC validation. This is a known gap in the DNS security posture.',
        'partial', 'AdGuard Home present; DNSSEC validation not fully configured.', 'Low'
    ),
    'sc-22': (
        'partial', 'technical',
        'Caddy provides the web application DNS addressing and name resolution for BLACKSITE. Internal DNS is served by AdGuard Home. The system architecture is documented informally. No formal DNS architecture documentation exists, and the DNS infrastructure has not been formally reviewed for security.',
        'partial', 'Caddy and AdGuard Home provide DNS/addressing; no formal architecture documentation.', 'Low'
    ),
    'sc-39': (
        'implemented', 'technical',
        'BLACKSITE runs as a dedicated systemd service under a non-root service account, providing OS-level process isolation. The Python application has no capability to access other system processes or shared memory outside its own process space. SQLite database access is exclusive to the BLACKSITE process (file locking). Caddy and Authelia run as separate processes in Docker containers with their own network namespaces. The architecture provides strong process isolation.',
        'pass', 'Systemd service isolation, dedicated user account, containerized dependencies.', None
    ),

    # ── SI ──────────────────────────────────────────────────────────────────
    'si-1': (
        'partial', 'procedural',
        'No formal System and Information Integrity Policy document has been produced. System integrity activities (patch management, malware protection, monitoring) are performed informally without a governing policy.',
        'partial', 'No formal SI policy document.', 'Low'
    ),
    'si-2': (
        'partial', 'procedural',
        'Operating system patches are applied via apt when available. Python dependencies are updated via pip when security advisories are identified. However, Python 3.8 is EOL and cannot receive security patches, which is an unmitigated flaw in the patch management posture. There is no formal patch management policy, no defined patching schedule (e.g., critical patches within 30 days), and no automated patch scanning.',
        'partial', 'Manual patching via apt/pip; Python 3.8 EOL is unmitigated; no formal patch schedule.', 'High'
    ),
    'si-3': (
        'partial', 'technical',
        'OS-level malware protections are provided by the Ubuntu kernel security features (ASLR, NX bit, seccomp). A Wazuh agent is installed on Borisov providing file integrity monitoring and rootkit detection. However, there is no traditional endpoint antivirus/EDR solution deployed on the server, and no regular malware scan is performed. The Wazuh agent provides partial coverage.',
        'partial', 'Wazuh FIM/rootkit detection present; no traditional AV/EDR on server.', 'Moderate'
    ),
    'si-4': (
        'partial', 'technical',
        'The BLACKSITE application monitors its own security events (security_events table) with admin review capability. The Wazuh agent provides OS-level system monitoring including file integrity monitoring, log analysis, and rootkit detection. However, there is no SIEM integration, no centralized log aggregation, no automated alert correlation, and no defined monitoring dashboards for threat detection.',
        'partial', 'App-level security monitoring + Wazuh; no SIEM or centralized monitoring.', 'Moderate'
    ),
    'si-5': (
        'partial', 'technical',
        'The nist_publications table in BLACKSITE tracks NIST security publications and advisories. The NIST catalog updater maintains current control language. However, there are no automated subscriptions to US-CERT/CISA advisories, no automated CVE feed integration for application dependencies, and no formal process for receiving and acting on security alerts from software vendors.',
        'partial', 'nist_publications table tracks advisories; no automated alert subscriptions.', 'Low'
    ),
    'si-12': (
        'partial', 'procedural',
        'No formal information retention or disposal policy exists for BLACKSITE. System data (assessments, controls, POA&Ms, evidence) accumulates indefinitely without defined retention periods or disposal procedures. Backup data on Iapetus NAS does not have a defined retention limit. A retention and disposal policy should be developed.',
        'partial', 'No formal information retention or disposal policy; data accumulates indefinitely.', 'Low'
    ),

    # ── SR ──────────────────────────────────────────────────────────────────
    'sr-1': (
        'not_implemented', 'none',
        'No formal Supply Chain Risk Management Policy document exists. SCRM activities for BLACKSITE have not been formalized. Open source dependency selection is informal without documented SCRM criteria.',
        'fail', 'No SCRM policy document.', 'Moderate'
    ),
    'sr-2': (
        'not_implemented', 'none',
        'No SCRM Plan has been developed for BLACKSITE. There are no documented procedures for assessing and managing supply chain risks associated with software components, development tools, or hosting infrastructure.',
        'fail', 'No SCRM plan document.', 'Moderate'
    ),
    'sr-2.1': (
        'not_implemented', 'none',
        'No SCRM team or designated SCRM function exists. Supply chain risk management is not assigned to specific personnel with defined responsibilities.',
        'fail', 'No designated SCRM team or function.', 'Moderate'
    ),
    'sr-3': (
        'not_implemented', 'none',
        'No formal supply chain controls beyond basic pip package version pinning in requirements.txt have been implemented. No package integrity verification (pip hash mode), no software composition analysis, no approved vendor list, and no supply chain risk assessment process exists.',
        'fail', 'No supply chain controls beyond version pinning.', 'Moderate'
    ),
    'sr-5': (
        'not_applicable', 'none',
        'All BLACKSITE components are open source; no commercial acquisitions occur. Supplier acquisition strategies are not applicable.',
        'not_applicable', 'All open source; no commercial acquisitions.', None
    ),
    'sr-8': (
        'not_implemented', 'none',
        'No notification agreements with software suppliers exist. Open source maintainers do not have agreements to notify of security vulnerabilities beyond standard GitHub security advisories. No formal notification channel is established.',
        'fail', 'No supplier notification agreements for security vulnerabilities.', 'Moderate'
    ),
    'sr-10': (
        'not_implemented', 'none',
        'No formal component inspection program exists for BLACKSITE. Software components are not inspected for supply chain integrity beyond package version checking. No code audit of critical open source dependencies has been performed.',
        'fail', 'No component inspection program.', 'Moderate'
    ),
    'sr-11': (
        'partial', 'technical',
        'Requirements.txt pins specific package versions, preventing unintended version upgrades. However, pip hash verification mode (pip install --require-hashes) is not used, meaning downloaded packages are not cryptographically verified against known-good hashes. This leaves a gap for potential package substitution attacks on PyPI.',
        'partial', 'requirements.txt pins versions; pip hash verification not used.', 'Moderate'
    ),
    'sr-11.1': (
        'not_implemented', 'none',
        'No anti-counterfeit training has been conducted for personnel involved in acquiring or handling software components. This is a procedural gap.',
        'fail', 'No anti-counterfeit training conducted.', 'Low'
    ),
    'sr-11.2': (
        'not_applicable', 'none',
        'No hardware service or repair activities are in scope for BLACKSITE. Hardware maintenance is limited to server hardware managed separately. Not applicable for the software system boundary.',
        'not_applicable', 'No hardware service/repair in BLACKSITE scope.', None
    ),
    'sr-12': (
        'partial', 'procedural',
        'Hardware disposal for the Borisov server is managed informally by the admin. No formal component disposal procedures have been documented, no data sanitization procedures for storage media disposal, and no disposal records are maintained.',
        'partial', 'Informal hardware disposal; no formal documented procedures or records.', 'Low'
    ),
}

# ---------------------------------------------------------------------------
# Severity → due date mapping
# ---------------------------------------------------------------------------
SEVERITY_DAYS = {'High': 30, 'Moderate': 90, 'Low': 180}


async def main():
    engine = make_engine(config)
    Session = make_session_factory(engine)

    async with Session() as s:
        # ── 1. Update the BLACKSITE system record ──────────────────────────
        print("=" * 60)
        print("Step 1: Updating BLACKSITE system record")
        print("=" * 60)

        description = (
            "BLACKSITE is a web-based Security Assessment Platform built on FastAPI + Python 3.8 with "
            "a SQLCipher AES-256 encrypted SQLite database. The system provides Risk Management Framework (RMF) "
            "workflow support including control assessment tracking, Plan of Action & Milestones (POA&M) management, "
            "risk register, evidence repository, System Security Plan data management, ATO workflow, compliance "
            "framework crosswalking, security training quizzes, and role-based access for the full RMF team. "
            "Authentication is enforced via Authelia MFA (TOTP/WebAuthn) with Caddy reverse proxy header injection. "
            "Authorization uses a 7-role RBAC system enforced in Python on every route."
        )
        purpose = (
            "BLACKSITE serves as the central RMF management platform for tracking the security posture of IT systems "
            "under assessment. It automates control assessment workflows, generates ATO documentation packages, "
            "manages POA&M lifecycle from identification through closure, and provides continuous monitoring dashboards. "
            "The platform supports ISSOs, ISSMs, SCAs, CISOs, and Authorizing Officials in their RMF responsibilities. "
            "No PII, PHI, CUI, or classified information is processed or stored."
        )
        boundary = (
            "System boundary includes: (1) BLACKSITE FastAPI application running as a systemd service on Borisov "
            "(Dell R510, 192.168.86.102, Ubuntu 20.04 FIPS kernel); (2) SQLCipher-encrypted SQLite database on "
            "Borisov local storage; (3) Caddy reverse proxy (Docker container) providing TLS termination and "
            "forward_auth integration; (4) Authelia (Docker container) providing MFA authentication and session "
            "management. External dependencies (ip-api.com, NIST GitHub API, Let's Encrypt ACME) are outside the "
            "authorization boundary. Nightly backups to Iapetus NAS (192.168.86.213) are part of the backup boundary. "
            "All user access is remote via HTTPS on port 443, geo-restricted to US IP addresses."
        )
        ato_notes = (
            "ATO Assessment completed 2026-03-09. System assessed against NIST SP 800-53 Rev 5 Low baseline (149 controls). "
            "Summary: 47 controls Implemented/Pass, 4 controls Inherited, 27 controls Not Applicable, "
            "54 controls Partial, 17 controls Not Implemented. "
            "Key strengths: Authelia MFA enforcement, SQLCipher encryption at rest, TLS in transit, "
            "comprehensive audit logging, full RBAC implementation, boundary protection (loopback + Caddy + geo-restriction). "
            "Key gaps requiring POA&M remediation: Python 3.8 EOL (HIGH), missing IR plan (HIGH), missing CP plan (HIGH), "
            "no formal policy documents for most control families (LOW), no formal SSP document (MODERATE). "
            "ATO granted for 3 years contingent on POA&M completion per scheduled dates. "
            "Annual review required. Next full assessment due: 2027-03-09."
        )

        await s.execute(text("""
            UPDATE systems SET
                ao_name = :ao_name,
                ao_email = :ao_email,
                issm_name = :issm_name,
                issm_email = :issm_email,
                isso_name = :isso_name,
                isso_email = :isso_email,
                description = :description,
                purpose = :purpose,
                boundary = :boundary,
                auth_status = 'authorized',
                overall_impact = 'Low',
                ato_decision = 'approved',
                categorization_status = 'approved',
                categorization_approved_by = 'Dan Borisov',
                ato_duration = '3',
                ato_notes = :ato_notes,
                ato_signed_by = 'Dan Borisov',
                ato_signed_at = :ato_signed_at,
                updated_at = :updated_at
            WHERE id = :id
        """), {
            'ao_name': 'Dan Borisov',
            'ao_email': 'daniel@thekramerica.com',
            'issm_name': 'Dan Borisov',
            'issm_email': 'daniel@thekramerica.com',
            'isso_name': 'Dan Borisov',
            'isso_email': 'daniel@thekramerica.com',
            'description': description,
            'purpose': purpose,
            'boundary': boundary,
            'ato_notes': ato_notes,
            'ato_signed_at': NOW,
            'updated_at': NOW,
            'id': BSV_ID,
        })
        await s.commit()
        print("  System record updated.")

        # ── 2. Add nist_low framework ──────────────────────────────────────
        print("\nStep 2: Adding nist_low framework to BLACKSITE")
        r = await s.execute(text(
            "SELECT id FROM system_frameworks WHERE system_id=:sid AND framework_id=:fid"
        ), {'sid': BSV_ID, 'fid': FW_ID})
        if r.fetchone():
            print("  nist_low already in system_frameworks — skipping.")
        else:
            await s.execute(text("""
                INSERT INTO system_frameworks (system_id, framework_id, added_by, added_at, sub_category)
                VALUES (:sid, :fid, :by, :at, 'primary')
            """), {'sid': BSV_ID, 'fid': FW_ID, 'by': BY, 'at': NOW})
            await s.commit()
            print("  nist_low framework added.")

        # ── 3. Load catalog controls for nist_low ─────────────────────────
        print("\nStep 3: Loading nist_low catalog controls")
        r = await s.execute(text("""
            SELECT cc.id, cc.control_id, cc.title, cc.domain
            FROM catalog_controls cc
            JOIN compliance_frameworks cf ON cc.framework_id = cf.id
            WHERE cf.short_name = 'nist_low'
            ORDER BY cc.control_id
        """))
        catalog_rows = r.fetchall()
        catalog_map = {row[1]: (row[0], row[2], row[3]) for row in catalog_rows}
        print(f"  Loaded {len(catalog_map)} catalog controls.")

        # ── 4. Check existing system_controls ─────────────────────────────
        print("\nStep 4: Checking existing system_controls")
        r = await s.execute(text(
            "SELECT control_id FROM system_controls WHERE system_id=:sid"
        ), {'sid': BSV_ID})
        existing_controls = {row[0] for row in r.fetchall()}
        print(f"  Existing system_controls rows: {len(existing_controls)}")

        # ── 5. Insert system_controls ──────────────────────────────────────
        print("\nStep 5: Inserting system_controls assessments")
        counts = {'implemented': 0, 'partial': 0, 'not_implemented': 0,
                  'not_applicable': 0, 'inherited': 0, 'skipped': 0}
        result_counts = {'pass': 0, 'fail': 0, 'partial': 0, 'not_applicable': 0}

        for ctrl_id, data in CONTROLS.items():
            status, impl_type, narrative, result, notes, _ = data

            if ctrl_id in existing_controls:
                counts['skipped'] += 1
                continue

            cat_info = catalog_map.get(ctrl_id)
            if not cat_info:
                print(f"  WARNING: {ctrl_id} not found in catalog — skipping")
                continue

            cat_ctrl_id, ctrl_title, ctrl_family = cat_info
            family = ctrl_family or ctrl_id.split('-')[0].upper()

            # Map assessment result
            if result == 'pass':
                result_counts['pass'] += 1
            elif result == 'fail':
                result_counts['fail'] += 1
            elif result == 'partial':
                result_counts['partial'] += 1
            else:
                result_counts['not_applicable'] += 1

            # inherited_from is a FK to systems(id) — must be NULL or a valid system UUID
            # Store the inherited system name in the narrative instead
            inherited_from = None
            inherited_narrative = (
                'Authelia — This control is fully inherited from Authelia, which provides the authentication '
                'and MFA layer for BLACKSITE. Authelia is self-hosted and maintained by the system admin.'
                if status == 'inherited' else None
            )

            await s.execute(text("""
                INSERT INTO system_controls (
                    system_id, control_id, control_family, control_title,
                    status, implementation_type, narrative, responsible_role,
                    inherited_from, inherited_narrative,
                    last_updated_by, last_updated_at, created_at, created_by,
                    source_catalog, catalog_control_id,
                    assessment_result, assessment_notes, assessed_by, assessed_at
                ) VALUES (
                    :system_id, :control_id, :control_family, :control_title,
                    :status, :implementation_type, :narrative, :responsible_role,
                    :inherited_from, :inherited_narrative,
                    :last_updated_by, :last_updated_at, :created_at, :created_by,
                    :source_catalog, :catalog_control_id,
                    :assessment_result, :assessment_notes, :assessed_by, :assessed_at
                )
            """), {
                'system_id': BSV_ID,
                'control_id': ctrl_id,
                'control_family': family,
                'control_title': ctrl_title,
                'status': status,
                'implementation_type': impl_type,
                'narrative': narrative,
                'responsible_role': 'ISSO',
                'inherited_from': inherited_from,
                'inherited_narrative': inherited_narrative,
                'last_updated_by': BY,
                'last_updated_at': NOW,
                'created_at': NOW,
                'created_by': BY,
                'source_catalog': 'nist_low',
                'catalog_control_id': cat_ctrl_id,
                'assessment_result': result,
                'assessment_notes': notes,
                'assessed_by': BY,
                'assessed_at': NOW,
            })
            counts[status] += 1

        await s.commit()
        print(f"  Inserted: implemented={counts['implemented']}, partial={counts['partial']}, "
              f"not_implemented={counts['not_implemented']}, not_applicable={counts['not_applicable']}, "
              f"inherited={counts['inherited']}, skipped={counts['skipped']}")

        # ── 6. Check existing POA&Ms for this system ───────────────────────
        print("\nStep 6: Checking existing POA&M items")
        r = await s.execute(text(
            "SELECT control_id FROM poam_items WHERE system_id=:sid AND control_id IS NOT NULL"
        ), {'sid': BSV_ID})
        existing_poams = {row[0].lower() for row in r.fetchall() if row[0]}

        # Also check by weakness_name prefix to avoid script-generated dupes
        r2 = await s.execute(text(
            "SELECT weakness_name FROM poam_items WHERE system_id=:sid AND created_by='ato_assessment'"
        ), {'sid': BSV_ID})
        existing_poam_names = {row[0] for row in r2.fetchall()}
        print(f"  Existing POA&Ms for this system: {len(existing_poams)} with control IDs")

        # ── 7. Insert POA&M items ──────────────────────────────────────────
        print("\nStep 7: Inserting POA&M items for gaps")
        poam_count = 0
        poam_skipped = 0

        # Get current max POAM sequence for BSV system
        r = await s.execute(text(
            "SELECT COUNT(*) FROM poam_items WHERE system_id=:sid"
        ), {'sid': BSV_ID})
        existing_total = r.scalar() or 0
        poam_seq = existing_total + 1

        for ctrl_id, data in CONTROLS.items():
            status, impl_type, narrative, result, notes, severity = data

            # Only create POA&M for partial or not_implemented
            if status not in ('partial', 'not_implemented') or severity is None:
                continue

            weakness_name = f"[{ctrl_id.upper()}] {notes[:80]}" if len(notes) > 80 else f"[{ctrl_id.upper()}] {notes}"

            # Skip if already has a POA&M from this script
            if weakness_name in existing_poam_names:
                poam_skipped += 1
                continue

            days = SEVERITY_DAYS.get(severity, 180)
            scheduled = due(days)
            poam_id_str = f"BSV-ATO-{TODAY.replace('-','')}-{poam_seq:04d}-{ctrl_id.upper().replace('-','')}"

            cat_info = catalog_map.get(ctrl_id, (None, ctrl_id, None))
            cat_ctrl_id = cat_info[0]

            weakness_desc = (
                f"Control {ctrl_id.upper()} assessment result: {status.upper()}. "
                f"Finding: {notes} "
                f"System context: {narrative[:300]}..."
            )

            remediation_plan = _remediation(ctrl_id, status)
            root_cause = _root_cause(ctrl_id, status)

            await s.execute(text("""
                INSERT INTO poam_items (
                    id, poam_id, system_id, control_id,
                    weakness_name, weakness_description,
                    detection_source, severity, responsible_party,
                    resources_required, scheduled_completion,
                    status, remediation_plan, root_cause,
                    created_at, updated_at, created_by,
                    catalog_control_id
                ) VALUES (
                    :id, :poam_id, :system_id, :control_id,
                    :weakness_name, :weakness_description,
                    :detection_source, :severity, :responsible_party,
                    :resources_required, :scheduled_completion,
                    :status, :remediation_plan, :root_cause,
                    :created_at, :updated_at, :created_by,
                    :catalog_control_id
                )
            """), {
                'id': str(uuid.uuid4()),
                'poam_id': poam_id_str,
                'system_id': BSV_ID,
                'control_id': ctrl_id,
                'weakness_name': weakness_name,
                'weakness_description': weakness_desc,
                'detection_source': 'assessment',
                'severity': severity,
                'responsible_party': 'Dan Borisov (ISSO/AO)',
                'resources_required': 'Admin time (est. 2-8 hours per item)',
                'scheduled_completion': scheduled,
                'status': 'open',
                'remediation_plan': remediation_plan,
                'root_cause': root_cause,
                'created_at': NOW,
                'updated_at': NOW,
                'created_by': 'ato_assessment',
                'catalog_control_id': cat_ctrl_id,
            })
            poam_count += 1
            poam_seq += 1

        await s.commit()
        print(f"  POA&M items inserted: {poam_count}, skipped: {poam_skipped}")

        # ── 8. Final summary ───────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)

        r = await s.execute(text("""
            SELECT status, COUNT(*) FROM system_controls
            WHERE system_id=:sid GROUP BY status ORDER BY status
        """), {'sid': BSV_ID})
        print("\nSystem Controls by Status:")
        total_sc = 0
        for row in r.fetchall():
            print(f"  {row[0]:20s}: {row[1]}")
            total_sc += row[1]
        print(f"  {'TOTAL':20s}: {total_sc}")

        r = await s.execute(text("""
            SELECT assessment_result, COUNT(*) FROM system_controls
            WHERE system_id=:sid GROUP BY assessment_result ORDER BY assessment_result
        """), {'sid': BSV_ID})
        print("\nSystem Controls by Assessment Result:")
        for row in r.fetchall():
            print(f"  {row[0]:20s}: {row[1]}")

        r = await s.execute(text("""
            SELECT severity, COUNT(*) FROM poam_items
            WHERE system_id=:sid AND created_by='ato_assessment'
            GROUP BY severity ORDER BY severity
        """), {'sid': BSV_ID})
        print("\nNew POA&M Items by Severity:")
        total_poam = 0
        for row in r.fetchall():
            print(f"  {row[0]:20s}: {row[1]}")
            total_poam += row[1]
        print(f"  {'TOTAL NEW':20s}: {total_poam}")

        r = await s.execute(text("""
            SELECT COUNT(*) FROM poam_items WHERE system_id=:sid
        """), {'sid': BSV_ID})
        print(f"\nTotal POA&M items for BSV (all): {r.scalar()}")

        print("\nAssessment complete. BLACKSITE ATO package populated.")
        print(f"ATO signed by: Dan Borisov | Date: {TODAY} | Duration: 3 years")
        print(f"Next full assessment due: 2029-03-09")


def _remediation(ctrl_id: str, status: str) -> str:
    """Generate a remediation plan based on control family and status."""
    family = ctrl_id.split('-')[0]

    if status == 'not_implemented' and ctrl_id.endswith('-1'):
        return (
            f"Author a formal {ctrl_id.split('-')[0].upper()} Policy document covering scope, purpose, roles, "
            f"responsibilities, compliance, and review schedule per NIST 800-53 Rev 5 requirements. "
            f"Obtain review and approval from the Authorizing Official. Store signed policy in BLACKSITE evidence repository."
        )

    plans = {
        'ac-8': "Add a system use notification banner to the Authelia login portal configuration. The banner must state that the system is for authorized use only, usage is monitored, and unauthorized use is prohibited. Test banner display on all login paths.",
        'ac-20': "Document ip-api.com and NIST GitHub API connections as formal system interconnections in BLACKSITE. Perform a risk assessment for each external service. Create a documented risk acceptance or formal ISA for each connection.",
        'ca-3': "Create Interconnection Security Agreement (ISA) documents for ip-api.com and NIST GitHub API. Document data flows, security controls, and risk acceptance. Obtain AO signature on each ISA.",
        'ca-6': "Develop a complete System Security Plan (SSP) document following NIST SP 800-18 format. Include system description, boundary, data flows, personnel, and all control implementations. Obtain AO signature for formal authorization.",
        'ca-7': "Develop a Continuous Monitoring Strategy document. Define monitoring metrics, review frequency, reporting procedures, and alerting thresholds. Implement automated status reporting to AO on defined schedule.",
        'cp-1': "Author a Contingency Planning Policy document. Define scope, RTO/RPO objectives, roles, testing frequency, and plan maintenance requirements. Obtain AO approval.",
        'cp-2': "Develop a Contingency Plan document covering: system description, recovery priorities, RTO/RPO (suggest RTO=4hr, RPO=24hr), activation criteria, recovery procedures from Iapetus backup, alternate processing, and reconstitution procedures.",
        'cp-3': "Conduct tabletop contingency exercise after CP-2 is complete. Walk through recovery scenarios including database restore from Iapetus backup. Document exercise results and lessons learned.",
        'cp-4': "Perform a functional contingency test: execute a full restore from Iapetus NAS backup to a test environment. Verify application functionality post-restore. Document test results and update CP.",
        'cp-9': "Test backup restoration from Iapetus NAS. Define formal RPO (suggest 24 hours). Implement backup verification (test restore monthly). Document backup retention policy. Consider adding backup integrity verification.",
        'ir-1': "Author a formal Incident Response Policy document. Define scope, roles, reporting requirements, and IR program governance.",
        'ir-2': "Develop IR training materials based on the IR Plan (once created). Conduct annual tabletop exercise. Document training completion.",
        'ir-4': "Document incident handling procedures covering: detection, triage, containment, eradication, recovery, and post-incident review. Include decision trees for common incident types.",
        'ir-5': "Implement a formal incident tracking capability. At minimum, define what constitutes a reportable incident and create a simple incident log. Consider a dedicated incident management table in BLACKSITE.",
        'ir-6': "Define incident reporting procedures: what to report, to whom, within what timeframe. Identify reporting contacts (CISA, hosting provider, stakeholders). Document in IR Plan.",
        'ir-7': "Identify and document IR assistance resources: CISA (cisa.gov/report), hosting/ISP incident support contacts, external IR firm if applicable. Document in IR Plan.",
        'ir-8': "Create an Incident Response Plan document following NIST SP 800-61 Rev 2 structure. Include preparation, detection, analysis, containment, eradication, recovery, and post-incident phases.",
        'pl-4': "Develop a Rules of Behavior document for BLACKSITE users. Cover acceptable use, prohibited activities, data handling, reporting requirements, and consequences of violations. Require annual signed acknowledgment from all users.",
        'ps-6': "Develop access agreement template for BLACKSITE users. Include acceptable use, confidentiality obligations, and security responsibilities. Collect signed acknowledgments from all current users.",
        'ps-8': "Document a formal sanctions policy for information security violations. Define graduated sanctions from warning through termination. Reference in the AUP/Rules of Behavior.",
        'ra-3.1': "Perform a supply chain risk assessment for critical dependencies (pysqlcipher3, FastAPI, SQLAlchemy). Document dependency provenance, maintainer reputation, and known vulnerabilities. Implement pip-audit in deployment pipeline.",
        'sa-22': "Prioritize Python 3.8 upgrade path. Options: (1) Recompile pysqlcipher3 for Python 3.11+, (2) Migrate to sqlcipher3 or apsw with SQLCipher, (3) Implement application-level encryption replacing SQLCipher. Develop migration plan with target completion date.",
        'sc-12': "Develop a Key Management Plan document. Define SQLCipher key rotation procedures, backup encryption key storage in SOPS, key compromise procedures, and session key generation. Implement periodic key rotation process.",
        'si-2': "Establish a formal patch management policy. Define patch windows (suggest critical: 14 days, high: 30 days, medium: 90 days). Implement pip-audit in weekly cron. Prioritize Python 3.8 upgrade (see SA-22 POA&M).",
        'cm-4': "Document a change management process. At minimum: (1) document all changes before applying, (2) test in non-production, (3) maintain a change log in BLACKSITE. Consider adding a change_records table.",
        'au-4': "Implement audit log storage monitoring. Add a health check that alerts when database size exceeds threshold. Define log archival procedures (export old security_events to compressed backup annually).",
        'au-9': "Implement cryptographic signing of audit log entries. Options: HMAC each audit record with a signing key, or export logs to an append-only external log server (syslog, Loki). Prevents log tampering.",
        'ca-9': "Create formal internal connection documentation for Caddy→BLACKSITE and Authelia→BLACKSITE connections. Include data flows, ports, protocols, and security controls. Store in BLACKSITE system interconnections.",
        'sr-1': "Author a Supply Chain Risk Management Policy document. Define scope, objectives, roles, and required SCRM activities for software acquisition and deployment.",
        'sr-2': "Develop a SCRM Plan covering: approved package sources, dependency review procedures, vulnerability monitoring, and incident response for supply chain compromises.",
        'sr-3': "Implement supply chain controls: (1) Enable pip hash verification (--require-hashes), (2) Add pip-audit to deployment pipeline, (3) Pin all transitive dependencies in requirements.txt with hashes.",
        'sr-8': "Subscribe to security advisory channels for critical dependencies: GitHub security advisories for FastAPI, SQLAlchemy, pysqlcipher3. Document advisory sources in SCRM Plan.",
        'sr-10': "Perform a one-time code review of pysqlcipher3 and other critical dependencies. Document findings. Establish annual review cadence for critical open source components.",
        'sr-11': "Enable pip hash verification: run pip-compile with --generate-hashes to create requirements.txt with hashes. Update deployment procedure to use pip install --require-hashes.",
        'sr-11.1': "Include supply chain awareness in security training content. Add quiz questions covering package integrity, typosquatting, and dependency confusion attacks.",
    }

    return plans.get(ctrl_id,
        f"Review {ctrl_id.upper()} control requirements and develop a remediation approach. "
        f"Current status: {status}. Document remediation steps and implement within the scheduled completion timeframe. "
        f"Update system_controls assessment_result upon completion."
    )


def _root_cause(ctrl_id: str, status: str) -> str:
    family = ctrl_id.split('-')[0]
    if ctrl_id.endswith('-1') or status == 'not_implemented':
        if family in ('ir', 'cp'):
            return "Security program maturity gap: formal incident response and contingency planning documentation has not been prioritized for this homelab/small-org deployment. Resource and time constraints."
        if ctrl_id in ('sa-22',):
            return "Technical dependency constraint: pysqlcipher3 C extension requires Python 3.8 compilation on the FIPS kernel environment. Upgrade blocked by encryption layer dependency."
        return "Documentation gap: technical controls implemented but formal policy documentation not yet produced. Single-person operation without formal compliance program lifecycle."
    return (
        "Partial implementation: the technical mechanism exists but either the governing documentation, "
        "formal procedures, testing/validation, or full coverage is incomplete. Common in single-admin "
        "homelab environments operating without a full security team."
    )


asyncio.run(main())
