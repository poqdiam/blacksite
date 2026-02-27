"""
BLACKSITE — Email sender (Gmail STARTTLS via system credentials file).

Credentials are stored in /etc/blacksite/email.conf (root:root, 600).
They are NOT in config.yaml, NOT in the project directory, NOT synced to Iapetus.
Run: sudo bash /home/graycat/scripts/setup-blacksite-email.sh <gmail> <app-password>
"""

from __future__ import annotations

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, Dict, List

log = logging.getLogger("blacksite.mailer")

_SYSTEM_EMAIL_CONF = "/etc/blacksite/email.conf"


def _load_system_email_creds() -> tuple:
    """
    Read Gmail credentials from /etc/blacksite/email.conf (root-owned, 600).
    Returns (gmail_user, gmail_pass) or ("", "") if not configured.
    """
    try:
        vals: Dict[str, str] = {}
        with open(_SYSTEM_EMAIL_CONF) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    vals[k.strip()] = v.strip()
        return vals.get("GMAIL_USER", ""), vals.get("GMAIL_PASS", "")
    except OSError:
        return "", ""


def _smtp_send(config: dict, msg: MIMEMultipart) -> bool:
    """Send a pre-built MIME message. Returns True on success."""
    gmail_user, gmail_pass = _load_system_email_creds()
    if not gmail_user or not gmail_pass:
        log.warning(
            "Email credentials not found in %s — skipping. "
            "Run: sudo bash /home/graycat/scripts/setup-blacksite-email.sh",
            _SYSTEM_EMAIL_CONF,
        )
        return False
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_user, gmail_pass)
            server.sendmail(str(msg["From"]), [str(msg["To"])], msg.as_string())
        log.info("Email sent to %s — subject: %s", msg["To"], msg["Subject"])
        return True
    except Exception as e:
        log.error("Email send failed: %s", e)
        return False


def _build_html(assessment_data: dict, quiz_data: Optional[dict]) -> str:
    """Build the HTML email body from assessment data."""
    name           = assessment_data.get("candidate_name", "Candidate")
    filename       = assessment_data.get("filename", "SSP")
    ssp_score      = assessment_data.get("ssp_score", 0)
    quiz_score     = assessment_data.get("quiz_score", 0)
    combined_score = assessment_data.get("combined_score", 0)
    is_allstar     = assessment_data.get("is_allstar", False)
    grade_counts   = assessment_data.get("grade_counts", {})
    ctrl_results   = assessment_data.get("top_issues", [])

    star_html = """
    <div style="background:#ffd700;color:#000;padding:12px 20px;border-radius:6px;
                margin:16px 0;font-weight:bold;font-size:1.1em;text-align:center;">
        ★ ALL STAR — This candidate meets the combined threshold for recruitment.
    </div>""" if is_allstar else ""

    issues_rows = ""
    for r in ctrl_results[:10]:
        grade   = r.get("grade", "?")
        color   = {"COMPLETE": "#00c853", "PARTIAL": "#ffb300",
                   "INSUFFICIENT": "#f44336", "NOT_FOUND": "#9e9e9e"}.get(grade, "#888")
        issues  = "; ".join(r.get("issues", [])[:2])
        issues_rows += f"""
        <tr>
            <td style="padding:6px 10px;font-family:monospace;white-space:nowrap">{r.get("control_id","").upper()}</td>
            <td style="padding:6px 10px">{r.get("control_title","")}</td>
            <td style="padding:6px 10px;color:{color};font-weight:bold">{grade}</td>
            <td style="padding:6px 10px;font-size:0.85em;color:#ccc">{issues}</td>
        </tr>"""

    quiz_html = ""
    if quiz_data:
        quiz_html = f"""
        <h3 style="color:#00ffcc;margin-top:24px">Quiz Results</h3>
        <p>Score: <strong>{quiz_data.get('score',0)}/{quiz_data.get('total',20)}</strong>
           ({quiz_data.get('percentage',0):.1f}%)</p>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="background:#0a0a0f;color:#e0e0e0;font-family:Inter,Roboto,sans-serif;
             padding:24px;max-width:800px;margin:auto">
  <div style="border-bottom:2px solid #00ffcc;padding-bottom:12px;margin-bottom:20px">
    <span style="font-size:1.4em;font-weight:900;letter-spacing:2px;color:#fff">BLACKSITE</span>
    <span style="margin-left:12px;color:#888;font-size:0.9em">by TheKramerica</span>
  </div>

  <h2 style="color:#fff">Assessment Report — {name}</h2>
  <p style="color:#aaa">File: <code>{filename}</code></p>

  {star_html}

  <table style="border-collapse:collapse;margin:16px 0;width:100%">
    <tr>
      <td style="padding:10px 16px;background:#1a1a2e;border-radius:4px 0 0 4px;text-align:center">
        <div style="font-size:2em;font-weight:bold;color:#00ffcc">{ssp_score:.1f}</div>
        <div style="font-size:0.75em;color:#aaa">SSP SCORE</div>
      </td>
      <td style="padding:10px 16px;background:#1a1a2e;text-align:center;border-left:1px solid #333">
        <div style="font-size:2em;font-weight:bold;color:#00ffcc">{quiz_score:.1f}</div>
        <div style="font-size:0.75em;color:#aaa">QUIZ SCORE</div>
      </td>
      <td style="padding:10px 16px;background:#1a1a2e;border-radius:0 4px 4px 0;text-align:center;border-left:1px solid #333">
        <div style="font-size:2em;font-weight:bold;color:#ffd700">{combined_score:.1f}</div>
        <div style="font-size:0.75em;color:#aaa">COMBINED</div>
      </td>
    </tr>
  </table>

  <h3 style="color:#00ffcc">Control Coverage</h3>
  <p>
    Complete: <strong style="color:#00c853">{grade_counts.get('COMPLETE',0)}</strong> &nbsp;|&nbsp;
    Partial: <strong style="color:#ffb300">{grade_counts.get('PARTIAL',0)}</strong> &nbsp;|&nbsp;
    Insufficient: <strong style="color:#f44336">{grade_counts.get('INSUFFICIENT',0)}</strong> &nbsp;|&nbsp;
    Not Found: <strong style="color:#9e9e9e">{grade_counts.get('NOT_FOUND',0)}</strong>
  </p>

  <h3 style="color:#00ffcc">Top Issues (Lowest-Scoring Controls)</h3>
  <table style="border-collapse:collapse;width:100%;font-size:0.85em">
    <thead>
      <tr style="background:#1a1a2e;color:#aaa">
        <th style="padding:6px 10px;text-align:left">Control</th>
        <th style="padding:6px 10px;text-align:left">Title</th>
        <th style="padding:6px 10px;text-align:left">Grade</th>
        <th style="padding:6px 10px;text-align:left">Issues</th>
      </tr>
    </thead>
    <tbody>{issues_rows}</tbody>
  </table>

  {quiz_html}

  <p style="margin-top:32px;font-size:0.75em;color:#555">
    This is an AI-generated baseline assessment. Proctor review is required before
    any final determination.
  </p>
  <p style="font-size:0.7em;color:#333">BLACKSITE — TheKramerica | daniel@thekramerica.com</p>
</body>
</html>"""


def send_report(
    config: dict,
    candidate_name: str,
    assessment_data: dict,
    quiz_data: Optional[dict] = None,
    attachment_path: Optional[Path] = None,
) -> bool:
    """
    Send an assessment report email via Gmail STARTTLS.
    Recipient is config.email.to_address (Dan).
    Returns True on success, False on failure.
    """
    email_cfg = config.get("email", {})
    if not email_cfg.get("enabled", False):
        log.info("Email disabled in config — skipping send.")
        return False

    from_addr = email_cfg.get("from_address", "BLACKSITE <daniel@thekramerica.com>")
    to_addr   = email_cfg.get("to_address", "daniel@thekramerica.com")

    subject_star = " ★ ALL STAR" if assessment_data.get("is_allstar") else ""
    subject = f"[BLACKSITE] Assessment: {candidate_name}{subject_star}"

    html_body = _build_html(
        {**assessment_data, "candidate_name": candidate_name},
        quiz_data
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html"))

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={Path(attachment_path).name}")
        msg.attach(part)

    return _smtp_send(config, msg)


def forward_assessment(
    config: dict,
    assessment,
    candidate_name: str,
    employee: dict,
    review_note: str = "",
    top_issues: Optional[List[dict]] = None,
) -> bool:
    """
    Forward an assessment to an employee with a summary and link to the full report.

    Args:
        config:         App config dict
        assessment:     Assessment ORM object
        candidate_name: Name of the candidate who submitted the SSP
        employee:       Dict with keys: name, email (from config.employees)
        review_note:    Optional admin note to include
        top_issues:     List of lowest-scoring controls

    Returns True on success, False on failure.
    """
    email_cfg = config.get("email", {})
    if not email_cfg.get("enabled", False):
        log.info("Email disabled in config — skipping forward.")
        return False

    employee_email = employee.get("email", "")
    employee_name  = employee.get("name", employee.get("username", "Team"))
    if not employee_email:
        log.warning("forward_assessment: no email address for employee %s", employee)
        return False

    from_addr  = email_cfg.get("from_address", "BLACKSITE <daniel@thekramerica.com>")
    base_url   = config.get("app", {}).get("base_url", "https://blacksite.borisov.network")
    results_url = f"{base_url}/results/{assessment.id}"

    ssp_score   = getattr(assessment, "ssp_score", 0) or 0
    quiz_score  = getattr(assessment, "quiz_score", 0) or 0
    combined    = getattr(assessment, "combined_score", 0) or 0
    is_allstar  = getattr(assessment, "is_allstar", False)
    filename    = getattr(assessment, "filename", "SSP")

    star_banner = """
    <div style="background:#ffd700;color:#000;padding:10px 16px;border-radius:4px;
                margin:12px 0;font-weight:bold;text-align:center;">
      ★ ALL STAR CANDIDATE
    </div>""" if is_allstar else ""

    note_block = ""
    if review_note and review_note.strip():
        note_block = f"""
    <div style="margin:16px 0;padding:12px 16px;background:#1a1a2e;
                border-left:3px solid #00ffcc;border-radius:0 4px 4px 0">
      <div style="font-size:0.72em;color:#888;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">
        Admin Note
      </div>
      <div style="color:#e0e0e0;font-size:0.9em">{review_note}</div>
    </div>"""

    issues_rows = ""
    for r in (top_issues or [])[:5]:
        grade  = r.get("grade", "?")
        color  = {"COMPLETE": "#00c853", "PARTIAL": "#ffb300",
                  "INSUFFICIENT": "#f44336", "NOT_FOUND": "#9e9e9e"}.get(grade, "#888")
        issues = "; ".join(str(x) for x in r.get("issues", [])[:2] if x)
        issues_rows += f"""
        <tr>
          <td style="padding:5px 8px;font-family:monospace;font-size:0.8em">{r.get("control_id","").upper()}</td>
          <td style="padding:5px 8px;font-size:0.8em">{r.get("control_title","")}</td>
          <td style="padding:5px 8px;color:{color};font-weight:bold;font-size:0.8em">{grade}</td>
          <td style="padding:5px 8px;font-size:0.75em;color:#ccc">{issues}</td>
        </tr>"""

    issues_section = ""
    if issues_rows:
        issues_section = f"""
    <h3 style="color:#00ffcc;margin-top:20px">Top Issues</h3>
    <table style="border-collapse:collapse;width:100%">
      <thead><tr style="background:#1a1a2e;color:#888">
        <th style="padding:5px 8px;text-align:left">Control</th>
        <th style="padding:5px 8px;text-align:left">Title</th>
        <th style="padding:5px 8px;text-align:left">Grade</th>
        <th style="padding:5px 8px;text-align:left">Issues</th>
      </tr></thead>
      <tbody>{issues_rows}</tbody>
    </table>"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="background:#0a0a0f;color:#e0e0e0;font-family:Inter,Roboto,sans-serif;
             padding:24px;max-width:800px;margin:auto">
  <div style="border-bottom:2px solid #00ffcc;padding-bottom:12px;margin-bottom:20px">
    <span style="font-size:1.4em;font-weight:900;letter-spacing:2px;color:#fff">BLACKSITE</span>
    <span style="margin-left:12px;color:#888;font-size:0.9em">Assessment Forwarded for Review</span>
  </div>

  <p style="color:#aaa">Hi {employee_name},</p>
  <p>An SSP assessment has been forwarded to you for review.</p>

  <h2 style="color:#fff">Candidate: {candidate_name}</h2>
  <p style="color:#aaa;font-size:0.85em">File: <code>{filename}</code></p>

  {star_banner}

  <table style="border-collapse:collapse;margin:16px 0;width:100%">
    <tr>
      <td style="padding:10px 16px;background:#1a1a2e;border-radius:4px 0 0 4px;text-align:center">
        <div style="font-size:2em;font-weight:bold;color:#00ffcc">{ssp_score:.1f}</div>
        <div style="font-size:0.72em;color:#aaa;letter-spacing:1px">SSP</div>
      </td>
      <td style="padding:10px 16px;background:#1a1a2e;text-align:center;border-left:1px solid #333">
        <div style="font-size:2em;font-weight:bold;color:#00ffcc">{quiz_score:.1f}</div>
        <div style="font-size:0.72em;color:#aaa;letter-spacing:1px">QUIZ</div>
      </td>
      <td style="padding:10px 16px;background:#1a1a2e;border-radius:0 4px 4px 0;text-align:center;border-left:1px solid #333">
        <div style="font-size:2em;font-weight:bold;color:#ffd700">{combined:.1f}</div>
        <div style="font-size:0.72em;color:#aaa;letter-spacing:1px">COMBINED</div>
      </td>
    </tr>
  </table>

  {note_block}
  {issues_section}

  <div style="margin-top:24px">
    <a href="{results_url}"
       style="display:inline-block;background:#00ffcc;color:#000;padding:12px 24px;
              border-radius:4px;font-weight:700;letter-spacing:1px;text-decoration:none">
      View Full Report →
    </a>
  </div>

  <p style="margin-top:32px;font-size:0.72em;color:#555">
    BLACKSITE — TheKramerica | This is an automated notification.
  </p>
</body>
</html>"""

    subject = f"[BLACKSITE] Assessment Review: {candidate_name}"
    if is_allstar:
        subject += " ★"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = employee_email
    msg.attach(MIMEText(html_body, "html"))

    return _smtp_send(config, msg)
