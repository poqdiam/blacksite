# Privacy Notice and Data Processing Disclosure

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09

---

## 1. Overview

This notice describes how the BLACKSITE GRC platform collects, processes, stores, and shares personal data about its users and visitors. BLACKSITE is operated by a solo developer / small team as a compliance management platform serving federal, state, local, tribal, and commercial organizations.

This notice applies to all individuals who access BLACKSITE, including registered users, organizational administrators, and demo visitors.

---

## 2. Personal Data Collected

### 2.1 User Account Data

When a user account is created, BLACKSITE collects and stores:

| Data Element | Description | Required |
|-------------|-------------|----------|
| Full name | Display name for the account | Yes |
| Email address | Used for account identification and notifications | Yes |
| Username | Unique identifier used for login | Yes |
| Password hash | Bcrypt hash of the user's password; plaintext is never stored | Yes |
| Role and access level | Admin, staff, or read-only designation | Yes |
| Account creation date | Timestamp of registration | Yes |
| Last login timestamp | Date and time of most recent successful authentication | Automatic |

### 2.2 Activity and Audit Data

BLACKSITE maintains an audit log for compliance and security purposes. The following events are logged with associated metadata:

- Login and logout events (including IP address and timestamp)
- Record creation, modification, and deletion events (user, timestamp, affected record)
- Administrative actions (user management, configuration changes)
- AI assistant queries (query text, timestamp, user — see Section 5 regarding Groq API)

### 2.3 Visitor and Session Data

For demo visitors and unauthenticated access:

- IP address (used for geo-IP lookup via ip-api.com to determine approximate country/region)
- Browser user-agent string (collected by web server)
- Pages accessed and timestamps
- Session token (ephemeral cookie for session state)

For authenticated users:
- Session token (stored as a server-side session; contains no personal data directly)
- Session creation and expiry timestamps

### 2.4 Compliance Workflow Data

Users may enter personal data about other individuals as part of compliance documentation (e.g., ISSO names, System Owner names, contractor information in SSP fields). BLACKSITE treats this data as organizational compliance records. The individual users responsible for entering this data are responsible for ensuring they have appropriate authority to do so.

---

## 3. Purpose of Processing

| Data | Purpose |
|------|---------|
| Account data | Authentication, authorization, account management |
| Audit log | Security monitoring, compliance evidence, incident investigation |
| IP address (authenticated) | Audit trail, anomalous login detection |
| IP address (visitor) | Demo analytics (country-level aggregate only) |
| Session data | Maintaining login state across requests |
| AI query text | Forwarding to Groq API to generate compliance assistant responses |

BLACKSITE does not use personal data for advertising, profiling, resale, or any purpose outside of platform operations.

---

## 4. Legal Basis for Processing

BLACKSITE processes personal data on the following bases:

- **Contractual necessity:** Processing account data, audit logs, and session data is necessary to provide the platform service that users and their organizations have contracted for.
- **Legitimate interest:** Security monitoring (audit logs, IP logging) is in the legitimate interest of the operator and all users to detect and prevent unauthorized access.
- **Legal obligation:** Retention of audit logs for 3 years is required under FISMA for federally connected systems.

For users in jurisdictions subject to GDPR or state privacy laws (California CCPA, Virginia CDPA, etc.), the legal bases above correspond to Article 6(1)(b) (contract performance) and Article 6(1)(f) (legitimate interests).

---

## 5. Data Sharing and Third-Party Disclosure

BLACKSITE shares data with third parties in the following limited circumstances only:

### 5.1 Groq API (AI Assistant)

When a user submits a query to the BLACKSITE AI compliance assistant, the query text is transmitted to **Groq, Inc.** for processing via the `llama-3.3-70b-versatile` model.

- **What is sent:** The user's query text and a system prompt defining the assistant's role
- **What is NOT sent:** User names, email addresses, account identifiers, SSP content, or any other platform data beyond the explicit query
- **Policy:** Users must not include personally identifiable information (PII) or protected health information (PHI) in AI assistant queries. The platform operator does not technically prevent such input but this use is prohibited under platform policy.
- **Groq's privacy policy:** https://groq.com/privacy-policy/

### 5.2 ip-api.com (Geo-IP Lookup)

Visitor IP addresses are sent to **ip-api.com** to determine the approximate geographic origin (country/region) for demo visitor analytics.

- **What is sent:** Visitor IP address
- **What is NOT sent:** Any user account data, credentials, or session identifiers
- **Note:** This service is used only for unauthenticated demo visitor tracking. Authenticated user IPs are not sent to this service.

### 5.3 No Other Sharing

BLACKSITE does not sell, rent, or share personal data with any other third parties. Aggregate, anonymized analytics (e.g., "15 visitors from the United States this month") may be reported to organizational customers but contain no personal identifiers.

---

## 6. Data Retention

| Data Category | Retention Period |
|--------------|-----------------|
| User account data | Duration of account + 1 year post-offboarding |
| Immutable audit logs | 3 years (FISMA requirement) |
| Assessment / SSP content | 6 years (federal records guidance) |
| AI chat logs (local) | 90 days |
| Session data | 30 days or until logout, whichever is sooner |
| Demo visitor logs | 90 days |

See the full Data Retention Policy (data-retention-policy.md) for disposal procedures.

---

## 7. Data Security

BLACKSITE implements the following controls to protect personal data:

- **Encryption at rest:** The SQLite database is encrypted using SQLCipher (AES-256). The encryption key is stored only in the systemd service unit environment, not in code or configuration files.
- **Encryption in transit:** All traffic is served via HTTPS (TLS 1.2+) through a Caddy reverse proxy with automatic certificate management.
- **Access control:** Role-based access control limits what data each user can view. Administrative functions require elevated privilege.
- **Authentication:** Passwords are hashed with bcrypt. Session tokens are server-side and cryptographically random.
- **Audit logging:** All authentication and data modification events are logged immutably with user, timestamp, and action.

No security measure is perfect. In the event of a data breach, affected users will be notified in accordance with the Incident Response Runbook.

---

## 8. User Rights

Users of the BLACKSITE platform have the following rights regarding their personal data:

| Right | How to Exercise |
|-------|----------------|
| **Access** | Contact the platform administrator to request a copy of your account data and associated audit records |
| **Correction** | Update name and email via platform account settings, or contact the administrator for other corrections |
| **Deletion** | Request account deletion via the platform or by contacting the administrator. Note: audit log entries tied to your account actions are retained for the retention periods above and cannot be deleted while the retention obligation persists |
| **Portability** | Request a JSON or CSV export of your account data by contacting the administrator |
| **Objection / Restriction** | Contact the administrator to discuss any concerns about specific processing activities |

Requests will be acknowledged within 5 business days and fulfilled within 30 days.

---

## 9. Cookies and Tracking

BLACKSITE uses:

- **Session cookies:** Necessary for maintaining login state. These are server-side session tokens with no personal data stored client-side.
- **No third-party tracking cookies:** No analytics platforms (Google Analytics, etc.) are embedded in the platform.
- **No persistent fingerprinting:** The platform does not implement browser fingerprinting or cross-session tracking beyond the server-side session.

---

## 10. Children's Privacy

BLACKSITE is a professional compliance management platform not directed at individuals under 18. The operator does not knowingly collect personal data from minors. If it is discovered that a minor has registered an account, that account will be deleted upon discovery.

---

## 11. Changes to This Notice

This notice is reviewed annually (next review: 2027-03-09) and updated whenever material changes occur to data processing practices. Registered users will be notified of material changes via the platform or email.

---

## 12. Contact Information

For privacy inquiries, data subject requests, or concerns:

**BLACKSITE Platform Administrator**
Contact via the platform's designated contact channel or the email address provided at contract/onboarding.

For urgent privacy concerns (e.g., suspected data breach affecting your account), reference the platform's Incident Response Runbook and contact the administrator directly.
