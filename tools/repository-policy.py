#!/usr/bin/env python3
# GHOST FIVE // VECTIS
# Enforces repository branding, writing, comment, and public product standards.

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BRAND = "GHOST FIVE // VECTIS"
SLOGAN = (
    "A language for turning what you intend to happen into a system "
    "that can prove how it will happen."
)
SKIP_PARTS = {".git", ".venv", "venv", "build", "dist", "__pycache__"}
CODE_SUFFIXES = {
    ".py",
    ".sh",
    ".js",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
    ".vectis",
}
FORBIDDEN_PUBLIC_PATHS = (
    ".autonomy",
    "artifacts",
    "docs/submission",
    "tools/task-gates",
)
GENERIC_PHRASES = (
    "in today's fast paced world",
    "game changing",
    "revolutionary solution",
    "seamlessly integrates",
)
TRANSITIONAL_PHRASES = (
    " ".join(("active", "development")),
    " ".join(("public", "preview")),
    " ".join(("development", "line")),
    " ".join(("not", "yet")),
)
TRANSITIONAL_WORDS = tuple(
    "".join(parts)
    for parts in (
        ("n", "ew"),
        ("up", "dated"),
        ("ad", "ded"),
    )
)
PRERELEASE_MARKER = ".".join(("0", "1", "0", "dev0"))


def iter_files() -> list[Path]:
    """Return repository files that are part of the checked product surface."""
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def markdown_prose_violations(path: Path, text: str) -> list[str]:
    """Check branding and VECTIS prose rules outside fenced code blocks."""
    problems: list[str] = []
    relative = path.relative_to(ROOT)

    header = "\n".join(text.splitlines()[:12])
    if BRAND not in header:
        problems.append(f"{relative}: missing VECTIS brand header")
    if SLOGAN not in header:
        problems.append(f"{relative}: missing official VECTIS slogan")

    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if "—" in line or "–" in line:
            problems.append(
                f"{relative}:{number}: dash punctuation is not allowed in prose"
            )

        if re.match(r"^\s*-\s+", line):
            problems.append(
                f"{relative}:{number}: replace dash bullets with paragraphs, "
                "numbered lists, tables, or star bullets"
            )

        lowered = line.lower()
        for phrase in GENERIC_PHRASES:
            if phrase in lowered:
                problems.append(
                    f"{relative}:{number}: remove generic phrase {phrase!r}"
                )

        for phrase in TRANSITIONAL_PHRASES:
            if phrase in lowered:
                problems.append(
                    f"{relative}:{number}: remove transitional phrase {phrase!r}"
                )

        for word in TRANSITIONAL_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", lowered):
                problems.append(
                    f"{relative}:{number}: remove transitional word {word!r}"
                )

    return problems


def code_header_violations(path: Path, text: str) -> list[str]:
    """Require a VECTIS purpose header on code and configuration files."""
    if path.suffix.lower() not in CODE_SUFFIXES:
        return []

    head = "\n".join(text.splitlines()[:8])
    if BRAND not in head:
        return [
            f"{path.relative_to(ROOT)}: missing VECTIS code header"
        ]

    return []


def main() -> int:
    """Run repository policy checks and return a shell friendly exit code."""
    problems: list[str] = []

    for relative in FORBIDDEN_PUBLIC_PATHS:
        if (ROOT / relative).exists():
            problems.append(
                f"{relative}: internal path is not allowed in the public product tree"
            )

    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        relative = path.relative_to(ROOT)

        if PRERELEASE_MARKER in text:
            problems.append(
                f"{relative}: pre-release version marker is not allowed"
            )

        if path.suffix.lower() == ".md":
            problems.extend(markdown_prose_violations(path, text))

        problems.extend(code_header_violations(path, text))

    if problems:
        print("VECTIS REPOSITORY POLICY FAILED")
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print("VECTIS repository policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
