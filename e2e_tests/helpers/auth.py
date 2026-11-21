from __future__ import annotations

from typing import Dict, Optional, Tuple

import httpx
from playwright.sync_api import Page


def api_login(client: httpx.Client, username: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, (
        f"Login failed for {username}: status={resp.status_code}, body={resp.text}"
    )
    return resp.json()


def auth_headers_for(client: httpx.Client, creds: Tuple[str, str]) -> Dict[str, str]:
    token_data = api_login(client, creds[0], creds[1])
    return {"Authorization": f"Bearer {token_data['access_token']}"}


def _wait_settled(page: Page, timeout_ms: int = 5000) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass


def ui_login(
    page: Page,
    frontend_url: str,
    username: str,
    password: str,
    expected_url_part: Optional[str] = None,
) -> None:
    page.goto(f"{frontend_url}/login", wait_until="domcontentloaded")
    username_input = page.get_by_placeholder("e.g. admin or teacher_sarah")
    username_input.wait_for(state="visible", timeout=15000)
    username_input.fill(username)
    page.get_by_placeholder("••••••••").fill(password)
    page.get_by_role("button", name="Sign In to Portal").click()

    if expected_url_part:
        page.wait_for_function(
            "(part) => window.location.pathname.includes(part)",
            arg=expected_url_part,
            timeout=15000,
        )
    else:
        page.wait_for_function(
            "() => !window.location.pathname.endsWith('/login')",
            timeout=15000,
        )
    page.locator("header").wait_for(state="visible", timeout=15000)
    page.locator("main").wait_for(state="visible", timeout=15000)
    page.wait_for_timeout(400)
    _wait_settled(page)


def ui_logout(page: Page) -> None:
    _wait_settled(page)
    btn = page.locator('button[title="Sign Out"]')
    btn.wait_for(state="visible", timeout=10000)
    btn.click()
    page.wait_for_function(
        "() => window.location.pathname.endsWith('/login')",
        timeout=10000,
    )
