from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List, Optional, Set
from urllib.parse import urlparse

from playwright.sync_api import ConsoleMessage, Page, Request, Response

IGNORED_EXTERNAL_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")


class BrowserErrorWatcher:
    """Captures console errors, uncaught pageerrors, bad same-origin HTTP responses, and request failures."""

    def __init__(self, page: Page, frontend_url: str, api_url: str) -> None:
        self.page = page
        self.frontend_origin = self._origin(frontend_url)
        self.api_origin = self._origin(api_url)
        self.console_errors: List[str] = []
        self.page_errors: List[str] = []
        self.bad_responses: List[str] = []
        self.request_failures: List[str] = []
        self._allow_stack: List[Set[int]] = []

        page.on("console", self._on_console)
        page.on("pageerror", self._on_pageerror)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_requestfailed)

    @staticmethod
    def _origin(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}".lower()

    def _is_same_origin(self, url: str) -> bool:
        origin = self._origin(url)
        return origin in {self.frontend_origin, self.api_origin}

    @staticmethod
    def _is_ignored_external(url: str) -> bool:
        lowered = url.lower()
        return any(host in lowered for host in IGNORED_EXTERNAL_HOSTS)

    def _is_status_allowlisted(self, status: int) -> bool:
        return any(status in allowed for allowed in self._allow_stack)

    @contextmanager
    def allow_status(self, *statuses: int) -> Iterator[None]:
        self._allow_stack.append(set(statuses))
        try:
            yield
        finally:
            self._allow_stack.pop()

    def _on_console(self, msg: ConsoleMessage) -> None:
        if msg.type != "error":
            return
        loc = msg.location or {}
        loc_url = str(loc.get("url", "") or "")
        text = msg.text or ""
        if self._is_ignored_external(loc_url) or self._is_ignored_external(text):
            return
        # If an allowlisted 4xx triggered Chromium's generic "Failed to load resource: the server responded with a status of 401/403/404/422"
        if self._allow_stack and "the server responded with a status of" in text:
            for code in (s for group in self._allow_stack for s in group):
                if f"status of {code}" in text:
                    return
        self.console_errors.append(f"[console.error] {text} (location={loc})")

    def _on_pageerror(self, exc: Exception) -> None:
        self.page_errors.append(f"[pageerror] {exc!r}")

    def _on_response(self, response: Response) -> None:
        url = response.url
        status = response.status
        if not self._is_same_origin(url):
            return
        if status >= 500:
            self.bad_responses.append(f"[HTTP {status}] {response.request.method} {url}")
        elif 400 <= status < 500 and not self._is_status_allowlisted(status):
            self.bad_responses.append(f"[HTTP {status}] {response.request.method} {url}")

    def _on_requestfailed(self, request: Request) -> None:
        url = request.url
        if self._is_ignored_external(url):
            return
        if not self._is_same_origin(url):
            return
        failure = request.failure or "unknown"
        if failure == "net::ERR_ABORTED" and request.resource_type == "document":
            return
        self.request_failures.append(
            f"[requestfailed] {request.method} {url} ({request.resource_type}: {failure})"
        )

    def clear(self) -> None:
        self.console_errors.clear()
        self.page_errors.clear()
        self.bad_responses.clear()
        self.request_failures.clear()

    def assert_clean(self) -> None:
        errors = (
            self.console_errors
            + self.page_errors
            + self.bad_responses
            + self.request_failures
        )
        if errors:
            joined = "\n  - ".join(errors)
            raise AssertionError(f"BrowserErrorWatcher detected errors:\n  - {joined}")
