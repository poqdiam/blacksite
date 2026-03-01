"""
BLACKSITE RBAC Runner — RunnerEngine class and asyncio entry point.

The engine drives the full test cycle:
  1. Load config (roles.yaml, curated_flows.yaml, fixtures.yaml)
  2. For each platform role persona (filtered by --role):
     a. Launch Playwright browser
     b. Login once
     c. For each lens the persona can access (filtered by --lens):
        - switch_lens()
        - discover nav links from the rendered sidebar
        - run curated flows for this lens
        - run negative tests for this lens
        - exit lens
     d. logout
  3. Write summary.json
  4. Post Telegram notification
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger("bsv.rbac.runner")

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = Path(__file__).parent / "config"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "rbac-runs"
MAIN_PY = PROJECT_ROOT / "app" / "main.py"


def _load_yaml(path: Path) -> dict | list:
    if not path.exists():
        log.warning("Config file not found: %s", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class RunnerEngine:
    def __init__(self, args):
        self.base_url = (
            os.environ.get("BSV_BASE_URL") or
            getattr(args, "base_url", "http://127.0.0.1:8100")
        ).rstrip("/")

        self.headed = getattr(args, "headed", False)
        self.silent = getattr(args, "silent", False)
        self.role_filter = getattr(args, "role", None)
        self.lens_filter = getattr(args, "lens", None)
        self.no_negative = getattr(args, "no_negative", False)
        self.local_mode = (
            os.environ.get("BSV_LOCAL_MODE", "0") == "1" or
            getattr(args, "local_mode", False)
        )
        self.authelia_url = os.environ.get("BSV_AUTHELIA_URL", "http://127.0.0.1:9091")

        # Run ID
        given_id = getattr(args, "run_id", None)
        self.run_id = given_id or datetime.now(timezone.utc).strftime("RUN-%Y%m%d-%H%M%S")

        # Output directory
        output_base = Path(getattr(args, "output_dir", None) or DEFAULT_OUTPUT_DIR)
        self.output_dir = output_base / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load config files
        self.roles_config = _load_yaml(CONFIG_DIR / "roles.yaml")
        self.curated_config_raw = _load_yaml(CONFIG_DIR / "curated_flows.yaml")
        self.fixtures = _load_yaml(CONFIG_DIR / "fixtures.yaml")

        # curated_flows.yaml has a top-level "flows" key
        if isinstance(self.curated_config_raw, dict):
            self.curated_flows = self.curated_config_raw.get("flows", [])
        else:
            self.curated_flows = self.curated_config_raw or []

        # Log config load status
        log.info("Run ID: %s", self.run_id)
        log.info("Output: %s", self.output_dir)
        log.info("Base URL: %s", self.base_url)
        log.info("Platform roles: %d", len(self.roles_config.get("platform_roles", {})))
        log.info("Curated flows: %d", len(self.curated_flows))
        fixtures_ready = self.fixtures.get("bootstrapped", False)
        if not fixtures_ready:
            log.warning("Fixtures not bootstrapped — run: python -m tests.rbac.fixtures")

    async def run(self) -> dict:
        """Main run loop. Returns summary dict."""
        from playwright.async_api import async_playwright

        from tests.rbac.personas import build_personas, login, switch_lens, exit_lens, logout
        from tests.rbac.discovery import discover_all_nav, discover_routes_from_main, \
            generate_discovered_flows
        from tests.rbac.executor import FlowExecutor
        from tests.rbac.reporter import Reporter
        from tests.rbac import notifier

        reporter = Reporter(self.output_dir, self.run_id)
        executor = FlowExecutor(self.base_url, self.output_dir, self.run_id)

        # Discover routes from main.py once (static analysis)
        all_routes = discover_routes_from_main(str(MAIN_PY))
        log.info("Static route analysis: %d routes found", len(all_routes))

        # Build personas
        personas = build_personas(
            self.roles_config, self.base_url, self.authelia_url, self.local_mode
        )

        # Filter by --role
        if self.role_filter:
            personas = [p for p in personas if p.platform_role == self.role_filter]
            if not personas:
                log.warning("No persona matches --role=%s", self.role_filter)

        all_flow_results = []
        discovered_flows_all: dict = {}

        async with async_playwright() as pw:
            browser_type = pw.chromium
            launch_kwargs = {
                "headless": not self.headed,
                "args": ["--no-sandbox", "--disable-setuid-sandbox"],
            }

            for persona in personas:
                log.info("=== Persona: %s (user=%s) ===",
                         persona.platform_role, persona.username)

                context = await browser_type.launch_persistent_context(
                    user_data_dir=str(self.output_dir / f"browser_{persona.platform_role}"),
                    **launch_kwargs,
                )
                page = await context.new_page()

                # Set viewport for consistent screenshots
                await page.set_viewport_size({"width": 1280, "height": 900})

                # Login
                logged_in = await login(page, persona)
                if not logged_in:
                    log.error("Login failed for persona %s — skipping", persona.platform_role)
                    await context.close()
                    continue

                # Determine lenses to test
                lenses = persona.lenses
                if self.lens_filter:
                    lenses = [l for l in lenses if l == self.lens_filter]

                if not lenses:
                    log.warning("No lenses to test for persona %s", persona.platform_role)

                for lens in lenses:
                    log.info("--- Lens: %s ---", lens)

                    # Switch to this lens
                    switched = await switch_lens(page, persona, lens)
                    if not switched:
                        log.warning("Could not switch to lens %s — skipping", lens)
                        continue

                    # Discover nav links from the live rendered page
                    nav_links = await discover_all_nav(page, self.base_url, lens)
                    log.info("Nav links discovered for lens %s: %d", lens, len(nav_links))

                    # Generate discovered flows and merge with curated
                    discovered = generate_discovered_flows(
                        self.base_url, lens, nav_links, all_routes
                    )
                    discovered_flows_all[lens] = discovered

                    # Run curated flows for this lens
                    # Admin personas use a user that bypasses role guards via _is_admin(),
                    # so denied-lens flows will never produce a 403 — skip them.
                    admin_username = os.environ.get("BSV_TEST_USER", "dan")
                    skip_denied = (persona.username == admin_username)
                    flow_results = await executor.run_curated_flows(
                        page, self.curated_flows, self.fixtures,
                        lens, persona.platform_role,
                        skip_denied=skip_denied,
                    )
                    all_flow_results.extend(flow_results)
                    for fr in flow_results:
                        reporter.record_flow(fr)

                    # Run discovered nav checks
                    for flow_id, flow_config in discovered.items():
                        disc_steps = flow_config.get("steps", [])
                        from tests.rbac.executor import Flow, FlowStep
                        disc_flow = Flow(
                            id=flow_id,
                            name=flow_config.get("name", flow_id),
                            lens=lens,
                            steps=[FlowStep(**{k: v for k, v in s.items()
                                               if k in FlowStep.__dataclass_fields__})
                                   for s in disc_steps],
                            allowed_lenses=flow_config.get("allowed_lenses", []),
                            denied_lenses=flow_config.get("denied_lenses", []),
                        )
                        disc_result = await executor.run_flow(
                            page, disc_flow, lens, persona.platform_role)
                        all_flow_results.append(disc_result)
                        reporter.record_flow(disc_result)

                    # Run negative tests (unless suppressed)
                    if not self.no_negative:
                        neg_results = await executor.run_negative_tests(
                            page, lens, persona.platform_role,
                            all_routes, self.fixtures
                        )
                        all_flow_results.extend(neg_results)
                        for nr in neg_results:
                            reporter.record_flow(nr)

                    # Exit this lens before moving to the next
                    await exit_lens(page, persona)

                # Logout after testing all lenses for this persona
                await logout(page, persona)
                await context.close()

        # Write discovered flows
        reporter.write_discovered_flows(discovered_flows_all)

        # Write summary
        extra_meta = {
            "base_url":   self.base_url,
            "run_id":     self.run_id,
            "headed":     self.headed,
            "local_mode": self.local_mode,
            "role_filter": self.role_filter,
            "lens_filter": self.lens_filter,
            "routes_discovered": len(all_routes),
        }
        summary = reporter.write_summary(all_flow_results, extra_meta)

        # Post Telegram notification (unless silent)
        if not self.silent:
            await notifier.post_run_summary(
                summary, self.run_id, self.base_url, str(self.output_dir)
            )

        return summary
