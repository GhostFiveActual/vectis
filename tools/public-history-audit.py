#!/usr/bin/env python3
# GHOST FIVE // VECTIS
# Audits the public repository tree and reachable Git history for retired private labels.

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    "__pycache__",
}
RETIRED_PUBLIC_LABELS = (
    "".join(("spec", "tral core")),
    "".join(("spec", "tral-core")),
)


def repository_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def text_contains_retired_label(text: str) -> bool:
    lowered = text.lower()
    return any(label in lowered for label in RETIRED_PUBLIC_LABELS)


def scan_tree() -> list[str]:
    problems: list[str] = []
    for path in repository_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if text_contains_retired_label(text):
            problems.append(
                f"{path.relative_to(ROOT)}: retired private label appears in public tree"
            )
    return problems


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "git command failed: "
            + " ".join(args)
            + "\n"
            + completed.stderr.strip()
        )
    return completed.stdout


def scan_reachable_history() -> list[str]:
    if not (ROOT / ".git").exists():
        return []

    problems: list[str] = []

    refs = git_output("for-each-ref", "--format=%(refname)")
    if text_contains_retired_label(refs):
        problems.append(
            "reachable Git ref contains a retired private label"
        )

    messages = git_output("log", "--all", "--format=%H%n%B%n%x00")
    if text_contains_retired_label(messages):
        problems.append(
            "reachable commit message contains a retired private label"
        )

    commits = [
        line.strip()
        for line in git_output("rev-list", "--all").splitlines()
        if line.strip()
    ]

    for commit in commits:
        for label in RETIRED_PUBLIC_LABELS:
            completed = subprocess.run(
                [
                    "git",
                    "grep",
                    "-I",
                    "-i",
                    "-n",
                    "-F",
                    label,
                    commit,
                    "--",
                    ".",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode == 0:
                problems.append(
                    f"{commit}: retired private label appears in reachable file history"
                )
                break
            if completed.returncode not in (0, 1):
                raise RuntimeError(
                    "git grep failed for reachable history audit"
                )

    return problems


def main() -> int:
    problems = [
        *scan_tree(),
        *scan_reachable_history(),
    ]

    if problems:
        print("VECTIS PUBLIC HISTORY AUDIT FAILED")
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print("VECTIS public history audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
