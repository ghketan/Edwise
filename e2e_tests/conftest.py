from __future__ import annotations

from typing import Dict, Iterator, Tuple

import httpx
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
import pytest

from helpers.auth import auth_headers_for
from helpers.seed_helpers import (
    ADMIN_CREDS,
    STUDENT_1_CREDS,
    STUDENT_2_CREDS,
    TEACHER_ALAN_CREDS,
    TEACHER_SARAH_CREDS,
)
from helpers.servers import (
    EDGE_EXECUTABLE_PATH,
    IsolatedBackendServer,
    IsolatedFrontendServer,
    IsolatedStack,
    is_headless,
)
from helpers.watchers import BrowserErrorWatcher


@pytest.fixture(scope="session")
def backend_server() -> Iterator[IsolatedBackendServer]:
    server = IsolatedBackendServer()
    server.start(timeout=30.0)
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(scope="session")
def api_url(backend_server: IsolatedBackendServer) -> str:
    return backend_server.url


@pytest.fixture(scope="session")
def frontend_server(api_url: str) -> Iterator[IsolatedFrontendServer]:
    server = IsolatedFrontendServer(api_url=api_url)
    server.start(timeout=30.0)
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(scope="session")
def frontend_url(frontend_server: IsolatedFrontendServer) -> str:
    return frontend_server.url


@pytest.fixture(scope="session")
def playwright_instance() -> Iterator[Playwright]:
    pw = sync_playwright().start()
    try:
        yield pw
    finally:
        pw.stop()


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Iterator[Browser]:
    headless = is_headless()
    try:
        br = playwright_instance.chromium.launch(
            channel="msedge",
            headless=headless,
            args=["--no-sandbox"],
        )
    except Exception:
        br = playwright_instance.chromium.launch(
            executable_path=EDGE_EXECUTABLE_PATH,
            headless=headless,
            args=["--no-sandbox"],
        )
    try:
        yield br
    finally:
        br.close()


@pytest.fixture
def api_client(api_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_url, timeout=20.0) as client:
        yield client


@pytest.fixture
def admin_headers(api_client: httpx.Client) -> Dict[str, str]:
    return auth_headers_for(api_client, ADMIN_CREDS)


@pytest.fixture
def teacher_sarah_headers(api_client: httpx.Client) -> Dict[str, str]:
    return auth_headers_for(api_client, TEACHER_SARAH_CREDS)


@pytest.fixture
def teacher_alan_headers(api_client: httpx.Client) -> Dict[str, str]:
    return auth_headers_for(api_client, TEACHER_ALAN_CREDS)


@pytest.fixture
def student_1_headers(api_client: httpx.Client) -> Dict[str, str]:
    return auth_headers_for(api_client, STUDENT_1_CREDS)


@pytest.fixture
def student_2_headers(api_client: httpx.Client) -> Dict[str, str]:
    return auth_headers_for(api_client, STUDENT_2_CREDS)


@pytest.fixture
def browser_context(browser: Browser) -> Iterator[BrowserContext]:
    ctx = browser.new_context(
        accept_downloads=True,
        viewport={"width": 1280, "height": 800},
    )
    try:
        yield ctx
    finally:
        ctx.close()


@pytest.fixture
def page_with_watcher(
    browser_context: BrowserContext,
    frontend_url: str,
    api_url: str,
) -> Iterator[Tuple[Page, BrowserErrorWatcher]]:
    page = browser_context.new_page()
    watcher = BrowserErrorWatcher(page, frontend_url=frontend_url, api_url=api_url)
    try:
        yield page, watcher
        watcher.assert_clean()
    finally:
        page.close()


@pytest.fixture
def fresh_backend_client() -> Iterator[httpx.Client]:
    """Per-test isolated uvicorn + fresh DB copy for state-mutating API tests."""
    backend = IsolatedBackendServer()
    url = backend.start(timeout=30.0)
    try:
        with httpx.Client(base_url=url, timeout=20.0) as client:
            yield client
    finally:
        backend.stop()


@pytest.fixture
def fresh_isolated_stack(browser: Browser) -> Iterator[Tuple[IsolatedStack, Page, BrowserErrorWatcher]]:
    """Per-test isolated backend + frontend + fresh browser page + watcher for destructive/multi-role E2E tests."""
    backend = IsolatedBackendServer()
    api_u = backend.start(timeout=30.0)
    frontend = IsolatedFrontendServer(api_url=api_u)
    fe_u = frontend.start(timeout=30.0)

    ctx = browser.new_context(
        accept_downloads=True,
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()
    watcher = BrowserErrorWatcher(page, frontend_url=fe_u, api_url=api_u)
    client = httpx.Client(base_url=api_u, timeout=20.0)
    stack = IsolatedStack(
        api_url=api_u,
        frontend_url=fe_u,
        api_client=client,
        backend=backend,
        frontend=frontend,
    )
    try:
        yield stack, page, watcher
        watcher.assert_clean()
    finally:
        client.close()
        page.close()
        ctx.close()
        frontend.stop()
        backend.stop()
