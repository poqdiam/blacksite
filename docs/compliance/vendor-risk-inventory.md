# Vendor and Dependency Risk Inventory

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09

---

## Overview

This document inventories the third-party software dependencies and external services used by the BLACKSITE platform, with risk classifications and mitigation notes. It supports vendor risk management obligations under NIST SP 800-53 SA-9 (External System Services) and serves as a reference for periodic supply chain security reviews.

---

## Section A: Software Dependencies

Versions are pinned per `requirements.txt`. All packages should be reviewed for known CVEs at each release cycle using `pip audit` or equivalent.

**Periodic audit command:**
```bash
cd /home/graycat/projects/blacksite
.venv/bin/pip install pip-audit
.venv/bin/pip-audit
```

---

### Web Framework and Server

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **fastapi** | pinned per requirements.txt | Core web framework; request routing, dependency injection, OpenAPI spec generation | Low | Actively maintained by Tiangolo/FastAPI team. Subscribe to GitHub releases for CVE notices. No known critical vulnerabilities in recent releases. |
| **uvicorn** | pinned per requirements.txt | ASGI server; runs the FastAPI app | Low | Lightweight, widely used. Bound to 127.0.0.1 in production (not exposed directly); all external traffic goes through Caddy. Limit of attack surface by design. |
| **python-multipart** | pinned per requirements.txt | Multipart form parsing (file uploads, form submissions) | Medium | Prior CVE (CVE-2024-24762 ReDoS) patched in 0.0.7+. Ensure version is >= 0.0.7. Validate all uploaded file types at the application layer. |

---

### Templating

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **jinja2** | pinned per requirements.txt | HTML template rendering | Medium | XSS risk if templates use `\|safe` filter on untrusted input. BLACKSITE templates should use auto-escaping. Prior RCE via SSTI (CVE-2023-21895 and others) are patched in current versions. Ensure auto-escape is enabled globally (`autoescape=True`). |

---

### Database and ORM

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **sqlalchemy** | pinned per requirements.txt | ORM and SQL abstraction layer | Low | Industry-standard ORM. Parameterized queries prevent SQL injection by default when using ORM or `text()` with bound parameters. Avoid raw string interpolation in SQL. |
| **aiosqlite** | pinned per requirements.txt | Async SQLite driver | Low | Thin async wrapper around Python's built-in `sqlite3`. Low attack surface. No known critical CVEs in recent versions. |
| **pysqlcipher3** | 1.2.0 | Encrypted SQLite driver (SQLCipher / AES-256) | Medium | Provides at-rest encryption. Version 1.2.0 — confirm this version's SQLCipher linkage is against SQLCipher 4.x (not 3.x which uses weaker defaults). The encryption key must be stored in the systemd service unit only (see Encryption Key Rotation Policy). Build-time dependency on `libsqlcipher-dev`. |

---

### Document Generation

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **python-docx** | pinned per requirements.txt | DOCX export of SSP and assessment reports | Low | Used for generating outbound documents only; does not parse untrusted DOCX files. Low XSS/macro risk since BLACKSITE generates but does not execute DOCX. |
| **pdfplumber** | pinned per requirements.txt | PDF text extraction (for import/parse workflows) | Medium | Parses untrusted PDF input. PDF parsers have historically been a CVE-rich attack surface (malformed PDFs). Use `defusedxml` for any XML within PDFs. Validate file type and size before passing to pdfplumber. Consider sandboxing PDF parsing if customer-uploaded PDFs are processed. |

---

### Data Processing and Utilities

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **pyyaml** | pinned per requirements.txt | YAML parsing (configuration, OSCAL content) | High | YAML parsing with `yaml.load()` (unsafe loader) allows arbitrary code execution. **Must use `yaml.safe_load()` exclusively.** Audit all YAML parsing calls in the codebase. Prior critical CVEs (CVE-2017-18342, CVE-2020-14343) affect unsafe loader. |
| **defusedxml** | pinned per requirements.txt | XML parsing protection (prevents XXE, entity expansion attacks) | Low | Specifically designed to prevent XML-based attacks. Use this instead of stdlib `xml.etree` for any untrusted XML input. No known CVEs in defusedxml itself. |
| **python-dateutil** | pinned per requirements.txt | Date/time parsing utilities | Low | No known security issues. Used for date handling in compliance timeline calculations. |

---

### HTTP Clients

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **requests** | pinned per requirements.txt | Synchronous HTTP client (used for API calls where async is not needed) | Low | Widely used, well-maintained. Ensure SSL verification is not disabled (`verify=True` — the default). No credential data should be logged from requests calls. |
| **httpx** | pinned per requirements.txt | Async HTTP client (used for Groq API calls and other async outbound requests) | Low | Modern replacement for requests in async contexts. Same cautions apply: do not disable SSL verification. Ensure API keys in Authorization headers are never logged. |

---

### File Handling

| Package | Version | Purpose | Risk Level | Security Notes |
|---------|---------|---------|-----------|----------------|
| **aiofiles** | pinned per requirements.txt | Async file I/O (for streaming large file reads/writes) | Low | No known security issues. Wrapper around OS file I/O. Ensure file paths are validated before use to prevent path traversal. |

---

### Security Audit Schedule for Dependencies

| Action | Frequency | Tool |
|--------|-----------|------|
| CVE scan of all dependencies | Monthly | `pip-audit` or `safety check` |
| Full dependency version review | At each release | Manual + pip-audit |
| YAML `safe_load` audit | At each code review | `grep -r "yaml.load("` |
| Jinja2 autoescape verification | Annually | Code review |
| pdfplumber input validation review | Annually | Code review |

---

## Section B: External Services

---

### Groq API

| Attribute | Detail |
|-----------|--------|
| **Service** | Groq, Inc. — LLM inference API |
| **Model used** | `llama-3.3-70b-versatile` |
| **Purpose** | AI compliance assistant backend; generates responses to user GRC queries |
| **Data sent** | User query text + system prompt (role definition); no user PII, no PHI, no SSP content |
| **Risk Level** | **High** |
| **Availability dependency** | AI assistant feature is unavailable if Groq API is down; core platform functions are unaffected |
| **Data residency** | Data processed by Groq on their infrastructure; subject to Groq's privacy policy and terms of service |
| **Mitigations** | (1) System prompt explicitly instructs model to behave as a GRC assistant; (2) Platform policy prohibits users from including PII or PHI in AI queries; (3) Groq API key is stored only in systemd service unit — not in code; (4) API key is rotated every 6 months or upon staff departure; (5) AI feature degrades gracefully (error message) if Groq API is unreachable |
| **BAA status** | Not applicable (Groq is not a HIPAA Business Associate; PHI must never be sent to this service) |
| **Monitoring** | Review Groq console for unexpected API usage spikes (may indicate key compromise) |
| **Groq privacy policy** | https://groq.com/privacy-policy/ |

**Risk narrative:** The Groq integration represents the highest external service risk due to the potential for sensitive compliance context to be included in AI queries by users. The primary control is a strong platform policy and user-facing guidance. Technical controls (prompt filtering) should be considered for future implementation. The absence of a BAA with Groq means PHI must be strictly excluded from all AI queries.

---

### ip-api.com

| Attribute | Detail |
|-----------|--------|
| **Service** | ip-api.com — Geo-IP lookup |
| **Purpose** | Country/region identification for demo visitor analytics |
| **Data sent** | Visitor IP address (unauthenticated visitors only) |
| **Risk Level** | **Low** |
| **Data residency** | IP address processed by ip-api.com's servers |
| **Mitigations** | (1) No authenticated user data is sent; (2) No API key required — no credential to compromise; (3) Only country-level data is used; individual IPs are not retained by the platform beyond the 90-day visitor log window; (4) Service is used for analytics only — unavailability has no functional impact on the platform |
| **Availability dependency** | None — geo-IP lookup failure is handled gracefully (visitor logged without geo data) |
| **Privacy note** | IP addresses are personal data in some jurisdictions. Visitor IP transmission to ip-api.com is disclosed in the platform Privacy Notice. |
| **ip-api.com docs** | http://ip-api.com/docs |

---

### GitHub (NIST OSCAL Content)

| Attribute | Detail |
|-----------|--------|
| **Service** | GitHub, Inc. — code hosting and static content delivery |
| **Purpose** | NIST OSCAL control catalog content (SP 800-53 control definitions, baselines) fetched for reference or local cache |
| **Data sent** | Outbound HTTP GET requests only; no user data transmitted |
| **Risk Level** | **Low** |
| **Mitigations** | (1) Read-only access — no credentials used for public OSCAL content; (2) OSCAL content is cached locally and hash-verified before use; (3) Platform does not dynamically execute any content fetched from GitHub; (4) GitHub outage affects content refresh only — cached content remains functional |
| **Supply chain note** | OSCAL content integrity should be verified against NIST-published checksums when available. Automated updates to cached control definitions should include hash verification. |

---

### Shodan / Censys (Reference Links)

| Attribute | Detail |
|-----------|--------|
| **Service** | Shodan (shodan.io) and Censys (censys.io) — internet scanning databases |
| **Purpose** | Outbound reference links in the platform UI (e.g., "check your IP on Shodan") |
| **Data sent** | None — outbound links only; no data is transmitted programmatically |
| **Risk Level** | **Minimal** |
| **Notes** | These are hyperlinks only. The user's browser makes any request to these services, not the BLACKSITE application server. No API integration exists. |

---

## Vendor Review Schedule

| Activity | Frequency |
|----------|-----------|
| Full vendor inventory review | Annually (each March) |
| Groq API usage review | Monthly (check console for anomalies) |
| Dependency CVE scan | Monthly (`pip-audit`) |
| Review Groq terms of service for changes | Semi-annually |
| Assess new dependencies added during the year | At each release |

---

## References

- NIST SP 800-53 Rev 5: SA-9 (External System Services), SA-12 (Supply Chain Risk Management), SR-3 (Supply Chain Controls and Processes)
- NIST SP 800-161r1: Cybersecurity Supply Chain Risk Management
- This platform's Encryption Key Rotation Policy (encryption-key-rotation-policy.md)
- This platform's Privacy Notice (privacy-notice.md) — Groq and ip-api.com disclosures
