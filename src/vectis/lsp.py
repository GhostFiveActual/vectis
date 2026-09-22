# GHOST FIVE // VECTIS
# Implements a dependency-free Language Server Protocol endpoint for VECTIS editors.
"""VECTIS Language Server Protocol support over standard input and output."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import BinaryIO
from urllib.parse import unquote, urlparse

from vectis import __version__
from vectis.ast import ImportStatement
from vectis.compiler import compile_program
from vectis.diagnostic import Diagnostic, DiagnosticError
from vectis.editor import completion_items, document_symbols, hover_info
from vectis.formatter import format_program
from vectis.modules import load_program_file
from vectis.parser import parse


_JSON_RPC_VERSION = "2.0"
_LSP_ERROR_METHOD_NOT_FOUND = -32601
_LSP_ERROR_INTERNAL = -32603


def _uri_path(uri: str) -> Path | None:
    """Convert one file URI into a local path when possible."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None

    path = unquote(parsed.path)
    if parsed.netloc:
        path = f"//{parsed.netloc}{path}"
    if os.name == "nt" and len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    return Path(path)


def _lsp_diagnostic(diagnostic: Diagnostic) -> dict[str, object]:
    """Translate one VECTIS diagnostic into the LSP diagnostic shape."""
    start = diagnostic.span.start
    end = diagnostic.span.end
    return {
        "range": {
            "start": {
                "line": max(0, start.line - 1),
                "character": max(0, start.column - 1),
            },
            "end": {
                "line": max(0, end.line - 1),
                "character": max(0, end.column),
            },
        },
        "severity": 1 if diagnostic.severity.value == "error" else 2,
        "code": diagnostic.code.value,
        "source": "vectis",
        "message": diagnostic.message,
    }


def _response(message_id: object, result: object) -> dict[str, object]:
    return {
        "jsonrpc": _JSON_RPC_VERSION,
        "id": message_id,
        "result": result,
    }


def _error_response(
    message_id: object,
    *,
    code: int,
    message: str,
) -> dict[str, object]:
    return {
        "jsonrpc": _JSON_RPC_VERSION,
        "id": message_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _notification(method: str, params: object) -> dict[str, object]:
    return {
        "jsonrpc": _JSON_RPC_VERSION,
        "method": method,
        "params": params,
    }


class LanguageServer:
    """Small deterministic LSP server backed by the VECTIS compiler."""

    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self.shutdown_requested = False
        self.exit_requested = False

    def _diagnostics(self, uri: str, source: str) -> list[dict[str, object]]:
        file = uri
        try:
            program = parse(source, file=file)

            path = _uri_path(uri)
            has_imports = any(
                isinstance(statement, ImportStatement)
                for statement in program.statements
            )

            if path is not None and path.is_file():
                disk_source = path.read_text(encoding="utf-8")
                if disk_source == source:
                    program = load_program_file(path).program
                elif has_imports:
                    return []

            result = compile_program(program)
            return [
                _lsp_diagnostic(diagnostic)
                for diagnostic in result.diagnostics
            ]
        except DiagnosticError as exc:
            return [_lsp_diagnostic(exc.diagnostic)]
        except (OSError, UnicodeError, ValueError) as exc:
            return [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 1},
                    },
                    "severity": 1,
                    "code": "LSP001",
                    "source": "vectis",
                    "message": str(exc),
                }
            ]

    def _publish_diagnostics(self, uri: str) -> dict[str, object]:
        source = self.documents.get(uri, "")
        return _notification(
            "textDocument/publishDiagnostics",
            {
                "uri": uri,
                "diagnostics": self._diagnostics(uri, source),
            },
        )

    def _format(self, uri: str) -> list[dict[str, object]]:
        source = self.documents.get(uri)
        if source is None:
            path = _uri_path(uri)
            if path is None or not path.is_file():
                return []
            source = path.read_text(encoding="utf-8")

        try:
            formatted = format_program(parse(source, file=uri))
        except DiagnosticError:
            return []

        if formatted == source:
            return []

        line_count = source.count("\n") + 1
        return [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {
                        "line": line_count,
                        "character": 0,
                    },
                },
                "newText": formatted,
            }
        ]

    def handle(self, message: dict[str, object]) -> list[dict[str, object]]:
        """Handle one JSON-RPC message and return zero or more outbound messages."""
        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params")
        if not isinstance(params, dict):
            params = {}

        if method == "initialize":
            return [
                _response(
                    message_id,
                    {
                        "capabilities": {
                            "textDocumentSync": {
                                "openClose": True,
                                "change": 1,
                                "save": {"includeText": True},
                            },
                            "documentFormattingProvider": True,
                            "completionProvider": {
                                "triggerCharacters": [".", "_"],
                            },
                            "hoverProvider": True,
                            "documentSymbolProvider": True,
                        },
                        "serverInfo": {
                            "name": "vectis",
                            "version": __version__,
                        },
                    },
                )
            ]

        if method == "shutdown":
            self.shutdown_requested = True
            return [_response(message_id, None)]

        if method == "exit":
            self.exit_requested = True
            return []

        if method == "initialized":
            return []

        if method == "textDocument/didOpen":
            document = params.get("textDocument")
            if isinstance(document, dict):
                uri = document.get("uri")
                text = document.get("text")
                if isinstance(uri, str) and isinstance(text, str):
                    self.documents[uri] = text
                    return [self._publish_diagnostics(uri)]
            return []

        if method == "textDocument/didChange":
            document = params.get("textDocument")
            changes = params.get("contentChanges")
            if (
                isinstance(document, dict)
                and isinstance(changes, list)
                and changes
            ):
                uri = document.get("uri")
                latest = changes[-1]
                if isinstance(uri, str) and isinstance(latest, dict):
                    text = latest.get("text")
                    if isinstance(text, str):
                        self.documents[uri] = text
                        return [self._publish_diagnostics(uri)]
            return []

        if method == "textDocument/didSave":
            document = params.get("textDocument")
            if isinstance(document, dict):
                uri = document.get("uri")
                if isinstance(uri, str):
                    text = params.get("text")
                    if isinstance(text, str):
                        self.documents[uri] = text
                    return [self._publish_diagnostics(uri)]
            return []

        if method == "textDocument/didClose":
            document = params.get("textDocument")
            if isinstance(document, dict):
                uri = document.get("uri")
                if isinstance(uri, str):
                    self.documents.pop(uri, None)
                    return [
                        _notification(
                            "textDocument/publishDiagnostics",
                            {"uri": uri, "diagnostics": []},
                        )
                    ]
            return []

        if method == "textDocument/formatting":
            document = params.get("textDocument")
            uri = (
                document.get("uri")
                if isinstance(document, dict)
                else None
            )
            return [
                _response(
                    message_id,
                    self._format(uri) if isinstance(uri, str) else [],
                )
            ]

        if method == "textDocument/completion":
            return [
                _response(
                    message_id,
                    {
                        "isIncomplete": False,
                        "items": completion_items(),
                    },
                )
            ]

        if method == "textDocument/hover":
            document = params.get("textDocument")
            position = params.get("position")
            uri = (
                document.get("uri")
                if isinstance(document, dict)
                else None
            )
            source = (
                self.documents.get(uri)
                if isinstance(uri, str)
                else None
            )
            if source is None and isinstance(uri, str):
                path = _uri_path(uri)
                if path is not None and path.is_file():
                    source = path.read_text(encoding="utf-8")
            result = None
            if source is not None and isinstance(position, dict):
                line = position.get("line")
                character = position.get("character")
                if isinstance(line, int) and isinstance(character, int):
                    result = hover_info(
                        source,
                        line=line,
                        character=character,
                    )
            return [_response(message_id, result)]

        if method == "textDocument/documentSymbol":
            document = params.get("textDocument")
            uri = (
                document.get("uri")
                if isinstance(document, dict)
                else None
            )
            source = (
                self.documents.get(uri)
                if isinstance(uri, str)
                else None
            )
            if source is None and isinstance(uri, str):
                path = _uri_path(uri)
                if path is not None and path.is_file():
                    source = path.read_text(encoding="utf-8")
            symbols: list[dict[str, object]] = []
            if source is not None and isinstance(uri, str):
                try:
                    symbols = document_symbols(source, file=uri)
                except DiagnosticError:
                    symbols = []
            return [_response(message_id, symbols)]

        if message_id is not None:
            return [
                _error_response(
                    message_id,
                    code=_LSP_ERROR_METHOD_NOT_FOUND,
                    message=f"unsupported method: {method}",
                )
            ]
        return []


def _read_message(stream: BinaryIO) -> dict[str, object] | None:
    """Read one Content-Length framed JSON-RPC message."""
    headers: dict[str, str] = {}

    while True:
        line = stream.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("ascii").strip()
        if ":" not in decoded:
            continue
        name, value = decoded.split(":", 1)
        headers[name.lower().strip()] = value.strip()

    raw_length = headers.get("content-length")
    if raw_length is None:
        raise ValueError("missing Content-Length header")

    length = int(raw_length)
    if length < 0:
        raise ValueError("Content-Length must be non-negative")

    payload = stream.read(length)
    if len(payload) != length:
        raise EOFError("unexpected end of LSP input")

    message = json.loads(payload.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("LSP payload must be a JSON object")
    return message


def _write_message(stream: BinaryIO, message: dict[str, object]) -> None:
    """Write one Content-Length framed JSON-RPC message."""
    payload = json.dumps(
        message,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    stream.write(
        f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
    )
    stream.write(payload)
    stream.flush()


def serve(
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
) -> int:
    """Run the VECTIS language server until the client exits."""
    incoming = input_stream or sys.stdin.buffer
    outgoing = output_stream or sys.stdout.buffer
    server = LanguageServer()

    while not server.exit_requested:
        try:
            message = _read_message(incoming)
            if message is None:
                break
            replies = server.handle(message)
        except Exception as exc:
            replies = [
                _error_response(
                    None,
                    code=_LSP_ERROR_INTERNAL,
                    message=f"{type(exc).__name__}: {exc}",
                )
            ]

        for reply in replies:
            _write_message(outgoing, reply)

    return 0 if server.shutdown_requested else 1
