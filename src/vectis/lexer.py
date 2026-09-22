# GHOST FIVE // VECTIS
# Tokenizes VECTIS source into deterministic tokens with source locations.
"""Reference lexer for the VECTIS language."""

from __future__ import annotations

from vectis.diagnostic import (
    DiagnosticCode,
    DiagnosticError,
    error_diagnostic,
    point_span,
)
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan
from vectis.token import Token


KEYWORDS = frozenset(
    {
        "mission",
        "stage",
        "source",
        "let",
        "analyze",
        "when",
        "otherwise",
        "publish",
        "request",
        "require",
        "assert",
        "citations",
        "confidence",
        "function",
        "return",
        "import",
        "action",
        "using",
    }
)

PUNCTUATION = frozenset(
    {
        "{",
        "}",
        "(",
        ")",
        "[",
        "]",
        ";",
        ",",
        ":",
        ".",
    }
)

MULTI_OPERATORS = frozenset(
    {
        ">=",
        "<=",
        "==",
        "!=",
        "&&",
        "||",
    }
)

SINGLE_OPERATORS = frozenset(
    {
        "+",
        "-",
        "*",
        "/",
        "%",
        "!",
        "<",
        ">",
    }
)

UNSUPPORTED_OPERATOR_PREFIXES = frozenset(
    {
        "=",
        "&",
        "|",
    }
)


class LexerError(DiagnosticError):
    pass


class Lexer:
    """Tokenize VECTIS source according to the lexical specification."""

    def __init__(
        self,
        source: str,
        file: str = "<memory>",
    ) -> None:
        if not isinstance(source, str):
            raise TypeError(
                "source must be a string"
            )

        if not isinstance(file, str) or not file:
            raise ValueError(
                "file must be a non-empty string"
            )

        self.source = source
        self.file = file

        self.index = 0
        self.line = 1
        self.column = 1

        self.last_line = 1
        self.last_column = 1

        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        """Return the complete semantic token stream."""

        while not self._at_end():
            char = self._current()

            if char in " \t\r\n":
                self._consume_whitespace()
                continue

            if char == "/" and self._peek() == "/":
                self._consume_comment()
                continue

            if char == '"':
                self._consume_string()
                continue

            if self._is_identifier_start(char):
                self._consume_identifier()
                continue

            if self._starts_number():
                self._consume_number()
                continue

            if char in PUNCTUATION:
                self._consume_punctuation()
                continue

            if self._operator_starts_here():
                self._consume_operator()
                continue

            if char in UNSUPPORTED_OPERATOR_PREFIXES:
                self._error(
                    f"unsupported bare operator {char!r}",
                    code=DiagnosticCode.LEX_UNSUPPORTED_BARE_OPERATOR,
                )

            self._error(
                f"unrecognized character {char!r}",
                code=DiagnosticCode.LEX_UNRECOGNIZED_CHARACTER,
            )

        return list(self.tokens)

    def _at_end(self) -> bool:
        return self.index >= len(self.source)

    def _current(self) -> str:
        if self._at_end():
            return ""

        return self.source[self.index]

    def _peek(
        self,
        offset: int = 1,
    ) -> str:
        target = self.index + offset

        if target >= len(self.source):
            return ""

        return self.source[target]

    def _advance(self) -> str:
        char = self._current()

        if not char:
            return ""

        self.last_line = self.line
        self.last_column = self.column
        self.index += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def _position(self) -> SourcePosition:
        return SourcePosition(
            line=self.line,
            column=self.column,
            file=self.file,
        )

    def _span(
        self,
        start: SourcePosition,
    ) -> SourceSpan:
        end = SourcePosition(
            line=self.last_line,
            column=self.last_column,
            file=self.file,
        )

        return SourceSpan(
            start=start,
            end=end,
        )

    def _emit(
        self,
        token_type: str,
        value: str,
        start: SourcePosition,
    ) -> None:
        self.tokens.append(
            Token(
                type=token_type,
                value=value,
                span=self._span(start),
            )
        )

    def _error(
        self,
        message: str,
        *,
        code: DiagnosticCode,
        position: SourcePosition | None = None,
    ) -> None:
        location = (
            position
            if position is not None
            else self._position()
        )

        raise LexerError(
            error_diagnostic(
                code=code,
                message=message,
                span=point_span(
                    file=location.file,
                    line=location.line,
                    column=location.column,
                ),
            )
        )

    @staticmethod
    def _is_ascii_letter(
        char: str,
    ) -> bool:
        return (
            "a" <= char <= "z"
            or "A" <= char <= "Z"
        )

    @classmethod
    def _is_identifier_start(
        cls,
        char: str,
    ) -> bool:
        return (
            cls._is_ascii_letter(char)
            or char == "_"
        )

    @classmethod
    def _is_identifier_continue(
        cls,
        char: str,
    ) -> bool:
        return (
            cls._is_identifier_start(char)
            or "0" <= char <= "9"
        )

    def _consume_whitespace(self) -> None:
        while (
            not self._at_end()
            and self._current() in " \t\r\n"
        ):
            self._advance()

    def _consume_comment(self) -> None:
        self._advance()
        self._advance()

        while (
            not self._at_end()
            and self._current() != "\n"
        ):
            self._advance()

    def _consume_string(self) -> None:
        start = self._position()

        # Opening quote.
        self._advance()

        characters: list[str] = []

        while not self._at_end():
            char = self._current()

            if char == '"':
                self._advance()

                self._emit(
                    "string",
                    "".join(characters),
                    start,
                )
                return

            characters.append(
                self._advance()
            )

        self._error(
            "unterminated string literal",
            code=DiagnosticCode.LEX_UNTERMINATED_STRING,
            position=start,
        )

    def _consume_identifier(self) -> None:
        start = self._position()
        start_index = self.index

        self._advance()

        while (
            not self._at_end()
            and self._is_identifier_continue(
                self._current()
            )
        ):
            self._advance()

        value = self.source[
            start_index:self.index
        ]

        token_type = (
            "keyword"
            if value in KEYWORDS
            else "identifier"
        )

        self._emit(
            token_type,
            value,
            start,
        )

    def _starts_number(self) -> bool:
        char = self._current()

        if "0" <= char <= "9":
            return True

        return (
            char in {"+", "-"}
            and "0" <= self._peek() <= "9"
        )

    def _consume_number(self) -> None:
        start = self._position()
        start_index = self.index

        if self._current() in {"+", "-"}:
            self._advance()

        while (
            not self._at_end()
            and "0" <= self._current() <= "9"
        ):
            self._advance()

        if (
            not self._at_end()
            and self._current() == "."
            and "0" <= self._peek() <= "9"
        ):
            self._advance()

            while (
                not self._at_end()
                and "0" <= self._current() <= "9"
            ):
                self._advance()

        if (
            not self._at_end()
            and self._current() == "."
            and "0" <= self._peek() <= "9"
        ):
            self._error(
                "numeric literal contains more than one decimal point",
                code=DiagnosticCode.LEX_UNRECOGNIZED_CHARACTER,
            )

        value = self.source[
            start_index:self.index
        ]

        self._emit(
            "number",
            value,
            start,
        )

    def _consume_punctuation(self) -> None:
        start = self._position()
        value = self._advance()

        self._emit(
            "punctuation",
            value,
            start,
        )

    def _operator_starts_here(self) -> bool:
        pair = (
            self._current()
            + self._peek()
        )

        return (
            pair in MULTI_OPERATORS
            or self._current()
            in SINGLE_OPERATORS
        )

    def _consume_operator(self) -> None:
        start = self._position()

        pair = (
            self._current()
            + self._peek()
        )

        if pair in MULTI_OPERATORS:
            value = (
                self._advance()
                + self._advance()
            )
        else:
            value = self._advance()

        self._emit(
            "operator",
            value,
            start,
        )
