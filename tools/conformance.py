# GHOST FIVE // VECTIS
# Runs the product conformance suite against canonical VECTIS examples and contracts.
#!/usr/bin/env python3
"""Deterministic VECTIS language conformance checks."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Iterable

from vectis.compiler import compile_program
from vectis.lexer import Lexer, LexerError
from vectis.parser import ParserError, parse


@dataclass(frozen=True)
class ConformanceResult:
    """One deterministic conformance result."""

    name: str
    phase: str
    passed: bool
    detail: str = ""


POSITIVE_LEXICAL_FIXTURES: tuple[str, ...] = (
    'mission "Lexical" { source value 1; publish value; }',
    (
        'mission "Operators" { '
        'source score 1 + 2 * 3; '
        'when score >= 1 { publish score; } '
        '}'
    ),
)

POSITIVE_SYNTAX_FIXTURES: tuple[str, ...] = (
    '''
mission "Syntax" {
    source x 1;
    source y x + 1;
    publish y;
}
''',
    '''
mission "Conditional" {
    source ready true;

    when ready {
        publish "yes";
    } otherwise {
        publish "no";
    }
}
''',
    '''
mission "Capability syntax" {
    require "filesystem";
    request "network";
    publish "done";
}
''',
)

NEGATIVE_SYNTAX_FIXTURES: tuple[str, ...] = (
    'mission "Missing semicolon" { publish "x" }',
    'otherwise { publish "x"; }',
    'mission "Unclosed" { publish "x";',
)

POSITIVE_SEMANTIC_FIXTURES: tuple[str, ...] = (
    '''
mission "Semantic" {
    source x 1;
    source y x + 1;
    publish y;
}
''',
    '''
mission "Branch semantics" {
    source ready true;
    source result "complete";

    when ready {
        publish result;
    } otherwise {
        publish "fallback";
    }
}
''',
)

NEGATIVE_SEMANTIC_FIXTURES: tuple[str, ...] = (
    '''
mission "Unresolved reference" {
    publish missing;
}
''',
    '''
mission "Unsupported semantic statement" {
    confidence true;
}
''',
)

REGRESSION_FIXTURES: tuple[str, ...] = (
    '''
mission "Regression source ordering" {
    source x 5;
    source y x + 1;
    publish y;
}
''',
    '''
mission "Regression condition" {
    source enabled true;

    when enabled {
        publish "enabled";
    } otherwise {
        publish "disabled";
    }
}
''',
)


def check_lexical(source: str) -> None:
    """Require a source fixture to tokenize successfully."""

    Lexer(
        source,
        file="<conformance>",
    ).tokenize()


def check_syntax(source: str) -> None:
    """Require a source fixture to parse successfully."""

    parse(
        source,
        file="<conformance>",
    )


def check_semantic_valid(source: str) -> None:
    """Require a fixture to compile without semantic diagnostics."""

    program = parse(
        source,
        file="<conformance>",
    )

    result = compile_program(program)

    if result.diagnostics:
        raise AssertionError(
            "unexpected semantic diagnostics: "
            + "; ".join(
                str(item)
                for item in result.diagnostics
            )
        )

    if result.graph is None:
        raise AssertionError(
            "semantic-valid fixture produced no graph"
        )


def check_semantic_invalid(source: str) -> None:
    """Require a fixture to parse but fail deterministic semantics."""

    program = parse(
        source,
        file="<conformance>",
    )

    result = compile_program(program)

    if not result.diagnostics:
        raise AssertionError(
            "semantic-invalid fixture produced no diagnostics"
        )

    if result.graph is not None:
        raise AssertionError(
            "semantic-invalid fixture unexpectedly produced a graph"
        )


def _positive_results(
    phase: str,
    fixtures: Iterable[str],
    checker: Callable[[str], None],
) -> list[ConformanceResult]:
    results: list[ConformanceResult] = []

    for index, source in enumerate(fixtures, 1):
        name = f"{phase}-positive-{index}"

        try:
            checker(source)
        except Exception as exc:
            results.append(
                ConformanceResult(
                    name=name,
                    phase=phase,
                    passed=False,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
        else:
            results.append(
                ConformanceResult(
                    name=name,
                    phase=phase,
                    passed=True,
                )
            )

    return results


def run_conformance() -> tuple[ConformanceResult, ...]:
    """Run the deterministic VECTIS conformance matrix."""

    results: list[ConformanceResult] = []

    results.extend(
        _positive_results(
            "lexical",
            POSITIVE_LEXICAL_FIXTURES,
            check_lexical,
        )
    )

    results.extend(
        _positive_results(
            "syntax",
            POSITIVE_SYNTAX_FIXTURES,
            check_syntax,
        )
    )

    for index, source in enumerate(
        NEGATIVE_SYNTAX_FIXTURES,
        1,
    ):
        name = f"syntax-negative-{index}"

        try:
            parse(
                source,
                file="<conformance>",
            )
        except (LexerError, ParserError):
            results.append(
                ConformanceResult(
                    name=name,
                    phase="syntax",
                    passed=True,
                )
            )
        else:
            results.append(
                ConformanceResult(
                    name=name,
                    phase="syntax",
                    passed=False,
                    detail=(
                        "invalid syntax was unexpectedly accepted"
                    ),
                )
            )

    results.extend(
        _positive_results(
            "semantic",
            POSITIVE_SEMANTIC_FIXTURES,
            check_semantic_valid,
        )
    )

    results.extend(
        _positive_results(
            "semantic-invalid",
            NEGATIVE_SEMANTIC_FIXTURES,
            check_semantic_invalid,
        )
    )

    results.extend(
        _positive_results(
            "regression",
            REGRESSION_FIXTURES,
            check_semantic_valid,
        )
    )

    return tuple(results)


def conformance_passes() -> bool:
    """Return true only when every conformance fixture passes."""

    return all(
        result.passed
        for result in run_conformance()
    )


def main() -> int:
    """Command-line conformance entry point."""

    results = run_conformance()

    for result in results:
        status = "PASS" if result.passed else "FAIL"

        print(
            json.dumps(
                {
                    "name": result.name,
                    "phase": result.phase,
                    "status": status,
                    "detail": result.detail,
                },
                sort_keys=True,
            )
        )

    if all(result.passed for result in results):
        print("VECTIS CONFORMANCE PASSED")
        return 0

    print("VECTIS CONFORMANCE FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
