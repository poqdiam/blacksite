#!/usr/bin/env python3
"""
Generate plain-language compliance interview questions for every framework control.
Output: one YAML file per framework in data/compliance-questions/
Run from the blacksite project root.
"""

import sqlite3
import yaml
import re
import os
from pathlib import Path

DB_PATH   = "blacksite.db"
OUT_DIR   = Path("data/compliance-questions")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Question bank ─────────────────────────────────────────────────────────────
# Each entry: (keyword_patterns, questions[])
# Applied in order; first match wins per slot; all matches accumulated up to 5 Q's.

QUESTION_BANK = [

    # ── Access Control ────────────────────────────────────────────────────────
    (["access control", "authorized access", "user access", "least privilege",
      "need-to-know", "role-based", "privilege", "permission", "account management"],
     [
        "Who currently has access to this system or data, and can you show me an up-to-date list?",
        "How does someone request access — what is the approval process from request to activation?",
        "What happens when an employee leaves the organization or changes roles? How quickly is their access updated or removed?",
        "How do we ensure staff only have access to what they need for their specific job — not more?",
        "How often do we review who has access to make sure it's still appropriate?",
     ]),

    (["remote access", "vpn", "telework", "telecommute"],
     [
        "Who is allowed to access our systems remotely, and how is that list maintained?",
        "What technology do we use for remote access, and how do we know it's configured securely?",
        "Are there restrictions on what remote workers can do compared to on-site staff?",
        "How do we detect if someone is connecting remotely from an unexpected location or device?",
     ]),

    (["session lock", "session termination", "idle", "timeout", "screen lock"],
     [
        "Do our systems automatically lock or log users out after a period of inactivity?",
        "How long before a screen locks when a workstation is left unattended?",
        "Do all systems — including shared workstations — enforce session timeouts consistently?",
     ]),

    (["multi-factor", "mfa", "two-factor", "2fa", "authentication",
      "identification", "credential", "password", "passphrase"],
     [
        "Do we require more than just a password to log in to sensitive systems (e.g., a code sent to your phone)?",
        "What are our password rules — length, complexity, how often people must change them?",
        "How do we handle it when someone forgets their password or gets locked out?",
        "Are shared or generic accounts (like 'admin') allowed, and if so, how are they controlled?",
        "How do we protect credentials from being stored or transmitted insecurely?",
     ]),

    # ── Audit & Logging ───────────────────────────────────────────────────────
    (["audit", "log", "logging", "monitoring", "event record", "audit trail",
      "audit log", "audit record", "activity log"],
     [
        "What user and system activities are we recording (logged)?",
        "Who reviews those logs, and how often?",
        "How long do we keep log records, and where are they stored?",
        "Could a log be altered or deleted by someone who wanted to cover their tracks? How do we prevent that?",
        "If something suspicious happened last Tuesday at 2 PM, could we pull up a record of exactly what occurred?",
     ]),

    # ── Awareness & Training ──────────────────────────────────────────────────
    (["awareness", "training", "education", "role-based training",
      "security training", "phishing", "social engineering"],
     [
        "What security or compliance training is required for staff, and how often must they complete it?",
        "How do we know who has and hasn't completed the required training?",
        "What happens if someone fails training or doesn't complete it on time?",
        "Is training content updated when new threats or policy changes occur?",
        "Do different roles (e.g., IT vs. HR vs. executives) get different training tailored to their responsibilities?",
     ]),

    # ── Configuration Management ──────────────────────────────────────────────
    (["configuration", "baseline", "hardening", "secure configuration",
      "default setting", "patch", "vulnerability", "software inventory",
      "hardware inventory", "asset inventory", "asset management"],
     [
        "Do we have a documented 'secure baseline' for how systems should be set up?",
        "How do we check that systems are actually configured the way they're supposed to be?",
        "How do we find out about security patches, and how quickly do we apply them?",
        "What happens if someone changes a system configuration without authorization?",
        "Can we produce a list of every device and software version we're responsible for right now?",
     ]),

    # ── Contingency Planning & Business Continuity ────────────────────────────
    (["contingency", "continuity", "disaster recovery", "backup", "resilience",
      "recovery", "restore", "failover", "availability", "rto", "rpo",
      "business continuity", "bcp", "drp"],
     [
        "If our main system went down completely right now, what would we do, and how long would recovery take?",
        "How often do we back up critical data, and do we periodically test that backups can actually be restored?",
        "Where are backups stored — are they in the same location as the primary system? (If yes, that's a risk.)",
        "Is there a documented plan for continuing critical operations during an outage or disaster?",
        "When did we last test our recovery plan, and what did we find?",
     ]),

    # ── Incident Response ─────────────────────────────────────────────────────
    (["incident", "breach", "response", "notification", "reportable",
      "data breach", "security event", "security incident"],
     [
        "If we discovered a security incident or data breach today, who is the first person called and what happens next?",
        "Do we have a written incident response plan? When was it last updated and tested?",
        "What is our legal obligation to notify regulators or affected individuals if a breach occurs, and what is the timeline?",
        "How do we decide whether something is a real security incident versus a false alarm?",
        "After an incident is resolved, how do we capture lessons learned to prevent it from happening again?",
     ]),

    # ── Maintenance ───────────────────────────────────────────────────────────
    (["maintenance", "maintenance record", "controlled maintenance",
      "maintenance tool", "nonlocal maintenance"],
     [
        "Who is authorized to perform maintenance on our systems, and how is that list controlled?",
        "When external vendors or contractors do maintenance, how do we supervise their access?",
        "Are maintenance activities — especially remote ones — logged and reviewed?",
        "How do we ensure maintenance tools (software used to fix or update systems) are trustworthy and not malicious?",
     ]),

    # ── Media Protection ─────────────────────────────────────────────────────
    (["media", "removable", "usb", "portable", "media sanitization",
      "media disposal", "media protection"],
     [
        "Can staff plug in USB drives or other removable media? If so, is there a policy governing this?",
        "When a hard drive or device is retired or sent for repair, how do we ensure data can't be recovered from it?",
        "How do we track physical media (tapes, drives) that contain sensitive information?",
        "What happens to printed documents containing sensitive information — is there a secure disposal process?",
     ]),

    # ── Personnel Security ────────────────────────────────────────────────────
    (["personnel", "screening", "background check", "termination",
      "transfer", "sanctions", "workforce"],
     [
        "Do we conduct background checks before hiring staff who will access sensitive systems or data?",
        "What happens on an employee's last day to ensure their access is revoked and equipment returned?",
        "If an employee is transferred to a different role, how do we adjust their access accordingly?",
        "Is there a clear consequence (disciplinary process) for staff who violate security policies?",
        "How do we handle contractors or temps who need access — do they go through the same screening?",
     ]),

    # ── Physical & Environmental ──────────────────────────────────────────────
    (["physical", "facility", "environmental", "access badge", "visitor",
      "data center", "server room", "workstation", "clean desk"],
     [
        "Who is allowed into areas where servers or sensitive systems are housed, and how is access controlled?",
        "How do we track visitors entering secure areas — are they signed in, escorted, and signed out?",
        "Are cameras or other monitoring systems in place in sensitive areas?",
        "What protects our equipment from environmental hazards like fire, flood, or power outages?",
        "Is there a clean-desk policy to ensure sensitive information isn't left visible when workstations are unattended?",
     ]),

    # ── Planning ─────────────────────────────────────────────────────────────
    (["plan", "policy", "procedure", "rules of behavior", "system security plan",
      "ssp", "security plan", "privacy plan"],
     [
        "Do we have a documented security or privacy plan for this system? When was it last reviewed?",
        "Who is responsible for keeping this plan up to date, and what triggers a revision?",
        "Have all staff who use this system read and acknowledged the rules of behavior?",
        "How does this plan connect to broader organizational policies?",
     ]),

    # ── Program Management ────────────────────────────────────────────────────
    (["program management", "governance", "oversight", "executive", "leadership",
      "portfolio", "enterprise"],
     [
        "Who at the executive level is responsible for our overall security program, and how are they involved?",
        "How does leadership receive updates on our security posture and significant risks?",
        "Do we have a dedicated budget for security activities, and how is it prioritized?",
        "How do security policies get approved and communicated across the organization?",
     ]),

    # ── Risk Assessment ───────────────────────────────────────────────────────
    (["risk", "risk assessment", "risk management", "threat", "vulnerability assessment",
      "risk analysis", "risk register", "impact", "likelihood"],
     [
        "How do we identify what could go wrong with our systems or data (threats and vulnerabilities)?",
        "When was our last formal risk assessment completed, and what were the main findings?",
        "How do we decide which risks to fix first versus which ones to accept?",
        "Is there a documented list of known risks and what we're doing about each one?",
        "Who is involved in reviewing and approving risk decisions?",
     ]),

    # ── System & Services Acquisition ────────────────────────────────────────
    (["acquisition", "supply chain", "vendor", "third-party", "third party",
      "contractor", "developer", "outsource", "procurement", "software development",
      "system development", "sdlc"],
     [
        "When we buy new software or bring on a vendor, what security questions do we ask them?",
        "Do our contracts with vendors include requirements around security and data protection?",
        "How do we verify that software or systems we purchase don't have built-in security weaknesses?",
        "If a key vendor had a breach, how would we know, and what would we do?",
        "How do we ensure development or customization work meets security standards before going live?",
     ]),

    # ── System & Communications Protection ────────────────────────────────────
    (["network", "boundary", "firewall", "encryption", "cryptography",
      "tls", "https", "transmission", "in transit", "at rest",
      "communications", "data in transit", "data at rest"],
     [
        "Is sensitive data encrypted when it's stored, and also when it's sent across the network?",
        "What encryption standards do we use, and are they current (not outdated like MD5 or DES)?",
        "How do we separate our internal network from the internet and from less-trusted networks?",
        "If someone intercepted our network traffic, could they read sensitive information?",
        "How do we monitor our network for unusual or unauthorized activity?",
     ]),

    # ── System & Information Integrity ────────────────────────────────────────
    (["integrity", "malware", "antivirus", "malicious code", "spam",
      "flaw remediation", "patch management", "software update",
      "security alert", "integrity check"],
     [
        "Do all our systems have up-to-date antivirus or endpoint protection software running?",
        "How quickly do we apply security patches after they're released — is there a defined timeline?",
        "How would we know if data or a file had been secretly altered by someone unauthorized?",
        "Are staff warned about phishing emails or other social engineering attempts? How?",
        "What is our process when a new vulnerability is publicly announced that might affect our systems?",
     ]),

    # ── Supply Chain Risk ─────────────────────────────────────────────────────
    (["supply chain risk", "component", "counterfeit", "tamper", "provenance"],
     [
        "Do we verify that hardware and software we receive hasn't been tampered with during shipping or manufacturing?",
        "How do we vet the security practices of companies in our software supply chain (e.g., open-source libraries)?",
        "What would we do if we discovered a component we use had a known backdoor or vulnerability?",
     ]),

    # ── Privacy — Data Subject Rights ─────────────────────────────────────────
    (["data subject", "right to access", "right to erasure", "right to rectification",
      "right to portability", "subject access", "individual rights", "opt-out",
      "consent", "withdrawal"],
     [
        "If a person asks us 'what data do you hold about me?', can we pull that together and respond within the required timeframe?",
        "If someone asks us to delete their personal data, what is our process, and how long does it take?",
        "How do we handle a request to correct inaccurate personal data?",
        "Can individuals take their data and move it to another service? Do we support that?",
        "How do we record and manage consent — and what happens when someone withdraws it?",
     ]),

    (["privacy notice", "transparency", "lawful basis", "lawfulness",
      "purpose limitation", "data minimisation", "minimization", "purpose"],
     [
        "What legal basis do we rely on for each type of personal data we collect — is this documented?",
        "How do we tell people what we're doing with their data, and when do we tell them?",
        "Do we collect any data that isn't strictly necessary for the stated purpose?",
        "If our purpose for collecting data changes, what is our process for updating people?",
        "Who in the organization is responsible for ensuring our data processing is lawful?",
     ]),

    (["data retention", "retention period", "storage limitation", "data deletion",
      "data disposal", "retention schedule"],
     [
        "How long do we keep personal or sensitive data after it's no longer needed?",
        "Is there a written retention schedule that specifies what data is kept for how long?",
        "What is our process for securely deleting data when the retention period expires?",
        "How do we ensure backups and archives are also subject to the same retention limits?",
     ]),

    (["data protection officer", "dpo", "privacy officer", "privacy by design",
      "privacy impact", "pia", "dpia"],
     [
        "Who in our organization is responsible for privacy compliance, and what authority do they have?",
        "When we build a new product or process that handles personal data, how do we bake privacy in from the start?",
        "Have we conducted a Privacy Impact Assessment (PIA) for this system? What did it find?",
        "How do we contact our Data Protection Officer, and what situations require their involvement?",
     ]),

    (["data breach", "breach notification", "supervisory authority", "72 hour",
      "notify", "regulator"],
     [
        "If we discovered a data breach right now, do we know which regulatory authority to notify and within what timeframe?",
        "What information must be included in a breach notification to regulators versus to affected individuals?",
        "Who makes the final decision on whether a security incident is a notifiable breach?",
        "Do we have template notification letters ready to go so we can meet tight reporting deadlines?",
     ]),

    # ── Financial Controls ────────────────────────────────────────────────────
    (["financial", "payment", "transaction", "cardholder", "card data",
      "pci", "account number", "cvv", "pan"],
     [
        "Who has access to payment card or financial account data, and is that list as small as possible?",
        "Is payment data encrypted wherever it's stored and transmitted?",
        "Do we ever store the full card number, CVV, or PIN data — even temporarily?",
        "How do we ensure payment systems are segmented from the rest of our network?",
        "When was our last payment security assessment, and what were the findings?",
     ]),

    (["segregation", "separation of duties", "dual control", "four-eyes"],
     [
        "Are critical financial or system tasks split between at least two people so no single person has full control?",
        "Who reviews and approves financial transactions, and is that person different from the one initiating them?",
        "How do we prevent a single administrator from being able to create and approve their own changes?",
     ]),

    # ── Change Management ────────────────────────────────────────────────────
    (["change", "change management", "change control", "change request",
      "configuration change", "release", "deployment"],
     [
        "What is the process for making a change to our system — who approves it and what testing is required?",
        "How do we roll back a change if something goes wrong after it's deployed?",
        "Are emergency changes handled differently from normal changes? What's the process?",
        "Can a developer or admin make an unauthorized change to a production system? How would we detect it?",
        "How do we test changes in a non-production environment before applying them to live systems?",
     ]),

    # ── Vulnerability Management ──────────────────────────────────────────────
    (["vulnerability", "penetration test", "pen test", "scan", "security assessment",
      "security testing", "remediation", "weakness"],
     [
        "How often do we scan our systems for vulnerabilities, and who reviews the results?",
        "When a vulnerability is found, how do we prioritize and track fixing it?",
        "Do we conduct regular penetration testing — where someone tries to break in — and how are findings acted on?",
        "How do we find out about new vulnerabilities that affect software we use?",
        "Is there a maximum timeframe within which critical vulnerabilities must be remediated?",
     ]),

    # ── Encryption & Key Management ───────────────────────────────────────────
    (["key management", "cryptographic key", "certificate", "pki", "key rotation",
      "key storage", "hsm"],
     [
        "Who is responsible for managing our encryption keys, and what happens if that person is unavailable?",
        "How are encryption keys stored — are they protected from unauthorized access?",
        "How often do we rotate (replace) encryption keys, and is this documented?",
        "What happens to old keys when they're replaced — are they securely destroyed?",
        "Do we use certificates for identity verification? Who manages their renewal so they don't expire?",
     ]),

    # ── Security Operations / Monitoring ─────────────────────────────────────
    (["security operations", "soc", "siem", "threat detection", "intrusion",
      "detection", "alerting", "real-time monitoring", "continuous monitoring"],
     [
        "How do we get alerted to suspicious activity on our systems — is monitoring happening around the clock?",
        "What is the process when an alert is triggered — who receives it and what do they do?",
        "How do we distinguish a genuine threat from a false alarm?",
        "Can we tell if someone is probing or attacking our systems right now?",
        "How are monitoring tools kept up to date to recognize new types of attacks?",
     ]),

    # ── Identity Governance ───────────────────────────────────────────────────
    (["identity", "account", "provisioning", "deprovisioning", "user lifecycle",
      "orphan account", "privileged account", "service account", "admin account"],
     [
        "Do we have a complete list of all user accounts across all systems, including service and admin accounts?",
        "How do we find and clean up accounts that belong to people who no longer work here?",
        "Are privileged (admin) accounts separate from regular user accounts for the same person?",
        "How is access reviewed periodically to ensure it's still appropriate and current?",
     ]),

    # ── Data Classification ────────────────────────────────────────────────────
    (["classification", "data classification", "sensitivity", "labeling",
      "marking", "handling", "data category", "data type"],
     [
        "Do we have a data classification scheme — a way of categorizing data by how sensitive it is?",
        "How does an employee know how to handle a particular type of data — are there clear guidelines?",
        "Is sensitive data labeled or marked so people know to treat it carefully?",
        "What safeguards apply to our most sensitive data, and are they consistently applied?",
     ]),

    # ── Third Party / Vendor ──────────────────────────────────────────────────
    (["third-party assessment", "supplier", "service provider", "subprocessor",
      "data processing agreement", "dpa", "baa", "business associate"],
     [
        "Do we have written agreements with all vendors who handle our sensitive or regulated data?",
        "How do we verify that our key vendors are actually following the security requirements in their contracts?",
        "What happens if a vendor has a security incident that affects our data?",
        "Do we know who our vendors' sub-vendors (subprocessors) are, and have we approved them?",
        "How often do we re-evaluate vendor security as part of contract renewal?",
     ]),

    # ── Portable Devices & BYOD ───────────────────────────────────────────────
    (["mobile", "byod", "bring your own", "portable device", "laptop",
      "mobile device", "smartphone", "tablet", "endpoint"],
     [
        "Are employees allowed to use personal devices to access work systems or data?",
        "If a work laptop or phone is lost or stolen, can we remotely wipe the data?",
        "Are mobile devices required to have encryption, a PIN, and remote wipe capability?",
        "How do we prevent sensitive data from being saved to personal cloud storage on a work device?",
     ]),

    # ── Secure Development ────────────────────────────────────────────────────
    (["secure coding", "secure development", "code review", "static analysis",
      "owasp", "injection", "xss", "application security", "appsec",
      "development security", "devops", "sast", "dast"],
     [
        "Are developers trained in secure coding practices, such as how to prevent SQL injection or cross-site scripting?",
        "Is code reviewed for security vulnerabilities before it's deployed to production?",
        "Do we run automated security tests against our applications as part of the build process?",
        "How do we manage security vulnerabilities discovered in libraries or frameworks we use?",
        "Are production and development environments completely separated?",
     ]),

    # ── Compliance Monitoring ─────────────────────────────────────────────────
    (["compliance monitoring", "audit finding", "corrective action", "remediation plan",
      "gap assessment", "assessment finding", "internal audit", "external audit"],
     [
        "How do we track compliance findings and make sure they're resolved in a timely manner?",
        "Who is responsible for follow-up on audit or assessment findings?",
        "When an audit uncovers a gap, what is the process for creating and executing a remediation plan?",
        "How does leadership receive updates on the status of open compliance findings?",
     ]),

    # ── Regulatory Reporting ──────────────────────────────────────────────────
    (["reporting", "regulatory reporting", "annual report", "attestation",
      "certification", "self-assessment", "questionnaire", "saq"],
     [
        "What compliance reports or attestations do we need to submit, and to whom, and on what schedule?",
        "Who is responsible for preparing and signing off on our compliance reporting?",
        "How do we gather the evidence needed to support our compliance submissions?",
        "What happens if we discover a compliance issue during the reporting process?",
     ]),

    # ── General fallback ──────────────────────────────────────────────────────
    (["__FALLBACK__"],
     [
        "Can you walk me through how we currently handle this requirement in our day-to-day operations?",
        "Is there a written policy or procedure for this? When was it last reviewed and updated?",
        "Who owns this control — who is responsible for ensuring it's in place and working?",
        "How would we know if this control failed or wasn't being followed?",
        "Do we have any evidence (logs, reports, records) that this control is actually operating effectively?",
     ]),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return (text or "").lower()


def _pick_questions(control_id: str, title: str, domain: str, description: str,
                    n: int = 5):
    """Select the most relevant questions for a control, up to n."""
    haystack = _normalize(f"{title} {domain} {description} {control_id}")
    collected: list[str] = []
    used_fallback = False

    for patterns, questions in QUESTION_BANK:
        if "__FALLBACK__" in patterns:
            continue
        if any(p in haystack for p in patterns):
            for q in questions:
                if q not in collected:
                    collected.append(q)
                    if len(collected) >= n:
                        return collected

    # Always fill to n with fallback if needed
    if len(collected) < n:
        for _p, fallback_qs in QUESTION_BANK:
            if "__FALLBACK__" in _p:
                for q in fallback_qs:
                    if q not in collected:
                        collected.append(q)
                        if len(collected) >= n:
                            break
    return collected[:n]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    frameworks = db.execute("""
        SELECT id, short_name, name, category
        FROM compliance_frameworks
        WHERE is_active = 1
        ORDER BY category, name
    """).fetchall()

    index_entries = []

    for fw in frameworks:
        controls = db.execute("""
            SELECT control_id, title, domain, description
            FROM framework_controls
            WHERE framework_id = ?
            ORDER BY domain, control_id
        """, (fw["id"],)).fetchall()

        if not controls:
            continue

        # Group by domain
        domains: dict[str, list] = {}
        for c in controls:
            dom = c["domain"] or "General"
            domains.setdefault(dom, []).append(c)

        out = {
            "framework": fw["name"],
            "short_name": fw["short_name"],
            "category": fw["category"],
            "total_controls": len(controls),
            "domains": {}
        }

        for dom, ctrls in domains.items():
            out["domains"][dom] = []
            for c in ctrls:
                questions = _pick_questions(
                    c["control_id"], c["title"] or "",
                    c["domain"] or "", c["description"] or ""
                )
                out["domains"][dom].append({
                    "control_id":  c["control_id"],
                    "title":       c["title"] or "",
                    "questions":   questions,
                })

        fname = f"{fw['short_name']}.yaml"
        fpath = OUT_DIR / fname
        with open(fpath, "w") as f:
            yaml.dump(out, f, default_flow_style=False, allow_unicode=True,
                      sort_keys=False, width=120)

        print(f"  [{fw['category']:12s}] {fw['name']:50s} → {fname}  ({len(controls)} controls)")
        index_entries.append({
            "short_name":     fw["short_name"],
            "name":           fw["name"],
            "category":       fw["category"],
            "control_count":  len(controls),
            "domain_count":   len(domains),
            "file":           fname,
        })

    # Write index
    index = {
        "description": (
            "Compliance interview question bank — plain-language questions a non-technical staff member "
            "can ask colleagues to verify compliance with each control requirement. "
            "Generated from BLACKSITE framework_controls table. Review and refine before operational use."
        ),
        "total_frameworks": len(index_entries),
        "total_controls":   sum(e["control_count"] for e in index_entries),
        "frameworks":       index_entries,
    }
    with open(OUT_DIR / "INDEX.yaml", "w") as f:
        yaml.dump(index, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)

    print(f"\nDone. {len(index_entries)} framework files + INDEX.yaml written to {OUT_DIR}/")
    print(f"Total controls covered: {sum(e['control_count'] for e in index_entries)}")


if __name__ == "__main__":
    main()
