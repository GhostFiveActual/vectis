#!/usr/bin/env python3
# GHOST FIVE // VECTIS
# Runs the canonical VECTIS demonstration through the public compiler and runtime APIs.
"""Compile the canonical VECTIS submission demo and print its execution graph."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from vectis.compiler import compile_program
from vectis.parser import parse


DEMO_PATH = Path(__file__).with_name("demo.vectis")


def load_demo(path: Path = DEMO_PATH) -> str:
    """Return the demo source as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def compile_demo(path: Path = DEMO_PATH):
    """Parse and compile the demo, rejecting diagnostics or a missing graph."""
    source = load_demo(path)
    program = parse(source, file=str(path))
    result = compile_program(program)

    if result.diagnostics:
        rendered = "\n".join(str(item) for item in result.diagnostics)
        raise RuntimeError(
            "VECTIS demo compilation produced diagnostics:\n" + rendered
        )

    if result.graph is None:
        raise RuntimeError("VECTIS demo compilation produced no execution graph")

    return result


def render_graph(path: Path = DEMO_PATH) -> str:
    """Return the deterministic execution graph as JSON."""
    result = compile_demo(path)
    return result.graph.to_json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the canonical VECTIS submission demo and print "
            "its deterministic execution graph."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEMO_PATH,
        help="VECTIS source file to compile (default: demo.vectis)",
    )
    args = parser.parse_args(argv)

    try:
        print(render_graph(args.path))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"demo error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
