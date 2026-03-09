"""
BLACKSITE RBAC Runner — Executor module.

Provides FlowStep, Flow, FlowResult dataclasses and the FlowExecutor class that
runs curated flows and negative tests against the live application.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger("bsv.rbac.executor")

# Status codes that indicate access was denied
DENY_CODES = {403, 401}

# Status codes that indicate an unexpected server error
ERROR_CODES = {500, 502, 503}


@dataclass
class FlowStep:
    """A single step in a flow."""
    action: str                  # navigate|fill|click|submit|select|upload|assert_text|assert_status
    selector: str = ""           # CSS selector (for fill/click/select)
    value: str = ""              # text to fill, option to select, POST body data, or file path
    url: str = ""                # URL to navigate to or POST to
    expected_status: int = 200
    expected_text: str = ""      # text that must appear in the response
    expect_deny: bool = False    # True = this step should be blocked (403/401)
    tolerate_deny: bool = False  # True = 403/401 on this step is OK (not a failure)
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class Flow:
    """A test flow composed of multiple steps."""
    id: str
    name: str
    lens: str                    # which system role lens runs this flow
    steps: list[FlowStep]
    allowed_lenses: list[str]    # lenses expected to pass
    denied_lenses: list[str]     # lenses expected to get 403


@dataclass
class StepResult:
    """Result of a single flow step execution."""
    step_id: str
    action: str
    url: str
    expected_status: int
    observed_status: int
    expected_text: str
    observed_text_snippet: str   # first 200 chars of response body
    expect_deny: bool
    passed: bool
    violation: bool              # True = role got access it should NOT have
    failure: bool                # True = role was denied access it SHOULD have
    duration_ms: float
    error: str = ""
    screenshot_path: str = ""
    snapshot_path: str = ""


@dataclass
class FlowResult:
    """Aggregate result for an entire flow."""
    flow_id: str
    flow_name: str
    lens: str
    platform_role: str
    step_results: list[StepResult]
    passed: bool
    has_violation: bool
    has_failure: bool
    total_steps: int
    passed_steps: int
    duration_ms: float


def _parse_flows_from_config(config: list[dict], lens: str,
                              fixture_ids: dict, run_id: str) -> list[Flow]:
    """
    Parse curated_flows.yaml config into Flow objects for the given lens.
    Substitutes fixture IDs into URLs and values.
    """
    flows: list[Flow] = []
    for fc in config:
        flow_id = fc.get("id", "")
        name = fc.get("name", flow_id)
        allowed = fc.get("allowed_lenses", [])
        denied = fc.get("denied_lenses", [])

        steps_raw = fc.get("steps", [])
        steps: list[FlowStep] = []
        for sr in steps_raw:
            url = _substitute(sr.get("url", ""), fixture_ids, run_id)
            value = _substitute(sr.get("value", ""), fixture_ids, run_id)
            steps.append(FlowStep(
                action=sr.get("action", "navigate"),
                selector=sr.get("selector", ""),
                value=value,
                url=url,
                expected_status=sr.get("expected_status", 200),
                expected_text=sr.get("expected_text", ""),
                expect_deny=sr.get("expect_deny", False),
            ))

        flows.append(Flow(
            id=flow_id,
            name=name,
            lens=lens,
            steps=steps,
            allowed_lenses=allowed,
            denied_lenses=denied,
        ))
    return flows


def _substitute(text: str, fixture_ids: dict, run_id: str) -> str:
    """Replace {SYSTEM_ID}, {RISK_ID}, {POAM_ID}, {POAM_CLOSED_ID}, {BCDR_ID}, {RUN_ID} tokens."""
    if not text:
        return text
    systems = fixture_ids.get("systems", {})
    risks = fixture_ids.get("risks", {})
    poam = fixture_ids.get("poam", {})
    bcdr = fixture_ids.get("bcdr", {})

    text = text.replace("{SYSTEM_ID}", systems.get("alpha_id") or "00000000-0000-0000-0000-000000000001")
    text = text.replace("{SYSTEM_B}", systems.get("bravo_id") or "00000000-0000-0000-0000-000000000002")
    text = text.replace("{RISK_ID}", risks.get("test_risk_id") or "00000000-0000-0000-0000-000000000010")
    text = text.replace("{POAM_ID}", poam.get("test_poam_id") or "00000000-0000-0000-0000-000000000020")
    text = text.replace("{POAM_CLOSED_ID}", poam.get("closed_poam_id") or "00000000-0000-0000-0000-000000000021")
    text = text.replace("{BCDR_ID}", bcdr.get("test_event_id") or "1")
    text = text.replace("{RUN_ID}", run_id)
    return text


class FlowExecutor:
    """Executes flows against the live BLACKSITE application using a Playwright page."""

    def __init__(self, base_url: str, output_dir: Path, run_id: str):
        self.base_url = base_url.rstrip("/")
        self.output_dir = output_dir
        self.run_id = run_id
        self.screenshots_dir = output_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def _full_url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return self.base_url + path

    async def _navigate(self, page, url: str) -> tuple[int, str]:
        """Navigate to a URL and return (status_code, body_snippet)."""
        try:
            response = await page.goto(self._full_url(url),
                                        wait_until="domcontentloaded",
                                        timeout=20000)
            status = response.status if response else 0
            content = await page.content()
            snippet = content[:500] if content else ""
            return status, snippet
        except Exception as exc:
            log.debug("Navigate error for %s: %s", url, exc)
            return 0, str(exc)[:200]

    async def _post_form(self, page, url: str, form_data: str) -> tuple[int, str]:
        """
        Submit a POST request with URL-encoded form data using fetch().
        Returns (status_code, body_snippet).
        """
        full_url = self._full_url(url)
        # Encode form data and get CSRF if needed
        js = f"""
        async () => {{
            const resp = await fetch({json.dumps(full_url)}, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                body: {json.dumps(form_data)},
                redirect: 'follow',
            }});
            const text = await resp.text();
            return {{ status: resp.status, body: text.substring(0, 500) }};
        }}
        """
        try:
            result = await page.evaluate(js)
            return result.get("status", 0), result.get("body", "")
        except Exception as exc:
            log.debug("POST fetch error for %s: %s", url, exc)
            return 0, str(exc)[:200]

    async def _capture_failure(self, page, prefix: str) -> tuple[str, str]:
        """Capture screenshot and HTML snapshot. Returns (screenshot_path, snapshot_path)."""
        base_name = f"{prefix}_{int(time.time() * 1000)}"
        ss_path = str(self.screenshots_dir / f"{base_name}.png")
        html_path = str(self.screenshots_dir / f"{base_name}.html")
        try:
            await page.screenshot(path=ss_path, full_page=False, timeout=5000)
        except Exception:
            ss_path = ""
        try:
            content = await page.content()
            Path(html_path).write_text(content, encoding="utf-8")
        except Exception:
            html_path = ""
        return ss_path, html_path

    async def run_step(self, page, step: FlowStep, lens: str,
                       platform_role: str) -> StepResult:
        """Execute a single flow step and return a StepResult."""
        start = time.perf_counter()
        observed_status = 0
        observed_text = ""
        error = ""
        screenshot = ""
        snapshot = ""

        try:
            if step.action in ("navigate", "assert_status", "assert_text"):
                observed_status, observed_text = await self._navigate(page, step.url)

            elif step.action == "submit":
                # POST the URL with form_data in step.value
                if step.value:
                    observed_status, observed_text = await self._post_form(
                        page, step.url, step.value)
                else:
                    # GET then POST (form submission flow)
                    observed_status, observed_text = await self._navigate(page, step.url)

            elif step.action == "fill":
                if step.selector:
                    try:
                        await page.wait_for_selector(step.selector, timeout=15000)
                        await page.fill(step.selector, step.value, timeout=10000)
                        observed_status = 200
                        observed_text = "fill ok"
                    except Exception as e:
                        error = f"fill failed: {e}"
                        observed_status = 0

            elif step.action == "select":
                if step.selector:
                    try:
                        # Wait for element to be present and visible before selecting.
                        # Previously used flat 5000ms timeout with no pre-wait —
                        # caused 16 recurring failures on select[name='likelihood']
                        # when the form hadn't finished rendering. Fixed 2026-03-01.
                        await page.wait_for_selector(step.selector, state="visible", timeout=15000)
                        await page.select_option(step.selector, value=step.value, timeout=15000)
                        observed_status = 200
                        observed_text = "select ok"
                    except Exception as e:
                        error = f"select failed: {e}"
                        observed_status = 0

            elif step.action == "click":
                if step.selector:
                    try:
                        await page.wait_for_selector(step.selector, state="visible", timeout=15000)
                        await page.click(step.selector, timeout=10000)
                        observed_status = 200
                        observed_text = "click ok"
                    except Exception as e:
                        error = f"click failed: {e}"
                        observed_status = 0

            elif step.action == "upload":
                # File upload: skip actual file upload in basic runner
                # Just verify the upload form is accessible
                if step.url:
                    observed_status, observed_text = await self._navigate(page, step.url)
                else:
                    observed_status = 200
                    observed_text = "upload skipped"

            else:
                error = f"Unknown action: {step.action}"
                observed_status = 0

        except Exception as exc:
            error = str(exc)[:300]
            observed_status = 0

        duration_ms = (time.perf_counter() - start) * 1000

        # Determine pass/fail/violation
        # A violation is: expect_deny=True but got 200 (role got access it shouldn't have)
        # A failure is: expect_deny=False but got 403/401 (role was blocked when it shouldn't be)
        # Note: 404 (not found) and 405 (method not allowed) are NOT violations —
        #       the role did not gain access; the resource/method simply doesn't exist.
        _NOT_VIOLATION_CODES = {404, 405}
        if step.action in ("fill", "select", "click") and not error:
            # UI interaction steps: pass if no error
            passed = not bool(error)
            violation = False
            failure = bool(error)
        else:
            violation = (step.expect_deny and
                         observed_status not in DENY_CODES and
                         observed_status not in _NOT_VIOLATION_CODES and
                         observed_status > 0)
            failure = (not step.expect_deny and
                       not step.tolerate_deny and
                       observed_status in DENY_CODES)

            # Check expected_text if provided
            text_ok = True
            if step.expected_text and observed_text:
                text_ok = step.expected_text.lower() in observed_text.lower()

            # Check expected_status
            if step.expected_status and observed_status:
                status_ok = observed_status == step.expected_status
            else:
                status_ok = True

            passed = not violation and not failure and text_ok and not error

        # Capture artifacts on violation or failure
        if violation or failure or error:
            prefix = f"{platform_role}_{lens}_{step.step_id}"
            screenshot, snapshot = await self._capture_failure(page, prefix)

        return StepResult(
            step_id=step.step_id,
            action=step.action,
            url=step.url,
            expected_status=step.expected_status,
            observed_status=observed_status,
            expected_text=step.expected_text,
            observed_text_snippet=observed_text[:200],
            expect_deny=step.expect_deny,
            passed=passed,
            violation=violation,
            failure=failure,
            duration_ms=duration_ms,
            error=error,
            screenshot_path=screenshot,
            snapshot_path=snapshot,
        )

    async def run_flow(self, page, flow: Flow, current_lens: str,
                       platform_role: str) -> FlowResult:
        """Run all steps in a flow and return aggregate FlowResult."""
        start = time.perf_counter()
        step_results: list[StepResult] = []

        log.info("  Running flow [%s] as lens=%s", flow.id, current_lens)

        for step in flow.steps:
            result = await self.run_step(page, step, current_lens, platform_role)
            step_results.append(result)

            if result.violation:
                log.warning("  VIOLATION: flow=%s step=%s lens=%s url=%s got=%d (expected deny)",
                            flow.id, step.step_id, current_lens, step.url, result.observed_status)
            elif result.failure:
                log.warning("  FAILURE: flow=%s step=%s lens=%s url=%s got=%d (expected %d)",
                            flow.id, step.step_id, current_lens, step.url,
                            result.observed_status, step.expected_status)
            elif result.error:
                log.debug("  ERROR: flow=%s step=%s: %s", flow.id, step.step_id, result.error)

        duration_ms = (time.perf_counter() - start) * 1000
        has_violation = any(r.violation for r in step_results)
        has_failure = any(r.failure for r in step_results)
        passed_steps = sum(1 for r in step_results if r.passed)

        return FlowResult(
            flow_id=flow.id,
            flow_name=flow.name,
            lens=current_lens,
            platform_role=platform_role,
            step_results=step_results,
            passed=not has_violation and not has_failure,
            has_violation=has_violation,
            has_failure=has_failure,
            total_steps=len(step_results),
            passed_steps=passed_steps,
            duration_ms=duration_ms,
        )

    async def run_curated_flows(self, page, curated_config: list[dict],
                                 fixture_ids: dict, lens: str,
                                 platform_role: str,
                                 skip_denied: bool = False) -> list[FlowResult]:
        """
        Run all curated flows that are relevant to the current lens.
        Flows are relevant if:
          - lens is in allowed_lenses (expect pass)
          - lens is in denied_lenses (expect deny)
        Flows where lens is neither allowed nor denied are skipped.

        skip_denied: when True, flows where this lens is only in denied_lenses
          (not in allowed_lenses) are skipped entirely.  Use this for admin
          personas whose user bypasses all role guards via _is_admin(), because
          those users cannot produce meaningful 403 responses for denied flows.
        """
        results: list[FlowResult] = []

        for fc in curated_config:
            allowed = fc.get("allowed_lenses", [])
            denied = fc.get("denied_lenses", [])

            if lens not in allowed and lens not in denied:
                continue  # not relevant to this lens

            # Admin bypass: skip flows where this lens is denied but we can't get a 403
            if skip_denied and lens in denied and lens not in allowed:
                log.debug("  skip_denied: skipping flow %s (lens=%s in denied_lenses, admin user)",
                          fc.get("id", "?"), lens)
                continue

            steps_raw = fc.get("steps", [])

            # Detect flow type: navigate-only vs mixed (navigate + submit)
            # Navigate-only flows: the GET itself is the RBAC gate (e.g. /admin/siem)
            # Mixed flows: the POST/submit is the RBAC gate; the navigate is just prep
            has_submit_steps = any(
                s.get("action", "navigate") in ("submit", "upload")
                for s in steps_raw
            )

            steps: list[FlowStep] = []
            for sr in steps_raw:
                url = _substitute(sr.get("url", ""), fixture_ids, self.run_id)
                value = _substitute(sr.get("value", ""), fixture_ids, self.run_id)
                action = sr.get("action", "navigate")
                expect_deny = sr.get("expect_deny", False)
                tolerate_deny = False

                if lens in denied and not sr.get("expect_deny", False):
                    if action in ("submit", "upload"):
                        # POST/upload: always the RBAC boundary → expect deny
                        expect_deny = True
                        expected_status = 403
                    elif action == "navigate" and not has_submit_steps:
                        # Navigate-only flow: the GET IS the RBAC test → expect deny
                        expect_deny = True
                        expected_status = 403
                    else:
                        # navigate/fill/select in a mixed flow: preparatory steps.
                        # Don't override expect_deny, but tolerate a 403 if the route
                        # also happens to guard the GET (e.g. /observations/new).
                        tolerate_deny = True
                        expected_status = sr.get("expected_status", 200)
                else:
                    expected_status = sr.get("expected_status", 200)

                # For denied submit steps with no POST body, inject a minimal form value
                # to force an actual POST (instead of falling back to a GET → 405).
                if expect_deny and action == "submit" and not value:
                    value = "_rbac_test=1"

                steps.append(FlowStep(
                    action=action,
                    selector=sr.get("selector", ""),
                    value=value,
                    url=url,
                    expected_status=expected_status,
                    expected_text=sr.get("expected_text", ""),
                    expect_deny=expect_deny,
                    tolerate_deny=tolerate_deny,
                ))

            flow = Flow(
                id=fc.get("id", "unknown"),
                name=fc.get("name", ""),
                lens=lens,
                steps=steps,
                allowed_lenses=allowed,
                denied_lenses=denied,
            )
            result = await self.run_flow(page, flow, lens, platform_role)
            results.append(result)

        return results

    async def run_negative_tests(self, page, current_lens: str,
                                  platform_role: str,
                                  all_routes: list[dict],
                                  fixture_ids: dict) -> list[FlowResult]:
        """
        For POST routes where current_lens is NOT in required_roles:
        GET/POST the route and verify it returns 403 (not 200).

        A 200 on a denied route = PRIVILEGE VIOLATION.

        Only tests POST routes that have explicit role guards. Skips routes
        with no guards (they may be admin-only via Remote-User header logic).
        """
        results: list[FlowResult] = []

        # POST routes with explicit role guards
        post_routes = [r for r in all_routes
                       if r["method"] == "POST" and r["required_roles"]]

        for route in post_routes:
            required = route["required_roles"]
            if current_lens in required or "admin" in required:
                continue  # this lens IS allowed — not a negative test

            # current_lens should be denied — test that it gets 403
            path = route["path"]

            # Substitute path params with fixture IDs
            test_path = _substitute(
                path.replace("{system_id}", "{SYSTEM_ID}")
                    .replace("{item_id}", "{POAM_ID}")
                    .replace("{risk_id}", "{RISK_ID}")
                    .replace("{assessment_id}", "00000000-test-test-test-000000000001")
                    .replace("{event_id}", "{BCDR_ID}")
                    .replace("{ctrl_id}", "ac-1")
                    .replace("{step}", "prepare")
                    .replace("{username}", "testuser")
                    .replace("{sub_id}", "00000000-test-test-test-000000000002")
                    .replace("{art_id}", "00000000-test-test-test-000000000003")
                    .replace("{conn_id}", "1")
                    .replace("{item_id}", "1")
                    .replace("{ev_id}", "1"),
                fixture_ids, self.run_id
            )

            # Skip paths that still have unresolved params (complex dynamic routes)
            if "{" in test_path:
                continue

            flow_id = f"neg_{route['function']}_{current_lens}"
            step = FlowStep(
                action="submit",
                url=test_path,
                value="_rbac_negative_test=1",
                expected_status=403,
                expect_deny=True,
            )
            flow = Flow(
                id=flow_id,
                name=f"Negative: {route['method']} {path} as {current_lens}",
                lens=current_lens,
                steps=[step],
                allowed_lenses=[],
                denied_lenses=[current_lens],
            )
            result = await self.run_flow(page, flow, current_lens, platform_role)
            results.append(result)

        log.info("Ran %d negative tests for lens=%s", len(results), current_lens)
        return results


def flows_from_config(curated_config: list[dict], fixture_ids: dict,
                       run_id: str, lens: str) -> list[Flow]:
    """Helper: parse curated config into Flow objects for a specific lens."""
    return _parse_flows_from_config(curated_config, lens, fixture_ids, run_id)
