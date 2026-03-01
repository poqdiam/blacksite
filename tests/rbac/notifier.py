"""
BLACKSITE RBAC Runner — Telegram notifier module.

Posts run completion summaries to BorisovAlertsBot.

Environment variables:
  BSV_TELEGRAM_TOKEN    Bot token (falls back to TELEGRAM_BOT_TOKEN)
  BSV_TELEGRAM_CHAT_ID  Chat ID (default: 2054649730)
"""
from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timezone

log = logging.getLogger("bsv.rbac.notifier")

TELEGRAM_BOT_TOKEN = (
    os.environ.get("BSV_TELEGRAM_TOKEN") or
    os.environ.get("TELEGRAM_BOT_TOKEN") or
    ""
)
TELEGRAM_CHAT_ID = os.environ.get("BSV_TELEGRAM_CHAT_ID", "2054649730")
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def get_git_hash() -> str:
    """Return the short git hash of the current HEAD commit."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/home/graycat/projects/blacksite",
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _format_message(summary: dict, run_id: str, base_url: str,
                     artifact_dir: str) -> str:
    """Format the Telegram notification message."""
    totals = summary.get("totals", {})
    git_hash = get_git_hash()

    violations = totals.get("violations", 0)
    failures = totals.get("failures", 0)
    steps_passed = totals.get("steps_passed", 0)
    steps_total = totals.get("steps", 0)
    flows_passed = totals.get("flows_passed", 0)
    flows_total = totals.get("flows", 0)
    elapsed = summary.get("elapsed_s", 0)

    # Status emoji
    if violations > 0:
        status_icon = "CRITICAL"
        status_line = f"{violations} RBAC VIOLATION(S) DETECTED"
    elif failures > 0:
        status_icon = "WARN"
        status_line = f"{failures} access failure(s)"
    else:
        status_icon = "OK"
        status_line = "All checks passed"

    started = summary.get("started_at", "")
    finished = summary.get("finished_at", "")

    lines = [
        f"[{status_icon}] BLACKSITE RBAC Run Complete",
        "",
        f"Run ID:   {run_id}",
        f"Commit:   {git_hash}",
        f"App URL:  {base_url}",
        "",
        f"Started:  {started}",
        f"Finished: {finished}",
        f"Elapsed:  {elapsed:.1f}s",
        "",
        f"Status:   {status_line}",
        f"Flows:    {flows_passed}/{flows_total} passed",
        f"Steps:    {steps_passed}/{steps_total} passed",
        f"Violations: {violations}",
        f"Failures:   {failures}",
    ]

    # Top violations
    if summary.get("top_5_violations"):
        lines.append("")
        lines.append("TOP VIOLATIONS:")
        for v in summary["top_5_violations"][:5]:
            lines.append(
                f"  [{v.get('lens','?')} / {v.get('platform_role','?')}] "
                f"{v.get('flow_id','?')} {v.get('url','?')} "
                f"-> got {v.get('observed_status','?')}"
            )

    # Top failures
    if summary.get("top_5_failures"):
        lines.append("")
        lines.append("TOP FAILURES:")
        for f_item in summary["top_5_failures"][:5]:
            lines.append(
                f"  [{f_item.get('lens','?')} / {f_item.get('platform_role','?')}] "
                f"{f_item.get('flow_id','?')} {f_item.get('url','?')} "
                f"-> got {f_item.get('observed_status','?')}"
            )

    lines.append("")
    lines.append(f"Artifacts: {artifact_dir}")

    return "\n".join(lines)


async def post_run_summary(summary: dict, run_id: str,
                            base_url: str, artifact_dir: str) -> bool:
    """
    Post the run completion summary to Telegram via BorisovAlertsBot.

    Returns True if the message was sent successfully.
    """
    token = TELEGRAM_BOT_TOKEN
    if not token:
        log.info("No Telegram token configured — skipping notification")
        return False

    chat_id = TELEGRAM_CHAT_ID
    message = _format_message(summary, run_id, base_url, artifact_dir)

    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "None",
        "disable_web_page_preview": True,
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                log.info("Telegram notification sent (run_id=%s)", run_id)
                return True
            else:
                log.warning("Telegram API returned %d: %s", resp.status_code, resp.text[:200])
                return False
    except ImportError:
        log.warning("httpx not installed — cannot send Telegram notification")
        return False
    except Exception as exc:
        log.error("Telegram notification failed: %s", exc)
        return False


def post_run_summary_sync(summary: dict, run_id: str,
                           base_url: str, artifact_dir: str) -> bool:
    """Synchronous wrapper for post_run_summary (for use in non-async contexts)."""
    token = TELEGRAM_BOT_TOKEN
    if not token:
        log.info("No Telegram token configured — skipping notification")
        return False

    chat_id = TELEGRAM_CHAT_ID
    message = _format_message(summary, run_id, base_url, artifact_dir)

    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "None",
    }

    try:
        import httpx
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                log.info("Telegram notification sent (run_id=%s)", run_id)
                return True
            log.warning("Telegram API returned %d", resp.status_code)
            return False
    except ImportError:
        log.warning("httpx not installed — cannot send Telegram notification")
        return False
    except Exception as exc:
        log.error("Telegram notification failed: %s", exc)
        return False
