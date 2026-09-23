# GHOST FIVE // VECTIS
# Implements the VECTIS command line interface and command routing.
"""VECTIS command line interface."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any, Sequence

from vectis import __version__
from vectis.action_profile import (
    load_action_profile,
    profile_manifest,
)
from vectis.actions import standard_action_manifest
from vectis.ast import Mission
from vectis.capabilities import Capability, CapabilityRegistry
from vectis.compiler import CompileResult, compile_program
from vectis.demo_app import run_demo_app
from vectis.evaluator import builtin_manifest, evaluate_expression
from vectis.examples import CANONICAL_EXAMPLES, example_manifest
from vectis.formatter import format_program
from vectis.history import execution_history
from vectis.capability_config import capability_configuration
from vectis.module_browser import browse_project_modules
from vectis.templates import (
    template_catalog,
    template_preview,
    write_project_template,
)
from vectis.lexer import Lexer, LexerError
from vectis.modules import ModuleError, load_program_file
from vectis.parser import ParserError, parse, parse_expression
from vectis.product import (
    enforce_graph_limits,
    execution_report_html,
    execution_timeline,
    graph_fingerprint,
    graph_summary,
    graph_to_dot,
    graph_to_mermaid,
    initialize_project,
    node_stage_name,
    plan_audit,
    test_project,
)
from vectis.profile_attestation import (
    action_profile_attestation,
)
from vectis.receipt import (
    execution_receipt,
    write_execution_receipt,
)
from vectis.runtime import Runtime


_CAPABILITY_DESCRIPTIONS = {
    "filesystem": "Controlled filesystem adapter boundary.",
    "process": "Allowlisted structured process adapter boundary.",
    "http": "Bounded HTTP request adapter boundary.",
}


def _jsonable(value: Any) -> Any:
    """Convert public VECTIS values into deterministic JSON safe data."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            key: _jsonable(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _read_source(source: str) -> tuple[str, str]:
    """Read source from a file path or standard input."""
    if source == "-":
        return sys.stdin.read(), "<stdin>"
    path = Path(source)
    return path.read_text(encoding="utf-8"), str(path)


def _print_json(value: object) -> None:
    """Print stable human readable JSON for CLI and script consumers."""
    print(
        json.dumps(
            _jsonable(value),
            indent=2,
            sort_keys=True,
        )
    )


def _print_diagnostics(result: CompileResult) -> None:
    """Render compiler diagnostics to standard error."""
    for diagnostic in result.diagnostics:
        print(str(diagnostic), file=sys.stderr)


def _program_for_compilation(
    source: str,
):
    """Load one source program, resolving file imports when available."""
    if source == "-":
        text, file = _read_source(source)
        return parse(text, file=file), file, ()

    loaded = load_program_file(
        Path(source),
    )
    return (
        loaded.program,
        str(loaded.entry),
        tuple(str(path) for path in loaded.modules),
    )


def _compile_source(source: str):
    """Parse, resolve modules, and compile one source input."""
    program, _file, _modules = _program_for_compilation(
        source
    )
    result = compile_program(program)
    if result.graph is None or result.diagnostics:
        _print_diagnostics(result)
        return None
    return result.graph


def _capability_registry(
    names: Sequence[str],
) -> CapabilityRegistry | None:
    """Build an explicit runtime capability registry from CLI grants."""
    if not names:
        return None

    registry = CapabilityRegistry()
    for name in dict.fromkeys(names):
        registry.declare_capability(
            Capability(
                name=name,
                description=_CAPABILITY_DESCRIPTIONS.get(
                    name,
                    "Explicit CLI capability grant.",
                ),
            )
        )
    return registry


def _selected_action_profile(
    args: argparse.Namespace,
):
    """Load the explicitly selected action profile once."""
    profile_path = getattr(
        args,
        "actions_config",
        None,
    )
    return (
        load_action_profile(profile_path)
        if profile_path
        else None
    )


def _runtime_authority(
    args: argparse.Namespace,
    *,
    profile=None,
):
    """Resolve explicit CLI capability grants and one selected action profile."""
    if profile is None:
        profile = _selected_action_profile(
            args
        )
    names = [
        *(
            profile.capabilities
            if profile is not None
            else ()
        ),
        *getattr(args, "capability", ()),
    ]
    return (
        _capability_registry(names),
        (
            profile.actions
            if profile is not None
            else None
        ),
    )


def command_actions(args: argparse.Namespace) -> int:
    """Inspect standard action contracts or one explicit local profile."""
    if args.config is None:
        _print_json(
            {
                "configured": False,
                "standard_actions": standard_action_manifest(),
            }
        )
        return 0

    profile = load_action_profile(
        args.config
    )
    _print_json(
        {
            "configured": True,
            **profile_manifest(profile),
            "attestation": (
                action_profile_attestation(
                    profile
                )
            ),
        }
    )
    return 0


def command_check(args: argparse.Namespace) -> int:
    """Validate syntax and semantics without executing the mission."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1
    if args.details:
        _print_json(
            {
                "status": "ok",
                "source": args.source,
                "summary": graph_summary(graph),
            }
        )
    else:
        print("OK")
    return 0


def command_tokens(args: argparse.Namespace) -> int:
    """Emit the deterministic token stream."""
    text, file = _read_source(args.source)
    _print_json(Lexer(text, file=file).tokenize())
    return 0


def command_parse(args: argparse.Namespace) -> int:
    """Emit the typed abstract syntax tree."""
    text, file = _read_source(args.source)
    _print_json(parse(text, file=file))
    return 0


def command_plan(args: argparse.Namespace) -> int:
    """Compile source and emit the execution graph as JSON."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1
    print(graph.to_json())
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    """Emit source syntax plus the resolved compilation plan."""
    text, file = _read_source(args.source)
    tokens = Lexer(text, file=file).tokenize()
    source_program = parse(text, file=file)
    program, resolved_file, modules = _program_for_compilation(
        args.source
    )
    result = compile_program(program)
    _print_json(
        {
            "version": __version__,
            "source": resolved_file,
            "modules": modules,
            "tokens": tokens,
            "ast": source_program,
            "resolved_ast": (
                program
                if modules
                else source_program
            ),
            "diagnostics": result.diagnostics,
            "execution_graph": (
                result.graph.to_dict()
                if result.graph is not None
                else None
            ),
        }
    )
    return 0 if result.ok else 1


def _receipt_authority(
    capabilities: CapabilityRegistry | None,
    actions: object | None,
) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    """Return value-free authority evidence for a receipt."""
    granted = (
        tuple(
            sorted(
                capabilities.capabilities
            )
        )
        if capabilities is not None
        else ()
    )

    if actions is None:
        return granted, ()

    manifest = getattr(
        actions,
        "manifest",
        None,
    )
    if not callable(manifest):
        return granted, ()

    registered: list[dict[str, str]] = []
    for item in manifest():
        operation = item.get("operation")
        capability = item.get("capability")
        if (
            isinstance(operation, str)
            and operation
            and isinstance(capability, str)
            and capability
        ):
            registered.append(
                {
                    "operation": operation,
                    "capability": capability,
                }
            )

    return granted, tuple(registered)


def _execution_receipt(
    *,
    graph: object,
    result: object,
    source_name: str,
    capabilities: CapabilityRegistry | None,
    actions: object | None,
    selected_profile=None,
) -> dict[str, object]:
    """Build one CLI receipt without runtime values."""
    granted, registered = _receipt_authority(
        capabilities,
        actions,
    )
    return execution_receipt(
        graph,
        result,
        source_name=source_name,
        granted_capabilities=granted,
        registered_actions=registered,
        action_profile_attestation=(
            action_profile_attestation(
                selected_profile
            )
            if selected_profile is not None
            else None
        ),
    )


def command_run(args: argparse.Namespace) -> int:
    """Compile and execute one VECTIS mission."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    selected_profile = (
        _selected_action_profile(args)
    )
    capabilities, actions = _runtime_authority(
        args,
        profile=selected_profile,
    )
    result = Runtime(
        graph,
        dry_run=args.dry_run,
        capabilities=capabilities,
        actions=actions,
    ).execute()

    if args.receipt:
        write_execution_receipt(
            args.receipt,
            _execution_receipt(
                graph=graph,
                result=result,
                source_name=args.source,
                capabilities=capabilities,
                actions=actions,
                selected_profile=selected_profile,
            ),
        )

    _print_json(result)
    return 0 if result.success else 1


def command_receipt(args: argparse.Namespace) -> int:
    """Execute one mission and emit value-free provenance."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    selected_profile = (
        _selected_action_profile(args)
    )
    capabilities, actions = _runtime_authority(
        args,
        profile=selected_profile,
    )
    result = Runtime(
        graph,
        dry_run=args.dry_run,
        capabilities=capabilities,
        actions=actions,
    ).execute()
    receipt = _execution_receipt(
        graph=graph,
        result=result,
        source_name=args.source,
        capabilities=capabilities,
        actions=actions,
        selected_profile=selected_profile,
    )

    if args.output:
        destination = write_execution_receipt(
            args.output,
            receipt,
        )
        print(destination)
    else:
        _print_json(receipt)

    return 0 if result.success else 1


def command_history(args: argparse.Namespace) -> int:
    """Inspect explicitly persisted value-free execution receipts."""
    _print_json(
        execution_history(
            Path(args.directory),
            limit=args.limit,
        )
    )
    return 0


def command_capability_config(args: argparse.Namespace) -> int:
    """Preview explicit runtime authority against one compiled mission."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    profile = (
        load_action_profile(args.actions_config)
        if args.actions_config
        else None
    )
    preview = capability_configuration(
        graph,
        profile=profile,
        extra_capabilities=args.capability,
    )
    _print_json(preview)
    return 0 if preview["satisfied"] else 1


def _terminal_value(value: object, *, limit: int = 34) -> str:
    """Render a compact scalar value for Mission Control."""
    rendered = json.dumps(_jsonable(value), ensure_ascii=False)
    if len(rendered) <= limit:
        return rendered
    return rendered[: limit - 1] + "…"


def _program_mission_name(program: object, fallback: str) -> str:
    """Return the first declared mission name for operator presentation."""
    for statement in getattr(program, "statements", ()):
        if isinstance(statement, Mission):
            return statement.name
    return fallback


def _render_mission_control(
    *,
    mission_name: str,
    source_name: str,
    graph: object,
    result: object,
) -> None:
    """Render a human focused Ghost Five execution view."""
    states = dict(result.node_states)
    values = dict(result.node_values)
    width = 74

    print("╔" + "═" * width + "╗")
    print("║ " + "GHOST FIVE // VECTIS".ljust(width - 1) + "║")
    print("║ " + "MISSION CONTROL".ljust(width - 1) + "║")
    print("╠" + "═" * width + "╣")
    print("║ " + "A language for turning what you intend to happen into a system".ljust(width - 1) + "║")
    print("║ " + "that can prove how it will happen.".ljust(width - 1) + "║")
    print("╚" + "═" * width + "╝")
    print()
    print(f"MISSION        {mission_name}")
    print(f"SOURCE         {source_name}")
    print(
        "EXECUTION      "
        + ("COMPLETE" if result.success else "FAILED")
    )
    summary = graph_summary(graph)
    print(
        f"GRAPH          {summary['nodes']} nodes // "
        f"{summary['edges']} edges"
    )
    print(
        f"PLAN           {summary['levels']} levels // "
        f"width {summary['max_width']} // "
        f"fan-out {summary['max_fan_out']}"
    )
    print(f"FINGERPRINT    {summary['fingerprint'][:24]}…")
    print()

    print(f"STAGES         {summary['stage_count']}")
    print()

    active_stage: str | None = None
    for node in graph.nodes:
        stage = node_stage_name(node) or "Mission"
        if stage != active_stage:
            if active_stage is not None:
                print()
            print(f"STAGE          {stage}")
            print("─" * width)
            active_stage = stage

        state = states[node.id].value.upper()
        value = (
            _terminal_value(values[node.id])
            if node.id in values
            else ""
        )
        marker = {
            "SUCCEEDED": "✓",
            "FAILED": "✕",
            "BLOCKED": "■",
            "SKIPPED": "○",
            "DRY_RUN": "◇",
        }.get(state, "•")
        print(
            f"{marker} {node.id:<28} "
            f"{state:<12} {value}"
        )

    published = [
        values[node.id]
        for node in graph.nodes
        if node.kind.value == "publish"
        and node.id in values
        and states[node.id].value == "succeeded"
    ]

    print()
    print("RESULT")
    if published:
        for value in published:
            print(_terminal_value(value, limit=72))
    elif result.success:
        print("Mission completed without a published value.")
    else:
        for failure in result.failures:
            print(f"{failure.node_id}: {failure.message}")


def command_mission(args: argparse.Namespace) -> int:
    """Execute a mission and render the Ghost Five operator view."""
    program, file, _modules = _program_for_compilation(
        args.source
    )
    compiled = compile_program(program)

    if compiled.graph is None or compiled.diagnostics:
        _print_diagnostics(compiled)
        return 1

    capabilities, actions = _runtime_authority(
        args
    )
    result = Runtime(
        compiled.graph,
        dry_run=args.dry_run,
        capabilities=capabilities,
        actions=actions,
    ).execute()

    _render_mission_control(
        mission_name=_program_mission_name(
            program,
            Path(file).stem,
        ),
        source_name=file,
        graph=compiled.graph,
        result=result,
    )
    return 0 if result.success else 1


def command_fmt(args: argparse.Namespace) -> int:
    """Print, check, or write canonical VECTIS formatting."""
    text, file = _read_source(args.source)
    formatted = format_program(parse(text, file=file))

    if args.check:
        if text == formatted:
            print("OK")
            return 0
        print(
            f"vectis: formatting required: {file}",
            file=sys.stderr,
        )
        return 1

    if args.write:
        if args.source == "-":
            print(
                "vectis: --write requires a file path",
                file=sys.stderr,
            )
            return 2
        Path(args.source).write_text(
            formatted,
            encoding="utf-8",
        )
        print(args.source)
        return 0

    sys.stdout.write(formatted)
    return 0


def command_builtins(_args: argparse.Namespace) -> int:
    """List the deterministic built in function registry."""
    _print_json({"builtins": builtin_manifest()})
    return 0


def command_capabilities(_args: argparse.Namespace) -> int:
    """List standard VECTIS capability names."""
    _print_json(
        {
            "capabilities": [
                {
                    "name": name,
                    "description": description,
                }
                for name, description in sorted(
                    _CAPABILITY_DESCRIPTIONS.items()
                )
            ]
        }
    )
    return 0


def command_doctor(_args: argparse.Namespace) -> int:
    """Report the local VECTIS runtime environment."""
    _print_json(
        {
            "vectis": __version__,
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "builtins": len(builtin_manifest()),
            "capabilities": sorted(
                _CAPABILITY_DESCRIPTIONS
            ),
        }
    )
    return 0


def command_eval(args: argparse.Namespace) -> int:
    """Evaluate a pure VECTIS expression from the command line."""
    value = evaluate_expression(
        parse_expression(
            args.expression,
            file="<cli-expression>",
        ),
        {},
    )
    _print_json(
        {
            "expression": args.expression,
            "value": value,
        }
    )
    return 0


def command_graph(args: argparse.Namespace) -> int:
    """Export a compiled graph in JSON, DOT, or Mermaid form."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    if args.format == "json":
        print(graph.to_json())
    elif args.format == "dot":
        sys.stdout.write(graph_to_dot(graph))
    else:
        sys.stdout.write(graph_to_mermaid(graph))
    return 0


def command_explain(args: argparse.Namespace) -> int:
    """Explain the structural shape of a compiled mission."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    _print_json(
        {
            "source": args.source,
            "summary": graph_summary(graph),
        }
    )
    return 0


def command_modules(args: argparse.Namespace) -> int:
    """Inspect one import graph or browse the project module catalog."""
    if args.source == "-":
        raise ValueError(
            "vectis modules requires a file path"
        )

    if args.browse:
        _print_json(
            browse_project_modules(
                Path(args.source),
            )
        )
        return 0

    loaded = load_program_file(
        Path(args.source),
    )
    relative_modules = [
        path.relative_to(loaded.root).as_posix()
        for path in loaded.modules
    ]
    _print_json(
        {
            "entry": loaded.entry.relative_to(
                loaded.root
            ).as_posix(),
            "root": str(loaded.root),
            "modules": relative_modules,
            "module_count": len(relative_modules),
        }
    )
    return 0


def _render_plan_audit(
    source_name: str,
    audit: dict[str, object],
) -> None:
    """Render a readable pre-execution audit for a compiled plan."""
    summary = audit["summary"]
    capabilities = audit["capabilities"]
    stages = audit["stages"]

    print("╔" + "═" * 74 + "╗")
    print("║ " + "GHOST FIVE // VECTIS".ljust(73) + "║")
    print("║ " + "PLAN AUDIT".ljust(73) + "║")
    print("╚" + "═" * 74 + "╝")
    print()
    print(f"SOURCE         {source_name}")
    print(f"FINGERPRINT    {audit['fingerprint']}")
    print(
        f"GRAPH          {summary['nodes']} nodes // "
        f"{summary['edges']} edges // "
        f"{summary['levels']} levels"
    )
    print(
        f"SHAPE          width {summary['max_width']} // "
        f"fan-in {summary['max_fan_in']} // "
        f"fan-out {summary['max_fan_out']}"
    )
    print(
        f"BRANCHING      {summary['branch_edges']} branch edges"
    )
    print()

    required = capabilities["required"]
    requested = capabilities["requested"]
    unresolved = capabilities["unresolved_nodes"]

    print("CAPABILITY FOOTPRINT")
    print(
        "  required      "
        + (", ".join(required) if required else "none")
    )
    print(
        "  requested     "
        + (", ".join(requested) if requested else "none")
    )
    print(
        "  unresolved    "
        + (", ".join(unresolved) if unresolved else "none")
    )
    print()

    print("STAGE DISTRIBUTION")
    for stage in stages:
        kinds = ", ".join(
            f"{name}:{count}"
            for name, count in stage["node_kinds"].items()
        )
        print(
            f"  {stage['name']:<28} "
            f"{stage['nodes']:>4} nodes  {kinds}"
        )


def command_audit(args: argparse.Namespace) -> int:
    """Audit a compiled plan before execution."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    audit = plan_audit(graph)
    if args.json:
        _print_json(
            {
                "source": args.source,
                "audit": audit,
            }
        )
    else:
        _render_plan_audit(args.source, audit)
    return 0


def command_fingerprint(args: argparse.Namespace) -> int:
    """Print the stable SHA-256 fingerprint of a compiled plan."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1
    print(graph_fingerprint(graph))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    """Verify repeated compilation and dry-run scheduling are deterministic."""
    if not 2 <= args.runs <= 100:
        raise ValueError("--runs must be between 2 and 100")

    fingerprints: list[str] = []
    schedule_signatures: list[str] = []
    first_summary: dict[str, object] | None = None

    for _ in range(args.runs):
        program, _file, _modules = _program_for_compilation(
            args.source
        )
        compiled = compile_program(program)
        if compiled.graph is None or compiled.diagnostics:
            _print_diagnostics(compiled)
            return 1

        graph = compiled.graph
        fingerprints.append(graph_fingerprint(graph))
        if first_summary is None:
            first_summary = graph_summary(graph)

        runtime = Runtime(graph, dry_run=True).execute()
        schedule_signatures.append(
            json.dumps(
                {
                    "execution_order": list(runtime.execution_order),
                    "node_states": [
                        [node_id, state.value]
                        for node_id, state in runtime.node_states
                    ],
                    "node_values": list(runtime.node_values),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    fingerprint_stable = len(set(fingerprints)) == 1
    schedule_stable = len(set(schedule_signatures)) == 1
    deterministic = fingerprint_stable and schedule_stable

    _print_json(
        {
            "deterministic": deterministic,
            "runs": args.runs,
            "fingerprint": fingerprints[0],
            "fingerprint_stable": fingerprint_stable,
            "dry_run_schedule_stable": schedule_stable,
            "summary": first_summary,
        }
    )
    return 0 if deterministic else 1


def command_diff(args: argparse.Namespace) -> int:
    """Compare two compiled execution plans without running them."""
    left = _compile_source(args.left)
    if left is None:
        return 1

    right = _compile_source(args.right)
    if right is None:
        return 1

    left_summary = graph_summary(left)
    right_summary = graph_summary(right)
    left_fingerprint = graph_fingerprint(left)
    right_fingerprint = graph_fingerprint(right)

    keys = (
        "nodes",
        "edges",
        "depth",
        "max_width",
        "max_fan_in",
        "max_fan_out",
    )
    delta = {
        key: right_summary[key] - left_summary[key]
        for key in keys
    }

    _print_json(
        {
            "same": left_fingerprint == right_fingerprint,
            "left": {
                "source": args.left,
                "fingerprint": left_fingerprint,
                "summary": left_summary,
            },
            "right": {
                "source": args.right,
                "fingerprint": right_fingerprint,
                "summary": right_summary,
            },
            "delta": delta,
        }
    )
    return 0


def command_limits(args: argparse.Namespace) -> int:
    """Validate a compiled plan against explicit complexity budgets."""
    graph = _compile_source(args.source)
    if graph is None:
        return 1

    result = enforce_graph_limits(
        graph,
        max_nodes=args.max_nodes,
        max_edges=args.max_edges,
        max_depth=args.max_depth,
        max_width=args.max_width,
        max_fan_in=args.max_fan_in,
        max_fan_out=args.max_fan_out,
    )
    _print_json(result)
    return 0 if result["ok"] else 1


def command_timeline(args: argparse.Namespace) -> int:
    """Execute a mission and print runtime state grouped by graph level."""
    program, file, _modules = _program_for_compilation(
        args.source
    )
    compiled = compile_program(program)

    if compiled.graph is None or compiled.diagnostics:
        _print_diagnostics(compiled)
        return 1

    capabilities, actions = _runtime_authority(
        args
    )
    result = Runtime(
        compiled.graph,
        dry_run=args.dry_run,
        capabilities=capabilities,
        actions=actions,
    ).execute()

    _print_json(
        {
            "source": file,
            "success": result.success,
            "fingerprint": graph_fingerprint(compiled.graph),
            "timeline": execution_timeline(
                compiled.graph,
                result,
            ),
        }
    )
    return 0 if result.success else 1


def command_report(args: argparse.Namespace) -> int:
    """Execute a mission and write a standalone HTML execution report."""
    program, file, _modules = _program_for_compilation(
        args.source
    )
    compiled = compile_program(program)

    if compiled.graph is None or compiled.diagnostics:
        _print_diagnostics(compiled)
        return 1

    capabilities, actions = _runtime_authority(
        args
    )
    result = Runtime(
        compiled.graph,
        dry_run=args.dry_run,
        capabilities=capabilities,
        actions=actions,
    ).execute()
    mission_name = _program_mission_name(
        program,
        Path(file).stem,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        execution_report_html(
            compiled.graph,
            result,
            mission_name=mission_name,
            source_name=file,
        ),
        encoding="utf-8",
    )
    print(output)
    return 0 if result.success else 1


def command_init(args: argparse.Namespace) -> int:
    """Create a Ghost Five branded VECTIS project scaffold."""
    if args.template is None:
        created = initialize_project(
            Path(args.path),
            force=args.force,
        )
    else:
        created = write_project_template(
            args.template,
            Path(args.path),
            force=args.force,
        )

    payload = {
        "root": str(Path(args.path).resolve()),
        "created": [
            str(path)
            for path in created
        ],
    }
    if args.template is not None:
        payload["template"] = args.template
    _print_json(payload)
    return 0


def command_test(args: argparse.Namespace) -> int:
    """Compile every VECTIS source file below a project path."""
    result = test_project(Path(args.path))
    _print_json(result)
    return 0 if result["failed"] == 0 else 1


def command_templates(args: argparse.Namespace) -> int:
    """List or preview deterministic built-in VECTIS project templates."""
    if args.name is None:
        _print_json(template_catalog())
        return 0

    _print_json(
        template_preview(args.name)
    )
    return 0


def command_examples(args: argparse.Namespace) -> int:
    """List or print the canonical VECTIS examples."""
    if args.name is None:
        _print_json(
            {
                "examples": example_manifest(),
            }
        )
        return 0

    source = CANONICAL_EXAMPLES.get(args.name)
    if source is None:
        print(
            f"vectis: unknown example {args.name!r}",
            file=sys.stderr,
        )
        return 2

    sys.stdout.write(source)
    return 0


def command_repl(_args: argparse.Namespace) -> int:
    """Run a small deterministic expression REPL with local scalar variables."""
    values: dict[str, object] = {}
    assignment = re.compile(
        r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?!=)(.+)$"
    )

    print(
        "VECTIS REPL // :quit exits // :vars prints variables"
    )

    while True:
        try:
            line = input("vectis> ").strip()
        except EOFError:
            print()
            return 0

        if not line:
            continue
        if line in {":quit", ":exit"}:
            return 0
        if line == ":vars":
            _print_json(values)
            continue

        match = assignment.match(line)
        expression_text = line
        target = None

        if match is not None:
            target = match.group(1)
            expression_text = match.group(2).strip()

        try:
            value = evaluate_expression(
                parse_expression(
                    expression_text,
                    file="<repl>",
                ),
                values,
            )
        except Exception as exc:
            print(
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            continue

        if target is not None:
            values[target] = value
            print(f"{target} = {json.dumps(value)}")
        else:
            _print_json(value)


def command_studio(args: argparse.Namespace) -> int:
    """Launch the local VECTIS Studio workbench."""
    from vectis.studio import run_studio

    run_studio(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        allow_remote=args.allow_remote,
    )
    return 0


def command_demo(args: argparse.Namespace) -> int:
    """Launch the VECTIS Launch Control application."""
    run_demo_app(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        allow_remote=args.allow_remote,
    )
    return 0


def command_lsp(_args: argparse.Namespace) -> int:
    """Run the VECTIS Language Server Protocol endpoint over stdio."""
    from vectis.lsp import serve

    return serve()


def command_version(_args: argparse.Namespace) -> int:
    """Print only the installed VECTIS version."""
    print(__version__)
    return 0


def _add_source_argument(
    command: argparse.ArgumentParser,
) -> None:
    """Add the standard VECTIS source file argument to a parser."""
    command.add_argument(
        "source",
        nargs="?",
        default="-",
        metavar="FILE",
        help=(
            "VECTIS source file; use '-' or omit FILE "
            "to read standard input"
        ),
    )


def _add_server_arguments(
    command: argparse.ArgumentParser,
    *,
    default_port: int,
) -> None:
    """Add common local application server arguments."""
    command.add_argument(
        "--host",
        default="127.0.0.1",
    )
    command.add_argument(
        "--port",
        type=int,
        default=default_port,
    )
    command.add_argument(
        "--no-browser",
        action="store_true",
    )
    command.add_argument(
        "--allow-remote",
        action="store_true",
        help=(
            "permit binding to a non-loopback interface"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the complete VECTIS command line grammar."""
    parser = argparse.ArgumentParser(
        prog="vectis",
        description=(
            "VECTIS deterministic automation language, Mission Control runtime, "
            "project tooling, and application interfaces."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="display the VECTIS version and exit",
    )

    commands = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
    )

    check_parser = commands.add_parser(
        "check",
        help="validate syntax and semantics",
    )
    _add_source_argument(check_parser)
    check_parser.add_argument(
        "--details",
        action="store_true",
        help="print structural plan metrics after successful validation",
    )
    check_parser.set_defaults(handler=command_check)

    tokens_parser = commands.add_parser(
        "tokens",
        help="print the lexer token stream as JSON",
    )
    _add_source_argument(tokens_parser)
    tokens_parser.set_defaults(handler=command_tokens)

    parse_parser = commands.add_parser(
        "parse",
        help="parse source and print its AST as JSON",
    )
    _add_source_argument(parse_parser)
    parse_parser.set_defaults(handler=command_parse)

    plan_parser = commands.add_parser(
        "plan",
        help="compile source into an execution graph",
    )
    _add_source_argument(plan_parser)
    plan_parser.set_defaults(handler=command_plan)

    inspect_parser = commands.add_parser(
        "inspect",
        help="show tokens, AST, diagnostics, and graph",
    )
    _add_source_argument(inspect_parser)
    inspect_parser.set_defaults(handler=command_inspect)

    run_parser = commands.add_parser(
        "run",
        help="compile and execute VECTIS source",
    )
    _add_source_argument(run_parser)
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "produce deterministic runtime states without "
            "invoking handlers"
        ),
    )
    run_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "grant a named runtime capability; may be repeated"
        ),
    )
    run_parser.add_argument(
        "--actions-config",
        metavar="FILE",
        help=(
            "explicit TOML action authority profile; "
            "no profile is discovered automatically"
        ),
    )
    run_parser.add_argument(
        "--receipt",
        metavar="FILE",
        help=(
            "write a value-free execution receipt "
            "without changing run JSON output"
        ),
    )
    run_parser.set_defaults(handler=command_run)

    receipt_parser = commands.add_parser(
        "receipt",
        help="execute source and emit a value-free execution receipt",
    )
    _add_source_argument(receipt_parser)
    receipt_parser.add_argument(
        "--output",
        metavar="FILE",
        help="write receipt JSON to FILE instead of standard output",
    )
    receipt_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "record deterministic scheduling without "
            "invoking handlers"
        ),
    )
    receipt_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="NAME",
        help="grant a named runtime capability; may be repeated",
    )
    receipt_parser.add_argument(
        "--actions-config",
        metavar="FILE",
        help=(
            "explicit TOML action authority profile; "
            "no profile is discovered automatically"
        ),
    )
    receipt_parser.set_defaults(
        handler=command_receipt
    )

    history_parser = commands.add_parser(
        "history",
        help="inspect explicit value-free execution receipt history",
    )
    history_parser.add_argument(
        "directory",
        metavar="DIRECTORY",
        help="directory containing persisted execution receipt JSON files",
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="maximum valid receipts to return; default: 50",
    )
    history_parser.set_defaults(
        handler=command_history
    )

    capability_config_parser = commands.add_parser(
        "capability-config",
        help="preview explicit authority against a compiled mission",
    )
    _add_source_argument(capability_config_parser)
    capability_config_parser.add_argument(
        "--actions-config",
        metavar="FILE",
        help="explicit TOML action authority profile to inspect",
    )
    capability_config_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="NAME",
        help="explicit capability grant to preview; may be repeated",
    )
    capability_config_parser.set_defaults(
        handler=command_capability_config
    )

    mission_parser = commands.add_parser(
        "mission",
        help="execute VECTIS source in the Ghost Five Mission Control view",
    )
    _add_source_argument(mission_parser)
    mission_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show deterministic scheduling without invoking handlers",
    )
    mission_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="NAME",
        help="grant a named runtime capability; may be repeated",
    )
    mission_parser.add_argument(
        "--actions-config",
        metavar="FILE",
        help=(
            "explicit TOML action authority profile; "
            "no profile is discovered automatically"
        ),
    )
    mission_parser.set_defaults(handler=command_mission)

    fmt_parser = commands.add_parser(
        "fmt",
        help="format VECTIS source canonically",
    )
    _add_source_argument(fmt_parser)
    mode = fmt_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="fail when formatting differs",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="rewrite the source file in place",
    )
    fmt_parser.set_defaults(handler=command_fmt)

    eval_parser = commands.add_parser(
        "eval",
        help="evaluate one pure VECTIS expression",
    )
    eval_parser.add_argument(
        "expression",
        help="VECTIS expression to evaluate",
    )
    eval_parser.set_defaults(handler=command_eval)

    graph_parser = commands.add_parser(
        "graph",
        help="export the execution graph",
    )
    _add_source_argument(graph_parser)
    graph_parser.add_argument(
        "--format",
        choices=("json", "dot", "mermaid"),
        default="json",
        help="graph output format",
    )
    graph_parser.set_defaults(handler=command_graph)

    explain_parser = commands.add_parser(
        "explain",
        help="summarize a compiled mission",
    )
    _add_source_argument(explain_parser)
    explain_parser.set_defaults(handler=command_explain)

    modules_parser = commands.add_parser(
        "modules",
        help="inspect one import graph or browse project modules",
    )
    _add_source_argument(modules_parser)
    modules_parser.add_argument(
        "--browse",
        action="store_true",
        help="browse every project-bounded VECTIS source module",
    )
    modules_parser.set_defaults(handler=command_modules)

    audit_parser = commands.add_parser(
        "audit",
        help="inspect complexity, stages, capabilities, and plan identity",
    )
    _add_source_argument(audit_parser)
    audit_parser.add_argument(
        "--json",
        action="store_true",
        help="emit the complete audit as structured JSON",
    )
    audit_parser.set_defaults(handler=command_audit)

    fingerprint_parser = commands.add_parser(
        "fingerprint",
        help="print the stable SHA-256 execution plan fingerprint",
    )
    _add_source_argument(fingerprint_parser)
    fingerprint_parser.set_defaults(handler=command_fingerprint)

    verify_parser = commands.add_parser(
        "verify",
        help="prove repeated compilation and dry-run scheduling are stable",
    )
    _add_source_argument(verify_parser)
    verify_parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="number of deterministic verification passes; default: 5",
    )
    verify_parser.set_defaults(handler=command_verify)

    diff_parser = commands.add_parser(
        "diff",
        help="compare two compiled execution plans",
    )
    diff_parser.add_argument("left", metavar="LEFT")
    diff_parser.add_argument("right", metavar="RIGHT")
    diff_parser.set_defaults(handler=command_diff)

    limits_parser = commands.add_parser(
        "limits",
        help="validate plan node, edge, and depth budgets",
    )
    _add_source_argument(limits_parser)
    limits_parser.add_argument("--max-nodes", type=int)
    limits_parser.add_argument("--max-edges", type=int)
    limits_parser.add_argument("--max-depth", type=int)
    limits_parser.add_argument("--max-width", type=int)
    limits_parser.add_argument(
        "--max-fan-in",
        type=int,
        default=None,
        help="reject plans whose maximum fan-in exceeds this value",
    )
    limits_parser.add_argument(
        "--max-fan-out",
        type=int,
        default=None,
        help="reject plans whose maximum fan-out exceeds this value",
    )
    limits_parser.set_defaults(handler=command_limits)

    timeline_parser = commands.add_parser(
        "timeline",
        help="execute and group runtime state by deterministic graph level",
    )
    _add_source_argument(timeline_parser)
    timeline_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show deterministic scheduling without invoking handlers",
    )
    timeline_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="NAME",
        help="grant a named runtime capability; may be repeated",
    )
    timeline_parser.add_argument(
        "--actions-config",
        metavar="FILE",
        help=(
            "explicit TOML action authority profile; "
            "no profile is discovered automatically"
        ),
    )
    timeline_parser.set_defaults(handler=command_timeline)

    report_parser = commands.add_parser(
        "report",
        help="execute a mission and write a standalone HTML execution report",
    )
    _add_source_argument(report_parser)
    report_parser.add_argument(
        "--output",
        default="vectis-report.html",
        help="HTML report destination",
    )
    report_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report deterministic scheduling without invoking handlers",
    )
    report_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        metavar="NAME",
        help="grant a named runtime capability; may be repeated",
    )
    report_parser.add_argument(
        "--actions-config",
        metavar="FILE",
        help=(
            "explicit TOML action authority profile; "
            "no profile is discovered automatically"
        ),
    )
    report_parser.set_defaults(handler=command_report)

    init_parser = commands.add_parser(
        "init",
        help="create a Ghost Five branded VECTIS project",
    )
    init_parser.add_argument(
        "path",
        nargs="?",
        default=".",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="replace scaffold files that already exist",
    )
    init_parser.add_argument(
        "--template",
        metavar="NAME",
        help=(
            "materialize one deterministic built-in project template; "
            "default init behavior is unchanged when omitted"
        ),
    )
    init_parser.set_defaults(handler=command_init)

    test_parser = commands.add_parser(
        "test",
        help="compile every VECTIS file under a path",
    )
    test_parser.add_argument(
        "path",
        nargs="?",
        default=".",
    )
    test_parser.set_defaults(handler=command_test)

    templates_parser = commands.add_parser(
        "templates",
        help="list or preview deterministic built-in project templates",
    )
    templates_parser.add_argument(
        "name",
        nargs="?",
    )
    templates_parser.set_defaults(
        handler=command_templates
    )

    examples_parser = commands.add_parser(
        "examples",
        help="list or print canonical VECTIS examples",
    )
    examples_parser.add_argument(
        "name",
        nargs="?",
    )
    examples_parser.set_defaults(handler=command_examples)

    repl_parser = commands.add_parser(
        "repl",
        help="open the deterministic expression REPL",
    )
    repl_parser.set_defaults(handler=command_repl)

    builtins_parser = commands.add_parser(
        "builtins",
        help="list deterministic built in functions",
    )
    builtins_parser.set_defaults(handler=command_builtins)

    actions_parser = commands.add_parser(
        "actions",
        help="inspect standard actions or an explicit action profile",
    )
    actions_parser.add_argument(
        "--config",
        metavar="FILE",
        help="TOML action profile to validate and inspect",
    )
    actions_parser.set_defaults(
        handler=command_actions
    )

    capabilities_parser = commands.add_parser(
        "capabilities",
        help="list standard capability names",
    )
    capabilities_parser.set_defaults(
        handler=command_capabilities
    )

    doctor_parser = commands.add_parser(
        "doctor",
        help="show local VECTIS environment information",
    )
    doctor_parser.set_defaults(handler=command_doctor)

    lsp_parser = commands.add_parser(
        "lsp",
        help="run the VECTIS Language Server Protocol endpoint over stdio",
    )
    lsp_parser.set_defaults(handler=command_lsp)

    version_parser = commands.add_parser(
        "version",
        help="print the installed VECTIS version",
    )
    version_parser.set_defaults(handler=command_version)

    for command_name in ("studio", "app"):
        studio_parser = commands.add_parser(
            command_name,
            help="launch VECTIS Mission Control Studio",
        )
        _add_server_arguments(
            studio_parser,
            default_port=8765,
        )
        studio_parser.set_defaults(handler=command_studio)

    demo_parser = commands.add_parser(
        "demo",
        aliases=["showcase"],
        help="launch the VECTIS Launch Control demo",
    )
    _add_server_arguments(
        demo_parser,
        default_port=8775,
    )
    demo_parser.set_defaults(handler=command_demo)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the VECTIS CLI and normalize user facing failures."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)

    if handler is None:
        parser.print_help()
        return 0

    try:
        return int(handler(args))
    except (LexerError, ParserError, ModuleError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"vectis: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
