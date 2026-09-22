# GHOST FIVE // VECTIS
# Defines stable diagnostic codes, source spans, and structured errors.
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class DiagnosticCode(str, Enum):
    LEX_UNTERMINATED_STRING = "LEX001"
    LEX_UNSUPPORTED_BARE_OPERATOR = "LEX002"
    LEX_UNRECOGNIZED_CHARACTER = "LEX003"

    SYN_EXPECTED_STATEMENT = "SYN001"
    SYN_STANDALONE_OTHERWISE = "SYN002"
    SYN_EXPECTED_TOKEN = "SYN003"
    SYN_EXPECTED_EXPRESSION = "SYN004"
    SYN_UNCLOSED_BLOCK = "SYN005"
    SYN_MALFORMED_CITATIONS = "SYN006"
    SYN_INVALID_STATEMENT_KEYWORD = "SYN007"

    SEM_UNDECLARED_REFERENCE = "SEM001"
    SEM_DUPLICATE_DECLARATION = "SEM002"
    SEM_UNKNOWN_FUNCTION = "SEM003"
    SEM_INVALID_ARITY = "SEM004"
    SEM_TYPE_MISMATCH = "SEM005"
    SEM_IMPORT_RESOLUTION = "SEM006"
    SEM_ACTION_CONTRACT = "SEM007"

    CAP_UNAVAILABLE = "CAP001"
    CAP_INVALID_VALUE = "CAP002"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: DiagnosticCode
    severity: DiagnosticSeverity
    message: str
    span: SourceSpan

    def __post_init__(self) -> None:
        if not isinstance(self.code, DiagnosticCode):
            raise TypeError("Diagnostic.code must be DiagnosticCode")

        if not isinstance(self.severity, DiagnosticSeverity):
            raise TypeError("Diagnostic.severity must be DiagnosticSeverity")

        if not isinstance(self.message, str) or not self.message:
            raise ValueError("Diagnostic.message must be a non-empty string")

        if not isinstance(self.span, SourceSpan):
            raise TypeError("Diagnostic.span must be SourceSpan")

    @property
    def file(self) -> str:
        return self.span.file

    @property
    def line(self) -> int:
        return self.span.start.line

    @property
    def column(self) -> int:
        return self.span.start.column

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
            "source": {
                "file": self.span.file,
                "start": {
                    "line": self.span.start.line,
                    "column": self.span.start.column,
                },
                "end": {
                    "line": self.span.end.line,
                    "column": self.span.end.column,
                },
            },
        }

    def render(self) -> str:
        return (
            f"{self.file}:{self.line}:{self.column}: "
            f"{self.severity.value} {self.code.value}: "
            f"{self.message}"
        )


class DiagnosticError(ValueError):
    def __init__(self, diagnostic: Diagnostic) -> None:
        if not isinstance(diagnostic, Diagnostic):
            raise TypeError("diagnostic must be Diagnostic")

        self.diagnostic = diagnostic
        self.code = diagnostic.code.value
        self.severity = diagnostic.severity.value
        self.message = diagnostic.message
        self.span = diagnostic.span
        self.file = diagnostic.file
        self.line = diagnostic.line
        self.column = diagnostic.column

        # Preserve the established file:line:column: message exception shape.
        super().__init__(
            f"{self.file}:{self.line}:{self.column}: {self.message}"
        )

    def to_dict(self) -> dict[str, object]:
        return self.diagnostic.to_dict()


def point_span(*, file: str, line: int, column: int) -> SourceSpan:
    position = SourcePosition(
        line=line,
        column=column,
        file=file,
    )
    return SourceSpan(
        start=position,
        end=position,
    )


def error_diagnostic(
    *,
    code: DiagnosticCode,
    message: str,
    span: SourceSpan,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        span=span,
    )
