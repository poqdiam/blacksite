# Personnel Security Procedures

**Document Owner:** BLACKSITE Platform Administrator
**Effective Date:** 2026-03-09
**Review Date:** 2027-03-09
**Reference:** NIST SP 800-53 PS controls (PS-1 through PS-8)

---

## 1. Purpose and Scope

This document defines the personnel security requirements for all individuals who have administrative or developer access to the BLACKSITE platform. These procedures protect the platform and its data against insider threats, unintentional misuse, and unauthorized access resulting from improper access management.

**In scope — all individuals with:**
- Root or sudo access to the production host (borisov / 192.168.86.102)
- Access to the BLACKSITE systemd service unit (which contains encryption keys and API keys)
- Admin-level accounts in the BLACKSITE platform itself (`admin_users` or `staff_users` configuration)
- Access to backup storage (iapetus NAS) where BLACKSITE data is stored
- Knowledge of the database encryption key, session secret, or API keys

**Current access holders (as of 2026-03-09):**
- Platform Administrator (solo developer): full access to all of the above

---

## 2. Pre-Access Requirements

Before any individual is granted administrative or developer access to BLACKSITE:

### 2.1 Background Check Recommendation

A background check is strongly recommended for all individuals receiving access to the production environment or encryption keys. At minimum:
- Identity verification
- Prior employment / reference check

For individuals who will access systems holding federal customer data (CUI, SSP content), a more formal background screening appropriate to the customer's requirements may be contractually required. Consult the customer's ISSO before granting access.

### 2.2 Non-Disclosure Agreement (NDA)

All personnel with access must sign a Non-Disclosure Agreement before receiving credentials. The NDA must cover:
- Confidentiality of customer data (SSP content, assessment records)
- Confidentiality of platform secrets (encryption keys, API keys)
- Obligation to report security incidents within the timeframes defined in this policy
- Post-employment data handling obligations

**Retain signed NDAs** in `/home/graycat/docs/personnel/[name]-nda.pdf` or equivalent secure document store.

### 2.3 Acceptable Use Agreement

All personnel must sign or acknowledge the Acceptable Use Policy (Section 6) before receiving access.

### 2.4 Access Request Documentation

Every access grant must be documented before credentials are issued. Create a record at `/home/graycat/docs/personnel/access-grants/YYYY-MM-DD-[name]-access.md` with:

```markdown
## Access Grant Record
Person: [Full name]
Role: [Admin / Developer / Auditor / Read-only]
Date granted: YYYY-MM-DD
Access scope: [Platform admin / Host SSH / Backup storage / All]
Granted by: [Name]
Business justification: [Why this person needs this access]
NDA signed: Yes / No [date]
AUA signed: Yes / No [date]
```

---

## 3. Access Provisioning

### 3.1 Principle of Least Privilege

Grant the minimum access required to perform the assigned function. Do not grant platform admin credentials to someone who only needs read-only access to compliance data.

**Access levels:**
| Level | Description | Access Granted |
|-------|-------------|---------------|
| **Read-only** | View SSPs and assessments; no modification | Platform read-only account |
| **Analyst** | Create and edit assessments, SSPs, POA&Ms | Platform standard user account |
| **Staff** | All analyst capabilities + user management | Platform staff account |
| **Admin** | Full platform control + config access | Platform admin account + possibly host SSH |
| **Developer** | Code changes, service management, key access | Host SSH + sudo + service unit access |

### 3.2 Platform Account Provisioning

Create a new platform account through the BLACKSITE admin interface:
1. Navigate to Admin → User Management
2. Create user with appropriate role
3. Provide temporary password to new user via a secure channel (not email plaintext)
4. Require password change on first login (if the platform supports forced rotation; otherwise instruct the user)

### 3.3 Host Access Provisioning (Admin/Developer)

```bash
# Add SSH public key to authorized_keys
# Collect the person's Ed25519 public key first
echo "ssh-ed25519 [PUBKEY] [person@host]" >> /home/graycat/.ssh/authorized_keys

# If sudo is needed:
sudo usermod -aG sudo [username]  # (only for developers)
```

Document all host-level access grants in the access grant record.

### 3.4 Service Unit Access

Access to the systemd service unit file (which contains encryption keys) is root-only by design. Grant this only to developers who absolutely require it, and only after NDA and AUA are signed.

---

## 4. Access Review

### 4.1 Quarterly Review

Every 90 days, the Platform Administrator reviews all accounts with access to BLACKSITE systems:

**Review checklist:**
- [ ] List all platform accounts: Admin → User Management
- [ ] List all SSH authorized_keys on the production host
- [ ] Confirm each account holder still needs that level of access
- [ ] Verify no unauthorized accounts have been added
- [ ] Confirm service unit file permissions are root:root 600
- [ ] Review audit log for any anomalous admin activity in the past 90 days
- [ ] Document review results in `/home/graycat/docs/personnel/access-reviews/YYYY-MM-DD-review.md`

**Frequency:** Quarterly (March, June, September, December)
**Next review:** 2026-06-09

### 4.2 Immediate Review Triggers

Conduct an out-of-cycle access review immediately following:
- Any security incident (per Incident Response Runbook)
- A personnel departure
- Discovery of an unauthorized account
- A customer complaint about unauthorized data access

---

## 5. Offboarding Checklist

When any individual with BLACKSITE access departs (employment end, contract end, role change removing access need):

Execute the following **on the day of departure** or as soon as notified:

**Platform access:**
- [ ] Disable the departing person's platform account (Admin → User Management → Deactivate)
- [ ] Do not immediately delete — retain per data retention policy (1 year post-offboarding, then hard delete)
- [ ] Review the person's recent audit log activity for anomalies before disabling

**SSH access (if applicable):**
- [ ] Remove their SSH public key from `~/.ssh/authorized_keys` on all hosts they had access to
- [ ] Verify removal: `grep "[identifier]" ~/.ssh/authorized_keys` returns nothing
- [ ] Check for any other authorized_keys locations (root, other service accounts)

**Credential rotation (if applicable):**
- [ ] If the person had access to the service unit file (encryption keys): rotate DB_ENCRYPTION_KEY, SECRET_KEY per the Encryption Key Rotation Policy — **this is mandatory**
- [ ] If the person knew the GROQ_API_KEY: rotate the Groq API key immediately
- [ ] If the person had iDRAC/NAS access: change those credentials

**Documentation:**
- [ ] Update the access grant record with offboarding date
- [ ] Note which credentials were rotated and when
- [ ] Retain NDA and access records for at least 3 years post-offboarding

**Equipment and access tokens:**
- [ ] Recover any platform-issued equipment or physical access tokens
- [ ] Revoke any personal API tokens issued through the platform

---

## 6. Acceptable Use Policy

All personnel with access to BLACKSITE agree to the following:

### Permitted Uses
- Using assigned credentials to perform assigned job functions
- Accessing customer data only as required for support, development, or administration tasks
- Reporting security incidents and policy violations

### Prohibited Uses
- Sharing credentials, passwords, SSH keys, or API keys with any unauthorized person
- Accessing customer data (SSP content, assessment records) for any purpose beyond operational necessity
- Using the platform's AI assistant with customer PII or PHI
- Installing unauthorized software or packages on the production host without following the Change Management Process
- Using admin credentials for personal projects or non-work purposes
- Storing encryption keys, API keys, or passwords in plaintext files, email, messaging apps, or version control

### Security Incident Reporting
Security incidents (suspected breaches, unauthorized access, policy violations, suspicious activity) must be reported to the Platform Administrator within **1 hour** of discovery. Delay in reporting is itself a policy violation.

### Consequences
Violations of this policy may result in immediate access revocation, termination of the working relationship, and — if customer data is involved — notification to affected customers and regulators.

---

## 7. Annual Security Awareness Training

All personnel with access must complete security awareness training annually. Training must cover at minimum:

| Topic | Objective |
|-------|-----------|
| Social engineering and phishing | Recognize and report phishing attempts targeting platform credentials |
| Password hygiene | Strong passwords, no reuse, use of a password manager |
| Secure handling of encryption keys | Never store keys in code, email, or plaintext files |
| Incident reporting | Know what constitutes an incident and how to report it |
| Data handling | Understand retention periods, PHI/PII handling, AI query policy |
| Access control | Principle of least privilege; report unexpected access grants |

**Training format:** Formal CBT, documented self-study, or structured review of this and related policies is acceptable for a small team.

**Documentation:** Record training completion in `/home/graycat/docs/personnel/training/YYYY-[name]-training.md`.

**Next training due:** 2027-03-09

---

## 8. Privileged Access Registry

Maintain a current registry of all accounts with admin or privileged access. This registry must be updated within 24 hours of any access change.

**Current registry (as of 2026-03-09):**

| Person | Role | Platform Access Level | Host SSH | Service Unit Access | Last Reviewed |
|--------|------|----------------------|----------|--------------------|--------------|
| Platform Administrator | Operator/Developer | Admin | Yes (sudo) | Yes | 2026-03-09 |

**Registry location:** `/home/graycat/docs/personnel/privileged-access-registry.md`

Update this registry:
- When access is granted (add entry)
- When access is revoked (mark inactive with offboarding date)
- At each quarterly access review (confirm all entries are current)

---

## 9. References

- NIST SP 800-53 Rev 5: PS-1 through PS-8 (Personnel Security controls)
- NIST SP 800-53 Rev 5: AC-2 (Account Management), AC-6 (Least Privilege)
- This platform's Acceptable Use Policy (Section 6 above)
- This platform's Encryption Key Rotation Policy (encryption-key-rotation-policy.md)
- This platform's Incident Response Runbook (incident-response-runbook.md)
- This platform's Data Retention Policy (data-retention-policy.md)
