# GHOST FIVE // VECTIS
# Implements the bounded HTTP capability adapter used by VECTIS.
"""Controlled HTTP capability adapter for VECTIS."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)


_JSON_UNSET = object()


class HttpAccessDenied(PermissionError):
    """Raised when an HTTP request violates the adapter boundary."""


class HttpTimeoutError(TimeoutError):
    """Raised when an HTTP operation exceeds its configured timeout."""

    def __init__(
        self,
        message: str,
        *,
        timeout: float,
        request: HttpRequest,
    ) -> None:
        super().__init__(message)
        self.timeout = timeout
        self.request = request


class HttpTransportError(ConnectionError):
    """Raised when the HTTP transport fails before a response is available."""

    def __init__(
        self,
        message: str,
        *,
        request: HttpRequest,
    ) -> None:
        super().__init__(message)
        self.request = request


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """Structured HTTP request model."""

    method: str
    url: str
    headers: tuple[tuple[str, str], ...] = ()
    body: bytes | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.method, str):
            raise TypeError(
                "HTTP method must be str"
            )

        method = self.method.strip().upper()

        if not method:
            raise ValueError(
                "HTTP method must not be empty"
            )

        if any(
            character.isspace()
            for character in method
        ):
            raise ValueError(
                "HTTP method must not contain whitespace"
            )

        if not isinstance(self.url, str) or not self.url:
            raise TypeError(
                "HTTP URL must be a non-empty str"
            )

        normalized_headers: list[tuple[str, str]] = []

        for item in self.headers:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "HTTP headers must contain name/value pairs"
                )

            name, value = item

            if not isinstance(name, str) or not name:
                raise TypeError(
                    "HTTP header names must be non-empty str"
                )

            if not isinstance(value, str):
                raise TypeError(
                    "HTTP header values must be str"
                )

            if "\r" in name or "\n" in name:
                raise ValueError(
                    "HTTP header names must not contain line breaks"
                )

            if "\r" in value or "\n" in value:
                raise ValueError(
                    "HTTP header values must not contain line breaks"
                )

            normalized_headers.append(
                (name, value)
            )

        if self.body is not None and not isinstance(
            self.body,
            bytes,
        ):
            raise TypeError(
                "HTTP request body must be bytes or None"
            )

        object.__setattr__(
            self,
            "method",
            method,
        )
        object.__setattr__(
            self,
            "headers",
            tuple(normalized_headers),
        )


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Structured HTTP response returned for every received HTTP status."""

    url: str
    status: int
    reason: str
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @property
    def ok(self) -> bool:
        """Return whether the status is in the 2xx range."""
        return 200 <= self.status < 300

    def text(
        self,
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
    ) -> str:
        """Decode the response body as text."""
        return self.body.decode(
            encoding,
            errors=errors,
        )

    def json(self) -> Any:
        """Decode the response body as UTF-8 JSON."""
        return json.loads(
            self.body.decode("utf-8")
        )


class _NoRedirectHandler(HTTPRedirectHandler):
    """Prevent implicit authority expansion through redirects."""

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class HttpAdapter:
    """Perform bounded HTTP requests through an explicit capability boundary."""

    capability = "http"

    def __init__(
        self,
        *,
        default_timeout: float = 10.0,
        max_timeout: float = 60.0,
        allowed_hosts: Iterable[str] | None = None,
    ) -> None:
        self._default_timeout = self._validate_timeout(
            default_timeout,
            field="default_timeout",
        )
        self._max_timeout = self._validate_timeout(
            max_timeout,
            field="max_timeout",
        )

        if self._default_timeout > self._max_timeout:
            raise ValueError(
                "default_timeout must not exceed max_timeout"
            )

        self._allowed_hosts = self._normalize_allowed_hosts(
            allowed_hosts
        )

        self._opener = build_opener(
            ProxyHandler({}),
            _NoRedirectHandler(),
        )

    @property
    def allowed_hosts(self) -> tuple[str, ...] | None:
        """Return the canonical host allowlist, or None when unrestricted."""
        return self._allowed_hosts

    @property
    def default_timeout(self) -> float:
        """Return the configured default timeout."""
        return self._default_timeout

    @property
    def max_timeout(self) -> float:
        """Return the configured maximum timeout."""
        return self._max_timeout

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] | None = None,
        body: bytes | None = None,
        json_body: Any = _JSON_UNSET,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Build and send one structured HTTP request."""
        if body is not None and json_body is not _JSON_UNSET:
            raise ValueError(
                "body and json_body are mutually exclusive"
            )

        normalized_headers = self._normalize_headers(
            headers
        )

        if json_body is not _JSON_UNSET:
            body = json.dumps(
                json_body,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")

            if not any(
                name.lower() == "content-type"
                for name, _ in normalized_headers
            ):
                normalized_headers += (
                    ("Content-Type", "application/json"),
                )

        structured = HttpRequest(
            method=method,
            url=url,
            headers=normalized_headers,
            body=body,
        )

        return self.send(
            structured,
            timeout=timeout,
        )

    def send(
        self,
        request: HttpRequest,
        *,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Send a structured request and return its received HTTP response."""
        if not isinstance(request, HttpRequest):
            raise TypeError(
                "request must be HttpRequest"
            )

        self._validate_url(request.url)

        effective_timeout = (
            self._default_timeout
            if timeout is None
            else self._validate_timeout(
                timeout,
                field="timeout",
            )
        )

        if effective_timeout > self._max_timeout:
            raise ValueError(
                "timeout must not exceed max_timeout"
            )

        outgoing = Request(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            method=request.method,
        )

        try:
            response = self._opener.open(
                outgoing,
                timeout=effective_timeout,
            )
        except HTTPError as exc:
            return self._response_from_http_error(
                exc
            )
        except TimeoutError as exc:
            raise HttpTimeoutError(
                (
                    "HTTP request exceeded timeout "
                    f"of {effective_timeout} seconds"
                ),
                timeout=effective_timeout,
                request=request,
            ) from exc
        except URLError as exc:
            if isinstance(
                exc.reason,
                TimeoutError,
            ):
                raise HttpTimeoutError(
                    (
                        "HTTP request exceeded timeout "
                        f"of {effective_timeout} seconds"
                    ),
                    timeout=effective_timeout,
                    request=request,
                ) from exc

            raise HttpTransportError(
                f"HTTP transport failed: {exc.reason}",
                request=request,
            ) from exc

        with response:
            return HttpResponse(
                url=response.geturl(),
                status=response.status,
                reason=str(response.reason or ""),
                headers=tuple(
                    response.headers.items()
                ),
                body=response.read(),
            )

    @staticmethod
    def _normalize_headers(
        headers: Mapping[str, str] | Iterable[tuple[str, str]] | None,
    ) -> tuple[tuple[str, str], ...]:
        if headers is None:
            return ()

        items = (
            tuple(headers.items())
            if isinstance(headers, Mapping)
            else tuple(headers)
        )

        return HttpRequest(
            method="GET",
            url="http://validation.invalid",
            headers=items,
        ).headers

    @staticmethod
    def _validate_timeout(
        value: float,
        *,
        field: str,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                f"{field} must be a positive number"
            )

        normalized = float(value)

        if normalized <= 0:
            raise ValueError(
                f"{field} must be greater than zero"
            )

        return normalized

    def _validate_url(self, url: str) -> None:
        parts = urlsplit(url)

        if parts.scheme not in {
            "http",
            "https",
        }:
            raise HttpAccessDenied(
                "HTTP URL scheme must be http or https"
            )

        if not parts.hostname:
            raise HttpAccessDenied(
                "HTTP URL must contain a hostname"
            )

        if parts.username is not None or parts.password is not None:
            raise HttpAccessDenied(
                "embedded HTTP credentials are denied"
            )

        hostname = parts.hostname.lower().rstrip(".")
        if (
            self._allowed_hosts is not None
            and hostname not in self._allowed_hosts
        ):
            raise HttpAccessDenied(
                f"HTTP hostname is not allowlisted: {hostname!r}"
            )

    @staticmethod
    def _normalize_allowed_hosts(
        values: Iterable[str] | None,
    ) -> tuple[str, ...] | None:
        if values is None:
            return None
        if isinstance(values, str):
            raise TypeError(
                "allowed_hosts must be an iterable of host strings"
            )

        normalized: list[str] = []
        for value in values:
            if not isinstance(value, str):
                raise TypeError(
                    "allowed_hosts entries must be strings"
                )
            host = value.strip().lower().rstrip(".")
            if not host:
                raise ValueError(
                    "allowed_hosts entries must not be empty"
                )
            if "://" in host or "/" in host or ":" in host:
                raise ValueError(
                    "allowed_hosts entries must contain hostnames only"
                )
            if host not in normalized:
                normalized.append(host)

        if not normalized:
            raise ValueError(
                "allowed_hosts must contain at least one hostname"
            )
        return tuple(normalized)

    @staticmethod
    def _response_from_http_error(
        error: HTTPError,
    ) -> HttpResponse:
        try:
            body = error.read()
        finally:
            error.close()

        return HttpResponse(
            url=error.geturl(),
            status=error.code,
            reason=str(error.reason or ""),
            headers=tuple(
                error.headers.items()
                if error.headers is not None
                else ()
            ),
            body=body,
        )


__all__ = [
    "HttpAccessDenied",
    "HttpAdapter",
    "HttpRequest",
    "HttpResponse",
    "HttpTimeoutError",
    "HttpTransportError",
]
