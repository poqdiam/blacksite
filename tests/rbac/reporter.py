"""
BLACKSITE RBAC Runner — Reporter module.

Writes:
  - run.jsonl: one JSON object per step result (append-only)
  - summary.json: aggregate stats + top violations and failures
  - screenshots/: PNG screenshots and HTML snapshots captured on failure/violation
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tests.rbac.executor import FlowResult, StepResult

log = logging.getLogger("bsv.rbac.reporter")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Reporter:
    def __init__(self, output_dir: Path, run_id: str):
        self.output_dir = output_dir
        self.run_id = run_id
        self.run_jsonl = output_dir / "run.jsonl"
        self.summary_json = output_dir / "summary.json"
        self.screenshots_dir = output_dir / "screenshots"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self._start_time = time.time()
        self._all_step_results: list[dict] = []

    def record(self, step_result: StepResult, run_meta: dict) -> None:
        """
        Append a step result to run.jsonl.
        Schema:
          run_id, role, lens, flow_id, step_id, action, url,
          expected_status, observed_status, expected_text, observed_text_snippet,
          expect_deny, passed, violation, failure, duration_ms, error,
          screenshot_path, snapshot_path, timestamp
        """
        entry = {
            "run_id":              self.run_id,
            "platform_role":       run_meta.get("platform_role", ""),
            "lens":                run_meta.get("lens", ""),
            "flow_id":             run_meta.get("flow_id", ""),
            "flow_name":           run_meta.get("flow_name", ""),
            "step_id":             step_result.step_id,
            "action":              step_result.action,
            "url":                 step_result.url,
            "expected_status":     step_result.expected_status,
            "observed_status":     step_result.observed_status,
            "expected_text":       step_result.expected_text,
            "observed_text_snippet": step_result.observed_text_snippet,
            "expect_deny":         step_result.expect_deny,
            "passed":              step_result.passed,
            "violation":           step_result.violation,
            "failure":             step_result.failure,
            "duration_ms":         round(step_result.duration_ms, 2),
            "error":               step_result.error,
            "screenshot_path":     step_result.screenshot_path,
            "snapshot_path":       step_result.snapshot_path,
            "timestamp":           _utcnow_iso(),
        }
        self._all_step_results.append(entry)
        try:
            with open(self.run_jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            log.error("Failed to write to run.jsonl: %s", exc)

    def record_flow(self, flow_result: FlowResult) -> None:
        """Record all steps in a FlowResult."""
        run_meta = {
            "platform_role": flow_result.platform_role,
            "lens":          flow_result.lens,
            "flow_id":       flow_result.flow_id,
            "flow_name":     flow_result.flow_name,
        }
        for step_result in flow_result.step_results:
            self.record(step_result, run_meta)

    def write_summary(self, all_flow_results: list[FlowResult],
                       extra_meta: dict = None) -> dict:
        """
        Compute aggregate statistics and write summary.json.

        Returns the summary dict.
        """
        total_steps = sum(fr.total_steps for fr in all_flow_results)
        passed_steps = sum(fr.passed_steps for fr in all_flow_results)
        total_flows = len(all_flow_results)
        passed_flows = sum(1 for fr in all_flow_results if fr.passed)

        violations: list[dict] = []
        failures: list[dict] = []

        for fr in all_flow_results:
            for sr in fr.step_results:
                entry = {
                    "flow_id":   fr.flow_id,
                    "flow_name": fr.flow_name,
                    "lens":      fr.lens,
                    "platform_role": fr.platform_role,
                    "step_id":   sr.step_id,
                    "action":    sr.action,
                    "url":       sr.url,
                    "observed_status": sr.observed_status,
                    "expected_status": sr.expected_status,
                    "error":     sr.error,
                    "screenshot_path": sr.screenshot_path,
                }
                if sr.violation:
                    violations.append(entry)
                if sr.failure:
                    failures.append(entry)

        end_time = time.time()
        elapsed_s = end_time - self._start_time

        summary = {
            "run_id":        self.run_id,
            "started_at":    datetime.fromtimestamp(
                self._start_time, tz=timezone.utc).isoformat(),
            "finished_at":   datetime.fromtimestamp(
                end_time, tz=timezone.utc).isoformat(),
            "elapsed_s":     round(elapsed_s, 2),
            "output_dir":    str(self.output_dir),
            "totals": {
                "flows":        total_flows,
                "flows_passed": passed_flows,
                "flows_failed": total_flows - passed_flows,
                "steps":        total_steps,
                "steps_passed": passed_steps,
                "steps_failed": total_steps - passed_steps,
                "violations":   len(violations),
                "failures":     len(failures),
            },
            "top_5_violations": violations[:5],
            "top_5_failures":   failures[:5],
            "all_violations":   violations,
            "all_failures":     failures,
            **(extra_meta or {}),
        }

        try:
            self.summary_json.write_text(
                json.dumps(summary, indent=2, default=str),
                encoding="utf-8"
            )
            log.info("Summary written to %s", self.summary_json)
        except Exception as exc:
            log.error("Failed to write summary.json: %s", exc)

        # Print a brief report to stdout
        self._print_summary(summary)
        return summary

    def _print_summary(self, summary: dict) -> None:
        """Print a human-readable summary to stdout."""
        totals = summary["totals"]
        print("\n" + "=" * 70)
        print(f"BLACKSITE RBAC Run: {summary['run_id']}")
        print(f"  Elapsed:    {summary['elapsed_s']:.1f}s")
        print(f"  Flows:      {totals['flows_passed']}/{totals['flows']} passed")
        print(f"  Steps:      {totals['steps_passed']}/{totals['steps']} passed")
        print(f"  Violations: {totals['violations']}  (role got access it should NOT have)")
        print(f"  Failures:   {totals['failures']}  (role denied access it SHOULD have)")
        print(f"  Output:     {summary['output_dir']}")

        if summary["top_5_violations"]:
            print("\nTop Violations (RBAC enforcement failures):")
            for v in summary["top_5_violations"]:
                print(f"  [{v['lens']} / {v['platform_role']}] "
                      f"{v['flow_id']} — {v['url']} "
                      f"got {v['observed_status']}")

        if summary["top_5_failures"]:
            print("\nTop Failures (unexpected access denial):")
            for f_item in summary["top_5_failures"]:
                print(f"  [{f_item['lens']} / {f_item['platform_role']}] "
                      f"{f_item['flow_id']} — {f_item['url']} "
                      f"got {f_item['observed_status']}")

        print("=" * 70)

    def write_discovered_flows(self, discovered: dict) -> None:
        """Write discovered_flows.json to the run output directory."""
        out_path = self.output_dir / "discovered_flows.json"
        try:
            out_path.write_text(
                json.dumps(discovered, indent=2, default=str),
                encoding="utf-8"
            )
            log.info("Discovered flows written to %s", out_path)
        except Exception as exc:
            log.error("Failed to write discovered_flows.json: %s", exc)

    async def capture_failure(self, page, prefix: str) -> tuple[str, str]:
        """
        Capture screenshot and HTML snapshot of the current page.
        Returns (screenshot_path, html_snapshot_path).
        """
        base_name = f"{prefix}_{int(time.time() * 1000)}"
        ss_path = str(self.screenshots_dir / f"{base_name}.png")
        html_path = str(self.screenshots_dir / f"{base_name}.html")
        try:
            await page.screenshot(path=ss_path, full_page=False, timeout=5000)
        except Exception as exc:
            log.debug("Screenshot failed: %s", exc)
            ss_path = ""
        try:
            content = await page.content()
            Path(html_path).write_text(content, encoding="utf-8")
        except Exception as exc:
            log.debug("HTML snapshot failed: %s", exc)
            html_path = ""
        return ss_path, html_path
