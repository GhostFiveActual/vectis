# GHOST FIVE // VECTIS
# Serves the local VECTIS Studio application and its compiler and runtime API.
"""Local-first VECTIS Studio server."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from importlib.resources import files
import ipaddress
import mimetypes
import threading
from typing import Any

from vectis import __version__
from vectis.browser import open_local_url
from vectis.compiler import compile_program
from vectis.evaluator import builtin_manifest
from vectis.examples import CANONICAL_EXAMPLES
from vectis.formatter import format_program
from vectis.lexer import LexerError
from vectis.parser import ParserError, parse
from vectis.runtime import Runtime


_EXAMPLES = CANONICAL_EXAMPLES


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _compile_payload(source: str, *, execute: bool = False, dry_run: bool = False) -> dict[str, Any]:
    program = parse(source, file="<studio>")
    result = compile_program(program)
    payload: dict[str, Any] = {
        "version": __version__,
        "ast": _jsonable(program),
        "diagnostics": [_jsonable(item) for item in result.diagnostics],
        "executionGraph": None,
        "runtime": None,
    }
    if result.graph is None:
        return payload
    payload["executionGraph"] = result.graph.to_dict()
    if execute:
        payload["runtime"] = _jsonable(
            Runtime(result.graph, dry_run=dry_run).execute()
        )
    return payload


def _is_loopback(host: str) -> bool:
    if host in {"localhost", ""}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "VECTISStudio/0.1"

    def log_message(self, format: str, *args: object) -> None:
        # Keep normal usage quiet; server startup prints the useful endpoint.
        return

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(_jsonable(payload), indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            raise ValueError("request body must be between 1 byte and 2 MB")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _source(self, data: dict[str, Any]) -> str:
        source = data.get("source")
        if not isinstance(source, str):
            raise ValueError("source must be a string")
        return source

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"service": "vectis-studio", "version": __version__, "status": "ok"})
            return
        if self.path == "/api/builtins":
            self._send_json(200, {"builtins": builtin_manifest()})
            return
        if self.path == "/api/examples":
            self._send_json(
                200,
                {
                    "examples": [
                        {"id": key, "title": key.replace("-", " ").title(), "source": value}
                        for key, value in _EXAMPLES.items()
                    ]
                },
            )
            return
        self._serve_asset()

    def do_POST(self) -> None:
        try:
            data = self._read_json()
            source = self._source(data)

            if self.path == "/api/check":
                payload = _compile_payload(source)
                self._send_json(200 if not payload["diagnostics"] else 422, payload)
                return
            if self.path == "/api/parse":
                program = parse(source, file="<studio>")
                self._send_json(200, {"ast": _jsonable(program)})
                return
            if self.path == "/api/plan":
                payload = _compile_payload(source)
                self._send_json(200 if payload["executionGraph"] is not None else 422, payload)
                return
            if self.path == "/api/run":
                payload = _compile_payload(source, execute=True, dry_run=bool(data.get("dry_run", False)))
                status = 200
                if payload["executionGraph"] is None:
                    status = 422
                elif payload["runtime"] and not payload["runtime"]["success"]:
                    status = 409
                self._send_json(status, payload)
                return
            if self.path == "/api/format":
                program = parse(source, file="<studio>")
                self._send_json(200, {"source": format_program(program)})
                return

            self._send_json(404, {"error": "unknown API endpoint"})
        except (LexerError, ParserError) as exc:
            diagnostic = getattr(exc, "diagnostic", None)
            self._send_json(
                422,
                {
                    "error": str(exc),
                    "diagnostics": [_jsonable(diagnostic)] if diagnostic is not None else [],
                },
            )
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def _serve_asset(self) -> None:
        relative = "index.html" if self.path in {"/", ""} else self.path.lstrip("/")
        if ".." in relative.split("/"):
            self._send_json(404, {"error": "not found"})
            return

        asset_root = files("vectis").joinpath("studio_assets")
        target = asset_root.joinpath(relative)
        if not target.is_file():
            self._send_json(404, {"error": "not found"})
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_studio(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    allow_remote: bool = False,
) -> None:
    if not allow_remote and not _is_loopback(host):
        raise ValueError(
            "VECTIS Studio binds to loopback by default; use --allow-remote explicitly for a non-loopback host"
        )
    server = ThreadingHTTPServer((host, port), StudioHandler)
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{url_host}:{server.server_port}/"
    print(f"VECTIS Mission Control {__version__}")
    print(f"Listening on {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.25, lambda: open_local_url(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
