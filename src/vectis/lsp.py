# GHOST FIVE // VECTIS
# Implements a dependency-free Language Server Protocol endpoint for VECTIS editors.
"""VECTIS Language Server Protocol support over standard input and output."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import BinaryIO

from vectis import __version__
from vectis.action_profile import load_action_profile
from vectis.capability_config import capability_configuration
from vectis.compiler import compile_program
from vectis.diagnostic import Diagnostic, DiagnosticError
from vectis.editor import completion_items, document_symbols, hover_info
from vectis.formatter import format_program
from vectis.history import execution_history
from vectis.templates import template_catalog, template_preview
from vectis.lsp_workspace import (
    load_workspace_program,
    navigation_workspace,
    overlay_map,
    symbol_definition,
    symbol_references,
    symbol_rename,
    uri_path,
)
from vectis.lsp_semantic import (
    SEMANTIC_TOKEN_LEGEND,
    semantic_tokens,
)
from vectis.lsp_graph import graph_inspection
from vectis.lsp_position import source_span_to_lsp_range
from vectis.lsp_signature import signature_help
from vectis.modules import module_root_for
from vectis.parser import parse


_JSON_RPC_VERSION = "2.0"
_LSP_ERROR_METHOD_NOT_FOUND = -32601
_LSP_ERROR_INVALID_PARAMS = -32602
_LSP_ERROR_INTERNAL = -32603


def _uri_path(uri: str) -> Path | None:
    """Compatibility wrapper around the workspace URI resolver."""
    return uri_path(uri)


def _lsp_diagnostic(
    diagnostic: Diagnostic,
    *,
    source: str | None = None,
) -> dict[str, object]:
    """Translate one VECTIS diagnostic through the shared UTF-16 contract."""
    if source is None:
        start = diagnostic.span.start
        end = diagnostic.span.end
        converted = {
            "start": {
                "line": max(0, start.line - 1),
                "character": max(0, start.column - 1),
            },
            "end": {
                "line": max(0, end.line - 1),
                "character": max(0, end.column),
            },
        }
    else:
        converted = source_span_to_lsp_range(
            source,
            diagnostic.span,
        )

    return {
        "range": converted,
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

    def _diagnostic_source(
        self,
        diagnostic: Diagnostic,
        fallback: str | None,
    ) -> str | None:
        """Return the open or saved source that produced one diagnostic span."""
        file = diagnostic.span.file
        if file in self.documents:
            return self.documents[file]

        path = _uri_path(file)
        if path is None and not file.startswith("<"):
            path = Path(file)
        if path is not None:
            canonical = path.expanduser().resolve()
            overlays = overlay_map(self.documents)
            if canonical in overlays:
                return overlays[canonical]
            if canonical.is_file():
                return canonical.read_text(encoding="utf-8")
        return fallback

    def _diagnostics(self, uri: str, source: str) -> list[dict[str, object]]:
        file = uri
        try:
            path = _uri_path(uri)
            if path is None:
                program = parse(
                    source,
                    file=file,
                )
            else:
                program = load_workspace_program(
                    path,
                    overlays=overlay_map(
                        self.documents
                    ),
                ).program

            result = compile_program(program)
            return [
                _lsp_diagnostic(
                    diagnostic,
                    source=self._diagnostic_source(diagnostic, source),
                )
                for diagnostic in result.diagnostics
            ]
        except DiagnosticError as exc:
            return [_lsp_diagnostic(
                    exc.diagnostic,
                    source=self._diagnostic_source(exc.diagnostic, source),
                )]
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

    def _publish_open_diagnostics(
        self,
    ) -> list[dict[str, object]]:
        """Publish diagnostics for every open document deterministically."""
        return [
            self._publish_diagnostics(uri)
            for uri in sorted(
                self.documents
            )
        ]

    def _navigation_workspace(
        self,
        uri: str,
    ):
        """Resolve the widest open workspace containing one document."""
        path = _uri_path(uri)
        if path is None:
            return None
        return navigation_workspace(
            path,
            documents=self.documents,
        )

    def _graph_inspection(
        self,
        uri: str,
    ) -> dict[str, object]:
        """Compile the current editor workspace into a structural graph view."""
        source = self.documents.get(uri)
        try:
            path = _uri_path(uri)
            if path is None:
                if source is None:
                    return {"ok": False, "diagnostics": []}
                program = parse(source, file=uri)
            else:
                workspace = navigation_workspace(
                    path,
                    documents=self.documents,
                )
                program = workspace.program

            result = compile_program(program)
            if result.graph is None:
                return {
                    "ok": False,
                    "diagnostics": [
                        _lsp_diagnostic(
                    diagnostic,
                    source=self._diagnostic_source(diagnostic, source),
                )
                        for diagnostic in result.diagnostics
                    ],
                }

            return {
                "ok": True,
                "inspection": graph_inspection(result.graph),
            }
        except DiagnosticError as exc:
            return {
                "ok": False,
                "diagnostics": [_lsp_diagnostic(
                    exc.diagnostic,
                    source=self._diagnostic_source(exc.diagnostic, source),
                )],
            }
        except (OSError, UnicodeError, ValueError) as exc:
            return {
                "ok": False,
                "diagnostics": [
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
                ],
            }

    def _history_inspection(
        self,
        uri: str,
        directory: str,
        limit: int,
    ) -> dict[str, object]:
        """Inspect explicit project-local receipts without exposing raw JSON."""
        path = _uri_path(uri)
        if path is None:
            return {
                "ok": False,
                "error": (
                    "history inspection requires a file-backed document"
                ),
            }

        relative = Path(directory)
        if relative.is_absolute():
            return {
                "ok": False,
                "error": "history directory must be relative to the project root",
            }

        root = module_root_for(path)
        destination = (root / relative).resolve()
        try:
            destination.relative_to(root)
        except ValueError:
            return {
                "ok": False,
                "error": "history directory must remain inside the project root",
            }

        try:
            history = execution_history(
                destination,
                limit=limit,
            )
        except (
            OSError,
            UnicodeError,
            TypeError,
            ValueError,
        ) as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

        return {
            "ok": True,
            "history": history,
        }

    def _capability_configuration(
        self,
        uri: str,
        profile_name: str | None,
        capability_names: tuple[str, ...],
    ) -> dict[str, object]:
        """Preview explicit authority against the current editor workspace."""
        source = self.documents.get(uri)
        path = _uri_path(uri)
        if path is None:
            return {
                "ok": False,
                "error": (
                    "capability configuration requires a file-backed document"
                ),
            }

        try:
            root = module_root_for(path)
            profile = None
            if profile_name is not None:
                relative = Path(profile_name)
                if relative.is_absolute():
                    return {
                        "ok": False,
                        "error": (
                            "capability profile must be relative to the project root"
                        ),
                    }
                profile_path = (root / relative).resolve()
                try:
                    profile_path.relative_to(root)
                except ValueError:
                    return {
                        "ok": False,
                        "error": (
                            "capability profile must remain inside the project root"
                        ),
                    }
                profile = load_action_profile(profile_path)

            workspace = navigation_workspace(
                path,
                documents=self.documents,
            )
            result = compile_program(workspace.program)
            if result.graph is None:
                return {
                    "ok": False,
                    "diagnostics": [
                        _lsp_diagnostic(
                            diagnostic,
                            source=self._diagnostic_source(
                                diagnostic,
                                source,
                            ),
                        )
                        for diagnostic in result.diagnostics
                    ],
                }

            return {
                "ok": True,
                "configuration": capability_configuration(
                    result.graph,
                    profile=profile,
                    extra_capabilities=capability_names,
                ),
            }
        except DiagnosticError as exc:
            return {
                "ok": False,
                "diagnostics": [
                    _lsp_diagnostic(
                        exc.diagnostic,
                        source=self._diagnostic_source(
                            exc.diagnostic,
                            source,
                        ),
                    )
                ],
            }
        except (
            OSError,
            UnicodeError,
            TypeError,
            ValueError,
        ) as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

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
                            "definitionProvider": True,
                            "referencesProvider": True,
                            "renameProvider": True,
                            "signatureHelpProvider": {
                                "triggerCharacters": ["(", ","],
                                "retriggerCharacters": [","],
                            },
                            "semanticTokensProvider": {
                                "legend": SEMANTIC_TOKEN_LEGEND,
                                "full": True,
                            },
                            "executeCommandProvider": {
                                "commands": [
                                    "vectis.graph.inspect",
                                    "vectis.history.inspect",
                                    "vectis.capabilities.inspect",
                                    "vectis.templates.inspect",
                                ],
                            },
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
                    return self._publish_open_diagnostics()
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
                        return self._publish_open_diagnostics()
            return []

        if method == "textDocument/didSave":
            document = params.get("textDocument")
            if isinstance(document, dict):
                uri = document.get("uri")
                if isinstance(uri, str):
                    text = params.get("text")
                    if isinstance(text, str):
                        self.documents[uri] = text
                    return self._publish_open_diagnostics()
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
                        ),
                        *self._publish_open_diagnostics(),
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

        if method == "textDocument/signatureHelp":
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
                    workspace = None
                    if isinstance(uri, str):
                        try:
                            workspace = self._navigation_workspace(uri)
                        except (
                            DiagnosticError,
                            OSError,
                            UnicodeError,
                            ValueError,
                        ):
                            workspace = None

                    result = signature_help(
                        source,
                        line=line,
                        character=character,
                        workspace=workspace,
                        supplemental_sources=(
                            self.documents[item]
                            for item in sorted(self.documents)
                            if item != uri
                        ),
                    )
            return [_response(message_id, result)]

        if method == "textDocument/semanticTokens/full":
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

            result = (
                semantic_tokens(
                    source,
                    file=uri,
                )
                if (
                    source is not None
                    and isinstance(uri, str)
                )
                else {"data": []}
            )
            return [
                _response(
                    message_id,
                    result,
                )
            ]

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

        if method == "textDocument/definition":
            document = params.get("textDocument")
            position = params.get("position")
            uri = (
                document.get("uri")
                if isinstance(document, dict)
                else None
            )
            result = None
            if (
                isinstance(uri, str)
                and isinstance(position, dict)
            ):
                line = position.get("line")
                character = position.get(
                    "character"
                )
                path = _uri_path(uri)
                if (
                    path is not None
                    and isinstance(line, int)
                    and isinstance(
                        character,
                        int,
                    )
                ):
                    try:
                        workspace = (
                            self._navigation_workspace(
                                uri
                            )
                        )
                        if workspace is not None:
                            result = (
                                symbol_definition(
                                    workspace,
                                    path=path,
                                    line=line,
                                    character=character,
                                )
                            )
                    except (
                        DiagnosticError,
                        OSError,
                        UnicodeError,
                        ValueError,
                    ):
                        result = None
            return [
                _response(
                    message_id,
                    result,
                )
            ]

        if method == "textDocument/references":
            document = params.get("textDocument")
            position = params.get("position")
            context = params.get("context")
            uri = (
                document.get("uri")
                if isinstance(document, dict)
                else None
            )
            result: list[
                dict[str, object]
            ] = []
            if (
                isinstance(uri, str)
                and isinstance(position, dict)
            ):
                line = position.get("line")
                character = position.get(
                    "character"
                )
                path = _uri_path(uri)
                include_declaration = (
                    bool(
                        context.get(
                            "includeDeclaration",
                            False,
                        )
                    )
                    if isinstance(
                        context,
                        dict,
                    )
                    else False
                )
                if (
                    path is not None
                    and isinstance(line, int)
                    and isinstance(
                        character,
                        int,
                    )
                ):
                    try:
                        workspace = (
                            self._navigation_workspace(
                                uri
                            )
                        )
                        if workspace is not None:
                            result = (
                                symbol_references(
                                    workspace,
                                    path=path,
                                    line=line,
                                    character=character,
                                    include_declaration=(
                                        include_declaration
                                    ),
                                )
                            )
                    except (
                        DiagnosticError,
                        OSError,
                        UnicodeError,
                        ValueError,
                    ):
                        result = []
            return [
                _response(
                    message_id,
                    result,
                )
            ]

        if method == "textDocument/rename":
            document = params.get("textDocument")
            position = params.get("position")
            new_name = params.get("newName")
            uri = (
                document.get("uri")
                if isinstance(document, dict)
                else None
            )
            if (
                not isinstance(uri, str)
                or not isinstance(
                    position,
                    dict,
                )
                or not isinstance(
                    new_name,
                    str,
                )
            ):
                return [
                    _error_response(
                        message_id,
                        code=_LSP_ERROR_INVALID_PARAMS,
                        message=(
                            "rename requires a document, "
                            "position, and newName"
                        ),
                    )
                ]

            line = position.get("line")
            character = position.get(
                "character"
            )
            path = _uri_path(uri)
            if (
                path is None
                or not isinstance(line, int)
                or not isinstance(
                    character,
                    int,
                )
            ):
                return [
                    _error_response(
                        message_id,
                        code=_LSP_ERROR_INVALID_PARAMS,
                        message=(
                            "rename position must use "
                            "integer line and character"
                        ),
                    )
                ]

            try:
                workspace = (
                    self._navigation_workspace(
                        uri
                    )
                )
                result = (
                    symbol_rename(
                        workspace,
                        path=path,
                        line=line,
                        character=character,
                        new_name=new_name,
                    )
                    if workspace is not None
                    else None
                )
            except ValueError as exc:
                return [
                    _error_response(
                        message_id,
                        code=_LSP_ERROR_INVALID_PARAMS,
                        message=str(exc),
                    )
                ]
            except (
                DiagnosticError,
                OSError,
                UnicodeError,
            ):
                result = None

            return [
                _response(
                    message_id,
                    result,
                )
            ]

        if method == "workspace/executeCommand":
            command = params.get("command")
            arguments = params.get("arguments")

            if command not in {
                "vectis.graph.inspect",
                "vectis.history.inspect",
                "vectis.capabilities.inspect",
                "vectis.templates.inspect",
            }:
                return [
                    _error_response(
                        message_id,
                        code=_LSP_ERROR_INVALID_PARAMS,
                        message=(
                            "unsupported VECTIS command: "
                            f"{command}"
                        ),
                    )
                ]

            if command == "vectis.templates.inspect":
                if (
                    not isinstance(arguments, list)
                    or len(arguments) != 1
                    or not isinstance(arguments[0], dict)
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message=(
                                "vectis.templates.inspect requires one "
                                "argument object"
                            ),
                        )
                    ]

                template_name = arguments[0].get("name")
                if (
                    template_name is not None
                    and not isinstance(template_name, str)
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message="template name must be a string",
                        )
                    ]

                try:
                    payload = (
                        template_catalog()
                        if template_name is None
                        else template_preview(template_name)
                    )
                except ValueError as exc:
                    return [
                        _response(
                            message_id,
                            {
                                "ok": False,
                                "error": str(exc),
                            },
                        )
                    ]

                return [
                    _response(
                        message_id,
                        {
                            (
                                "catalog"
                                if template_name is None
                                else "template"
                            ): payload,
                            "ok": True,
                        },
                    )
                ]

            if command == "vectis.capabilities.inspect":
                if (
                    not isinstance(arguments, list)
                    or len(arguments) != 1
                    or not isinstance(arguments[0], dict)
                    or not isinstance(arguments[0].get("uri"), str)
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message=(
                                "vectis.capabilities.inspect requires one "
                                "argument object with uri"
                            ),
                        )
                    ]

                profile_name = arguments[0].get("profile")
                capability_names = arguments[0].get(
                    "capabilities",
                    [],
                )
                if (
                    profile_name is not None
                    and not isinstance(profile_name, str)
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message="capability profile must be a string",
                        )
                    ]
                if (
                    not isinstance(capability_names, list)
                    or any(
                        not isinstance(item, str)
                        or not item.strip()
                        for item in capability_names
                    )
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message=(
                                "capabilities must be an array of "
                                "non-empty strings"
                            ),
                        )
                    ]

                return [
                    _response(
                        message_id,
                        self._capability_configuration(
                            arguments[0]["uri"],
                            profile_name,
                            tuple(capability_names),
                        ),
                    )
                ]

            if command == "vectis.history.inspect":
                if (
                    not isinstance(arguments, list)
                    or len(arguments) != 1
                    or not isinstance(arguments[0], dict)
                    or not isinstance(arguments[0].get("uri"), str)
                    or not isinstance(arguments[0].get("directory"), str)
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message=(
                                "vectis.history.inspect requires one argument object "
                                "with uri and relative directory"
                            ),
                        )
                    ]

                limit = arguments[0].get("limit", 50)
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                ):
                    return [
                        _error_response(
                            message_id,
                            code=_LSP_ERROR_INVALID_PARAMS,
                            message="history limit must be an integer",
                        )
                    ]

                return [
                    _response(
                        message_id,
                        self._history_inspection(
                            arguments[0]["uri"],
                            arguments[0]["directory"],
                            limit,
                        ),
                    )
                ]

            if (
                not isinstance(arguments, list)
                or len(arguments) != 1
                or not isinstance(arguments[0], dict)
                or not isinstance(arguments[0].get("uri"), str)
            ):
                return [
                    _error_response(
                        message_id,
                        code=_LSP_ERROR_INVALID_PARAMS,
                        message=(
                            "vectis.graph.inspect requires "
                            "one argument object with uri"
                        ),
                    )
                ]

            uri = arguments[0]["uri"]
            return [
                _response(
                    message_id,
                    self._graph_inspection(uri),
                )
            ]

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
