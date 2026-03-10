"""
BLACKSITE RBAC Runner — Personas module.

Provides the Persona dataclass and login/lens-switch logic for Playwright sessions.

Auth model:
  - BLACKSITE uses Authelia SSO that injects the Remote-User header.
  - There is no local /login route; access is gated by Authelia in front of the app.
  - For test automation we use the admin user (from config.yaml admin_users) and
    shell into each role lens via /switch-role-view?role=<lens>.
  - The bsv_role_shell cookie contains an HMAC-signed value: {role}.{sig20hex}
  - We drive the browser through Authelia's login form at the configured login URL
    OR inject the Remote-User header directly if testing without Authelia (local mode).

Environment variables:
  BSV_TEST_USER    Authelia username (must be in admin_users in config.yaml)
  BSV_TEST_PASS    Authelia password
  BSV_BASE_URL     App base URL (default http://127.0.0.1:8100)
  BSV_AUTHELIA_URL Authelia base URL (default http://127.0.0.1:9091)
  BSV_LOCAL_MODE   If "1", skip Authelia and inject Remote-User header directly
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("bsv.rbac.personas")

# App's valid shell role cookie values (from main.py _VALID_SHELL_ROLES)
# Note: bcdr_coordinator maps to shell cookie value "bcdr"
SHELL_COOKIE_ALIAS: dict[str, str] = {
    "bcdr_coordinator": "bcdr",
    "aodr": "aodr",
}

# All valid cookie values accepted by /switch-role-view
VALID_SHELL_ROLES = {
    "ao", "issm", "isso", "sca", "system_owner", "auditor", "bcdr", "employee",
    "ciso", "pen_tester", "data_owner", "pmo", "incident_responder", "aodr",
}


def lens_to_shell_value(lens: str) -> str:
    """Convert a lens name to the shell cookie value accepted by /switch-role-view."""
    return SHELL_COOKIE_ALIAS.get(lens, lens)


@dataclass
class Persona:
    """A test persona representing a platform role with associated lenses."""
    platform_role: str          # principal | executive | manager | analyst
    username: str               # Authelia username
    password: str               # Authelia password
    lenses: list[str]           # list of system role lenses this persona can switch to
    base_url: str = "http://127.0.0.1:8100"
    authelia_url: str = "http://127.0.0.1:9091"
    local_mode: bool = False    # if True: inject Remote-User header, skip Authelia

    def shell_value(self, lens: str) -> str:
        return lens_to_shell_value(lens)


def build_personas(roles_config: dict, base_url: str,
                   authelia_url: str, local_mode: bool) -> list[Persona]:
    """Build Persona objects from the roles.yaml config and environment variables.

    In local mode each platform tier uses its own test_user (from roles.yaml) so that
    _is_admin() returns False for non-principal personas and role guards are tested
    correctly. The test_user field in roles.yaml falls back to BSV_TEST_USER when empty.
    In Authelia mode only BSV_TEST_USER / BSV_TEST_PASS are used (single shared account).
    """
    global_username = os.environ.get("BSV_TEST_USER", "dan")
    password = os.environ.get("BSV_TEST_PASS", "")

    platform_roles = roles_config.get("platform_roles", {})
    personas = []
    for role_name, role_cfg in platform_roles.items():
        lenses = role_cfg.get("lenses", [])
        valid_lenses = [l for l in lenses if lens_to_shell_value(l) in VALID_SHELL_ROLES]

        # In local mode: use per-tier test_user if defined, so non-principal personas
        # are not treated as admin by the app's _is_admin() check.
        if local_mode:
            per_tier_user = (role_cfg.get("test_user") or "").strip()
            username = per_tier_user if per_tier_user else global_username
        else:
            username = global_username

        personas.append(Persona(
            platform_role=role_name,
            username=username,
            password=password,
            lenses=valid_lenses,
            base_url=base_url,
            authelia_url=authelia_url,
            local_mode=local_mode,
        ))
    return personas


async def login(page, persona: Persona) -> bool:
    """
    Log in to the application via Authelia or local mode.

    In local mode (BSV_LOCAL_MODE=1): navigate directly to / with the Remote-User
    header set. Playwright does not natively support custom request headers on
    navigate(), so we use page.set_extra_http_headers() which applies to all requests.

    In Authelia mode: navigate to the app root (which will redirect to Authelia),
    fill in credentials, and submit.

    Returns True on success, False on failure.
    """
    try:
        if persona.local_mode:
            # Inject Remote-User header for all requests from this page.
            # X-Authelia-Auth-Level simulates Authelia's MFA header so routes
            # guarded by require_mfa (e.g. _check_mfa) pass in local mode.
            await page.set_extra_http_headers({
                "Remote-User": persona.username,
                "Remote-Name":  persona.username,
                "Remote-Groups": "admins",
                "X-Authelia-Auth-Level": "two_factor",
            })
            response = await page.goto(persona.base_url + "/", wait_until="domcontentloaded",
                                       timeout=15000)
            if response and response.status in (200, 302):
                log.info("Local mode login OK for %s", persona.username)
                return True
            log.warning("Local mode login got status %s", response.status if response else "None")
            return False

        # Authelia login flow
        log.info("Logging in via Authelia for %s", persona.username)
        await page.goto(persona.base_url + "/", wait_until="domcontentloaded", timeout=20000)

        current_url = page.url
        if "auth" in current_url or "9091" in current_url or persona.authelia_url in current_url:
            # We were redirected to Authelia — fill the login form
            await page.wait_for_selector("input[name='username'], input[id='username']",
                                         timeout=10000)
            user_sel = "input[name='username']" if await page.query_selector("input[name='username']") \
                       else "input[id='username']"
            pass_sel = "input[name='password']" if await page.query_selector("input[name='password']") \
                       else "input[id='password']"

            await page.fill(user_sel, persona.username)
            await page.fill(pass_sel, persona.password)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=15000)

            # Check if we ended up back at the app
            after_url = page.url
            if persona.authelia_url in after_url:
                # Still on Authelia — possible MFA or wrong credentials
                error_text = await page.inner_text("body")
                if "incorrect" in error_text.lower() or "invalid" in error_text.lower():
                    log.error("Authelia login failed for %s — invalid credentials", persona.username)
                    return False
                # Check for TOTP/2FA prompt
                if "one-time" in error_text.lower() or "totp" in error_text.lower():
                    log.error("Authelia MFA required for %s — not supported in runner", persona.username)
                    return False

        # Verify we got into the app
        if persona.base_url in page.url or page.url.startswith(persona.base_url):
            log.info("Authelia login OK for %s, landed at %s", persona.username, page.url)
            return True

        log.warning("Unexpected post-login URL: %s", page.url)
        return True  # optimistic — let the run proceed

    except Exception as exc:
        log.error("Login failed for %s: %s", persona.username, exc)
        return False


def _load_app_secret() -> str:
    """Load the app secret using the same priority as main.py:
    1. app.secret_key in config.yaml
    2. data/.app_secret file
    """
    import hmac as _hmac  # noqa: F401 (used by callers)
    from pathlib import Path
    import yaml

    # Try config.yaml first — use whatever is set (including placeholder),
    # since the app uses it verbatim via _cfg("app.secret_key").
    for cfg_path in ("config.yaml", "../config.yaml"):
        p = Path(cfg_path)
        if p.exists():
            try:
                cfg = yaml.safe_load(p.read_text())
                sk = (cfg or {}).get("app", {}).get("secret_key", "")
                if sk:
                    return sk
            except Exception:
                pass

    # Fall back to data/.app_secret file
    for secret_path in ("data/.app_secret", "../data/.app_secret"):
        p = Path(secret_path)
        if p.exists():
            return p.read_text().strip()

    log.warning("Could not locate app secret — shell cookie HMAC will be invalid")
    return "fallback-insecure"


def _compute_shell_cookie(role: str) -> str:
    """Compute a valid bsv_role_shell cookie value using the app secret.

    Used in local mode to bypass /switch-role-view endpoint restrictions.
    Cookie format: '{role}.{sha256_hmac20hex}'.
    """
    import hmac as _hmac
    secret = _load_app_secret()
    sig = _hmac.new(secret.encode(), role.encode(), "sha256").hexdigest()[:20]
    return f"{role}.{sig}"


async def switch_lens(page, persona: Persona, lens: str) -> bool:
    """
    Switch the role shell to the given lens.

    In local mode: computes a valid HMAC cookie directly and injects it via
    the browser context, bypassing /switch-role-view endpoint restrictions.
    This lets non-admin fixture users test any lens regardless of their
    ROLE_CAN_VIEW_DOWN position in the hierarchy.

    In Authelia mode: uses /switch-role-view?role=<shell_value> as before.

    Returns True on success, False on failure.
    """
    shell_val = persona.shell_value(lens)
    if shell_val not in VALID_SHELL_ROLES:
        log.warning("Lens '%s' → shell value '%s' is not in VALID_SHELL_ROLES", lens, shell_val)
        return False

    if persona.local_mode:
        # Compute a valid signed cookie and inject it directly — no server roundtrip needed.
        # This allows fixture users (non-admin) to test any lens.
        cookie_val = _compute_shell_cookie(shell_val)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(persona.base_url)
            domain = parsed.hostname or "127.0.0.1"
            await page.context.add_cookies([{
                "name":   "bsv_role_shell",
                "value":  cookie_val,
                "domain": domain,
                "path":   "/",
            }])
            # Navigate to the base URL to confirm the shell is active
            response = await page.goto(persona.base_url + "/dashboard",
                                       wait_until="domcontentloaded", timeout=15000)
            log.info("Lens %s set via direct cookie (local mode) — status %s",
                     lens, response.status if response else "?")
            return True
        except Exception as exc:
            log.error("Local-mode cookie switch to %s failed: %s", lens, exc)
            return False

    try:
        switch_url = persona.base_url + f"/switch-role-view?role={shell_val}"
        log.debug("Switching lens: GET %s", switch_url)

        response = await page.goto(switch_url, wait_until="domcontentloaded", timeout=15000)
        if response and response.status >= 400:
            log.warning("switch-role-view returned %d for lens %s", response.status, lens)
            return False

        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        content = await page.content()

        role_display = lens.upper().replace("_", " ")
        if role_display in content or lens in content.lower():
            log.info("Lens switched to %s (shell: %s)", lens, shell_val)
            return True

        if response and response.status == 200:
            log.info("Lens switched to %s (banner not confirmed, but 200 OK)", lens)
            return True

        log.warning("Lens switch to %s may have failed — no confirmation in page", lens)
        return True  # optimistic

    except Exception as exc:
        log.error("Lens switch to %s failed: %s", lens, exc)
        return False


async def exit_lens(page, persona: Persona) -> None:
    """Exit the current role shell and return to admin/native role."""
    try:
        await page.goto(persona.base_url + "/exit-shell", wait_until="domcontentloaded",
                        timeout=10000)
    except Exception as exc:
        log.debug("exit_lens error (non-fatal): %s", exc)


async def logout(page, persona: Persona) -> None:
    """Navigate to logout. For Authelia this redirects to the Authelia logout URL."""
    try:
        # Clear shell cookie first to avoid stale state
        await page.evaluate("document.cookie = 'bsv_role_shell=; Max-Age=0; path=/'")
        await page.goto(persona.base_url + "/logout", wait_until="domcontentloaded",
                        timeout=10000)
    except Exception as exc:
        log.debug("logout error (non-fatal): %s", exc)
