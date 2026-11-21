from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Set

import httpx

REPO_ROOT = Path(r"d:\Projects\Edwise")
SEED_DB_PATH = REPO_ROOT / "edwise.db"
FRONTEND_DIR = REPO_ROOT / "frontend"
VITE_BIN = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
BACKEND_DATESHEETS_DIR = REPO_ROOT / "backend" / "uploads" / "datesheets"
EDGE_EXECUTABLE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def is_headless() -> bool:
    raw = os.environ.get("EDWISE_E2E_HEADLESS", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def snapshot_datesheets() -> Set[str]:
    if not BACKEND_DATESHEETS_DIR.exists():
        return set()
    return {p.name for p in BACKEND_DATESHEETS_DIR.iterdir() if p.is_file()}


def cleanup_new_datesheets(baseline: Set[str]) -> None:
    if not BACKEND_DATESHEETS_DIR.exists():
        return
    for item in BACKEND_DATESHEETS_DIR.iterdir():
        if item.is_file() and item.name not in baseline:
            try:
                item.unlink()
            except OSError:
                pass


class IsolatedBackendServer:
    """Manages an isolated uvicorn backend backed by a temporary copy of edwise.db."""

    def __init__(self, temp_root: Optional[Path] = None) -> None:
        env_url = os.environ.get("EDWISE_E2E_API_URL", "").strip().rstrip("/")
        self.external: bool = bool(env_url)
        self.url: str = env_url
        self._owns_temp_dir: bool = temp_root is None and not self.external
        self._temp_dir: Optional[Path] = temp_root
        self._proc: Optional[subprocess.Popen[str]] = None
        self._log_file = None
        self._baseline_datesheets: Set[str] = snapshot_datesheets()
        self.uploads_dir: Optional[Path] = None
        self.db_path: Optional[Path] = None

    def start(self, timeout: float = 30.0) -> str:
        if self.external:
            self._wait_for_health(timeout=timeout)
            return self.url

        if not SEED_DB_PATH.exists():
            raise FileNotFoundError(f"Seeded database not found at {SEED_DB_PATH}")

        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="edwise_e2e_api_"))

        self.db_path = self._temp_dir / "test_edwise.db"
        shutil.copy2(SEED_DB_PATH, self.db_path)

        self.uploads_dir = self._temp_dir / "uploads"
        (self.uploads_dir / "datesheets").mkdir(parents=True, exist_ok=True)

        port = get_free_port()
        self.url = f"http://127.0.0.1:{port}"

        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{self.db_path.as_posix()}"
        env["PYTHONPATH"] = str(REPO_ROOT)
        env["UPLOADS_DIR"] = str(self.uploads_dir)
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ]
        log_path = self._temp_dir / "backend.log"
        self._log_file = open(log_path, "w", encoding="utf-8", buffering=1)
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(self._temp_dir),
            env=env,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._wait_for_health(timeout=timeout)
        return self.url

    def _wait_for_health(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        last_err: Optional[Exception] = None
        while time.monotonic() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                log_path = self._temp_dir / "backend.log" if self._temp_dir else None
                output = log_path.read_text(encoding="utf-8", errors="replace") if log_path and log_path.exists() else ""
                raise RuntimeError(
                    f"Isolated uvicorn exited prematurely (code={self._proc.returncode}):\n{output}"
                )
            try:
                resp = httpx.get(f"{self.url}/health", timeout=1.5)
                if resp.status_code == 200 and resp.json().get("status") == "ok":
                    return
            except Exception as exc:
                last_err = exc
            time.sleep(0.25)

        output = ""
        if self._proc is not None:
            self.stop()
        raise TimeoutError(f"Backend {self.url}/health did not become ready within {timeout}s: {last_err}\n{output}")

    def stop(self) -> None:
        try:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=3)
        finally:
            if self._log_file is not None:
                try:
                    self._log_file.close()
                except OSError:
                    pass
            cleanup_new_datesheets(self._baseline_datesheets)
            if self._owns_temp_dir and self._temp_dir and self._temp_dir.exists():
                shutil.rmtree(self._temp_dir, ignore_errors=True)


class IsolatedFrontendServer:
    """Manages an isolated Vite dev server proxying /api and /uploads to the isolated backend."""

    def __init__(self, api_url: str, temp_root: Optional[Path] = None) -> None:
        env_url = os.environ.get("EDWISE_E2E_FRONTEND_URL", "").strip().rstrip("/")
        self.external: bool = bool(env_url)
        self.url: str = env_url
        self.api_url: str = api_url.rstrip("/")
        self._owns_temp_dir: bool = temp_root is None and not self.external
        self._temp_dir: Optional[Path] = temp_root
        self._proc: Optional[subprocess.Popen[str]] = None
        self._log_file = None

    def start(self, timeout: float = 30.0) -> str:
        if self.external:
            self._wait_for_ready(timeout=timeout)
            return self.url

        if not VITE_BIN.exists():
            raise FileNotFoundError(f"Vite binary not found at {VITE_BIN}")

        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="edwise_e2e_fe_"))

        port = get_free_port()
        self.url = f"http://127.0.0.1:{port}"

        vite_node_entry = (FRONTEND_DIR / "node_modules" / "vite" / "dist" / "node" / "index.js").as_uri()
        react_plugin_entry = (FRONTEND_DIR / "node_modules" / "@vitejs" / "plugin-react" / "dist" / "index.js").as_uri()
        config_path = self._temp_dir / "vite.e2e.config.mjs"
        config_content = (
            f"import {{ defineConfig }} from '{vite_node_entry}';\n"
            f"import react from '{react_plugin_entry}';\n\n"
            f"export default defineConfig({{\n"
            f"  plugins: [react()],\n"
            f"  server: {{\n"
            f"    host: '127.0.0.1',\n"
            f"    port: {port},\n"
            f"    strictPort: true,\n"
            f"    proxy: {{\n"
            f"      '/api': {{ target: '{self.api_url}', changeOrigin: true }},\n"
            f"      '/uploads': {{ target: '{self.api_url}', changeOrigin: true }},\n"
            f"    }},\n"
            f"  }},\n"
            f"}});\n"
        )
        config_path.write_text(config_content, encoding="utf-8")

        cmd = [
            "node",
            str(VITE_BIN),
            "-c",
            str(config_path),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--strictPort",
        ]
        log_path = self._temp_dir / "frontend.log"
        self._log_file = open(log_path, "w", encoding="utf-8", buffering=1)
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(FRONTEND_DIR),
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._wait_for_ready(timeout=timeout)
        return self.url

    def _wait_for_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        last_err: Optional[Exception] = None
        while time.monotonic() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                log_path = self._temp_dir / "frontend.log" if self._temp_dir else None
                output = log_path.read_text(encoding="utf-8", errors="replace") if log_path and log_path.exists() else ""
                raise RuntimeError(
                    f"Isolated Vite exited prematurely (code={self._proc.returncode}):\n{output}"
                )
            try:
                resp = httpx.get(f"{self.url}/login", timeout=1.5)
                if resp.status_code == 200:
                    return
            except Exception as exc:
                last_err = exc
            time.sleep(0.25)

        self.stop()
        raise TimeoutError(f"Frontend {self.url}/login did not become ready within {timeout}s: {last_err}")

    def stop(self) -> None:
        try:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=3)
        finally:
            if self._log_file is not None:
                try:
                    self._log_file.close()
                except OSError:
                    pass
            if self._owns_temp_dir and self._temp_dir and self._temp_dir.exists():
                shutil.rmtree(self._temp_dir, ignore_errors=True)


@dataclass
class IsolatedStack:
    api_url: str
    frontend_url: str
    api_client: httpx.Client
    backend: IsolatedBackendServer
    frontend: IsolatedFrontendServer

