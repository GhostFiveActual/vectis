# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS http adapter contract.
"""Security and behavior tests for the VECTIS HTTP adapter."""

from __future__ import annotations

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from vectis.adapters.http import (
    HttpAccessDenied,
    HttpAdapter,
    HttpRequest,
    HttpResponse,
    HttpTimeoutError,
)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str = "text/plain",
        headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/ok":
            self._write(200, b"ok")
            return

        if self.path == "/json":
            self._write(
                200,
                b'{"answer":42,"ok":true}',
                content_type="application/json",
            )
            return

        if self.path == "/status":
            self._write(
                418,
                b"teapot",
                headers=(("X-Vectis-Status", "captured"),),
            )
            return

        if self.path == "/redirect":
            self._write(
                302,
                b"redirect",
                headers=(("Location", "/ok"),),
            )
            return

        if self.path == "/headers":
            value = self.headers.get("X-Vectis-Test", "")
            self._write(200, value.encode("utf-8"))
            return

        if self.path == "/slow":
            time.sleep(0.25)
            try:
                self._write(200, b"late")
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self._write(404, b"missing")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        if self.path == "/echo":
            self._write(
                200,
                body,
                content_type=self.headers.get(
                    "Content-Type",
                    "application/octet-stream",
                ),
            )
            return

        self._write(404, b"missing")


class HttpAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            _Handler,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.thread.start()
        cls.base_url = (
            f"http://127.0.0.1:{cls.server.server_port}"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)

    def setUp(self) -> None:
        self.adapter = HttpAdapter(
            default_timeout=1.0,
            max_timeout=2.0,
        )

    def test_public_capability_name(self) -> None:
        self.assertEqual(
            self.adapter.capability,
            "http",
        )

    def test_structured_request_returns_response(self) -> None:
        response = self.adapter.send(
            HttpRequest(
                method="GET",
                url=self.base_url + "/ok",
            )
        )

        self.assertIsInstance(
            response,
            HttpResponse,
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, b"ok")

    def test_optional_host_allowlist_is_enforced(self) -> None:
        allowed = HttpAdapter(
            default_timeout=1.0,
            max_timeout=2.0,
            allowed_hosts=("127.0.0.1",),
        )
        response = allowed.send(
            HttpRequest(
                method="GET",
                url=self.base_url + "/ok",
            )
        )
        self.assertEqual(response.status, 200)

        denied = HttpAdapter(
            allowed_hosts=("example.invalid",),
        )
        with self.assertRaises(HttpAccessDenied):
            denied.send(
                HttpRequest(
                    method="GET",
                    url=self.base_url + "/ok",
                )
            )

    def test_host_allowlist_rejects_url_shaped_entries(self) -> None:
        with self.assertRaises(ValueError):
            HttpAdapter(
                allowed_hosts=("https://example.com",),
            )

    def test_non_http_scheme_is_denied(self) -> None:
        with self.assertRaises(HttpAccessDenied):
            self.adapter.send(
                HttpRequest(
                    method="GET",
                    url="file:///etc/passwd",
                )
            )

    def test_missing_hostname_is_denied(self) -> None:
        with self.assertRaises(HttpAccessDenied):
            self.adapter.send(
                HttpRequest(
                    method="GET",
                    url="http:///missing-host",
                )
            )

    def test_invalid_request_type_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.adapter.send(  # type: ignore[arg-type]
                "http://example.invalid"
            )

    def test_http_error_status_is_structured_response(self) -> None:
        response = self.adapter.send(
            HttpRequest(
                method="GET",
                url=self.base_url + "/status",
            )
        )

        self.assertEqual(response.status, 418)
        self.assertEqual(response.body, b"teapot")
        self.assertIn(
            ("X-Vectis-Status", "captured"),
            response.headers,
        )

    def test_redirect_is_not_followed_automatically(self) -> None:
        response = self.adapter.send(
            HttpRequest(
                method="GET",
                url=self.base_url + "/redirect",
            )
        )

        self.assertEqual(response.status, 302)
        self.assertEqual(response.body, b"redirect")
        self.assertIn(
            ("Location", "/ok"),
            response.headers,
        )

    def test_request_headers_are_preserved(self) -> None:
        response = self.adapter.send(
            HttpRequest(
                method="GET",
                url=self.base_url + "/headers",
                headers=(
                    ("X-Vectis-Test", "literal-value"),
                ),
            )
        )

        self.assertEqual(
            response.body,
            b"literal-value",
        )

    def test_binary_request_body_is_preserved(self) -> None:
        payload = b"\x00vectis\xff"

        response = self.adapter.send(
            HttpRequest(
                method="POST",
                url=self.base_url + "/echo",
                body=payload,
            )
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, payload)

    def test_json_response_is_deterministically_decoded(self) -> None:
        response = self.adapter.send(
            HttpRequest(
                method="GET",
                url=self.base_url + "/json",
            )
        )

        self.assertEqual(
            response.json(),
            {
                "answer": 42,
                "ok": True,
            },
        )

    def test_json_request_body_round_trip(self) -> None:
        payload = {
            "alpha": 1,
            "enabled": True,
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        response = self.adapter.send(
            HttpRequest(
                method="POST",
                url=self.base_url + "/echo",
                headers=(
                    ("Content-Type", "application/json"),
                ),
                body=encoded,
            )
        )

        self.assertEqual(
            json.loads(
                response.body.decode("utf-8")
            ),
            payload,
        )

    def test_timeout_is_enforced(self) -> None:
        with self.assertRaises(HttpTimeoutError) as raised:
            self.adapter.send(
                HttpRequest(
                    method="GET",
                    url=self.base_url + "/slow",
                ),
                timeout=0.05,
            )

        self.assertEqual(
            raised.exception.timeout,
            0.05,
        )

    def test_timeout_above_maximum_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.send(
                HttpRequest(
                    method="GET",
                    url=self.base_url + "/ok",
                ),
                timeout=3.0,
            )

    def test_nonpositive_timeout_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.send(
                HttpRequest(
                    method="GET",
                    url=self.base_url + "/ok",
                ),
                timeout=0,
            )

    def test_repeated_execution_is_deterministic(self) -> None:
        request = HttpRequest(
            method="GET",
            url=self.base_url + "/ok",
        )

        first = self.adapter.send(request)
        second = self.adapter.send(request)

        self.assertEqual(
            (
                first.status,
                first.body,
            ),
            (
                second.status,
                second.body,
            ),
        )


if __name__ == "__main__":
    unittest.main()
