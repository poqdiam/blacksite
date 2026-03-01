"""
BLACKSITE RBAC Runner — Discovery module.

Provides:
  - discover_nav_links(): extract sidebar nav links from a rendered page (GET + parse HTML)
  - discover_routes_from_main(): parse main.py with ast to find route decorators + role guards
  - generate_discovered_flows(): merge nav + route info into flow-compatible dict
"""
from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

log = logging.getLogger("bsv.rbac.discovery")

# Roles that are always allowed (admin is not a shell lens but appears in _require_role calls)
ADMIN_EQUIV = {"admin"}


def discover_nav_links(html_content: str, lens: str) -> list[str]:
    """
    Extract all href values from <a class="sb-link"> elements in the rendered sidebar.

    Since base.html uses Jinja2 with role-specific nav branches, we call GET on a page
    with the lens cookie active, then parse the returned HTML here.

    Returns a list of URL path strings (e.g. ["/systems", "/poam", "/risks"]).
    """
    links: list[str] = []
    # Match anchor tags with sb-link class in the sidebar nav
    # Pattern: <a href="/some/path" class="sb-link...">
    pattern = re.compile(
        r'<a\s+[^>]*href=["\']([^"\'#][^"\']*)["\'][^>]*class=["\'][^"\']*sb-link[^"\']*["\']'
        r'|'
        r'<a\s+[^>]*class=["\'][^"\']*sb-link[^"\']*["\'][^>]*href=["\']([^"\'#][^"\']*)["\']',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(html_content):
        href = m.group(1) or m.group(2)
        if href and href.startswith("/") and "#" not in href:
            if href not in links:
                links.append(href)

    # Also grab any /switch-role-view or /exit-shell links (exclude them)
    links = [l for l in links if not l.startswith("/switch-role-view")
             and not l.startswith("/exit-shell")
             and not l.startswith("/logout")
             and not l.startswith("/admin/view-as")]

    log.debug("Discovered %d nav links for lens %s", len(links), lens)
    return links


def _extract_role_list(node: ast.expr) -> list[str]:
    """
    Given an AST node that should be a list of strings (role list passed to _require_role),
    return those strings. Handles List nodes and Constant nodes.
    """
    roles: list[str] = []
    if isinstance(node, ast.List):
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                roles.append(elt.value)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        roles.append(node.value)
    return roles


def discover_routes_from_main(main_py_path: str) -> list[dict]:
    """
    Parse main.py with ast to find all @app.get/@app.post decorated functions.

    For each route extract:
      method: GET | POST
      path: the route path string
      required_roles: list of roles passed to _require_role() in the function body

    Returns list of {method, path, required_roles: list[str]}
    """
    path = Path(main_py_path)
    if not path.exists():
        log.error("main.py not found at %s", main_py_path)
        return []

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        log.error("Failed to parse main.py: %s", exc)
        return []

    routes: list[dict] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Find route decorators: @app.get("/path") or @app.post("/path")
        for decorator in node.decorator_list:
            method = None
            route_path = None

            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name) and func.value.id == "app":
                        if func.attr in ("get", "post", "put", "delete", "patch"):
                            method = func.attr.upper()
                            # First positional arg is the path
                            if decorator.args:
                                arg = decorator.args[0]
                                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                    route_path = arg.value

            if method is None or route_path is None:
                continue

            # Now look for _require_role calls in the function body
            required_roles: list[str] = []
            for body_node in ast.walk(node):
                if isinstance(body_node, ast.Call):
                    call_func = body_node.func
                    # Match _require_role(role_var, [...])
                    if (isinstance(call_func, ast.Name) and
                            call_func.id == "_require_role" and
                            len(body_node.args) >= 2):
                        roles = _extract_role_list(body_node.args[1])
                        required_roles.extend(roles)

                    # Also match calls with keyword args (unlikely but safe)
                    for kw in body_node.keywords:
                        if kw.arg == "allowed":
                            roles = _extract_role_list(kw.value)
                            required_roles.extend(roles)

            # Deduplicate
            required_roles = list(dict.fromkeys(required_roles))

            routes.append({
                "method": method,
                "path": route_path,
                "required_roles": required_roles,
                "function": node.name,
            })

    log.info("Discovered %d routes from main.py", len(routes))
    return routes


def generate_discovered_flows(base_url: str, lens: str,
                               nav_links: list[str],
                               routes: list[dict]) -> dict:
    """
    Merge nav links + route info into a dict of flow-id → flow-config.

    For GET routes with no role guard: generate a nav_check flow (expect 200).
    For POST routes with role guards: generate a write_access flow.

    Returns dict keyed by flow_id.
    """
    flows: dict[str, dict] = {}

    # Build a path → route lookup
    route_map: dict[str, dict] = {}
    for r in routes:
        route_map[r["path"]] = r

    for link in nav_links:
        # Strip query strings
        clean = link.split("?")[0]
        flow_id = f"nav_{clean.replace('/', '_').strip('_')}"
        if not flow_id or flow_id == "nav_":
            continue

        route_info = route_map.get(clean, {})
        required = route_info.get("required_roles", [])

        flows[flow_id] = {
            "id": flow_id,
            "name": f"Nav check: {clean}",
            "source": "discovered",
            "lens": lens,
            "allowed_lenses": [lens] if not required or lens in required or "admin" in required else [],
            "denied_lenses": [],
            "steps": [
                {
                    "action": "navigate",
                    "url": clean,
                    "expected_status": 200,
                }
            ],
        }

    return flows


async def discover_all_nav(page, base_url: str, lens: str) -> list[str]:
    """
    Navigate to the systems page (a comprehensive GRC hub page) and extract sidebar links.
    This is called with the lens cookie already set.
    """
    try:
        response = await page.goto(base_url + "/systems", wait_until="domcontentloaded",
                                   timeout=15000)
        if response and response.status >= 400:
            log.warning("Nav discovery GET /systems returned %d", response.status)
            return []
        html = await page.content()
        return discover_nav_links(html, lens)
    except Exception as exc:
        log.error("Nav discovery failed for lens %s: %s", lens, exc)
        return []
