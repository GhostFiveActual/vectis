# GHOST FIVE // VECTIS
# Defines explicit capability declarations, validation, and compatibility helpers.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vectis.diagnostic import (
    DiagnosticCode,
    DiagnosticError,
    error_diagnostic,
    point_span,
)
from vectis.ir import ExecutionGraph
from vectis.source_span import SourceSpan


class CapabilityError(DiagnosticError):
    """Base class for capability validation and authorization errors."""

    def __init__(
        self,
        message: str,
        *,
        span: SourceSpan,
        code: DiagnosticCode = DiagnosticCode.CAP_INVALID_VALUE,
    ) -> None:
        super().__init__(
            error_diagnostic(
                code=code,
                message=message,
                span=span,
            )
        )


class CapabilityDenied(CapabilityError):
    """Raised when a required capability is explicitly unavailable."""

    def __init__(self, message: str, *, span: SourceSpan) -> None:
        super().__init__(
            message,
            span=span,
            code=DiagnosticCode.CAP_UNAVAILABLE,
        )


@dataclass(frozen=True, slots=True)
class Capability:
    """A named unit of runtime authority.

    Capability objects describe authority; they do not perform effects. Adapter
    configuration remains responsible for enforcing filesystem, process, or HTTP
    boundaries when a runtime handler performs an external action.
    """

    name: str
    description: str
    required: bool = False
    optional: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Capability name must be a non-empty string")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Capability description must be a non-empty string")
        if self.required and self.optional:
            raise ValueError("A capability cannot be both required and optional")


class CapabilityRegistry:
    """Registry of explicitly declared runtime capabilities."""

    def __init__(self) -> None:
        self.capabilities: dict[str, Capability] = {}
        # Retained as a compatibility alias for the v0.0.x public API.
        self.declared_capabilities = self.capabilities

    def declare_capability(self, capability: Capability) -> None:
        if not isinstance(capability, Capability):
            raise TypeError("Only Capability instances can be declared")
        if capability.name in self.capabilities:
            raise ValueError(f"Capability '{capability.name}' already declared")
        self.capabilities[capability.name] = capability

    def get_capability(self, name: str) -> Capability | None:
        self._validate_name(name)
        return self.capabilities.get(name)

    def has_capability(self, name: str) -> bool:
        self._validate_name(name)
        return name in self.capabilities

    def check_capabilities(
        self,
        execution_graph: ExecutionGraph,
    ) -> list[DiagnosticError]:
        """Validate graph metadata that references declared capabilities.

        This compatibility API checks only explicit capability metadata already
        present on graph nodes. Runtime `require`/`request` nodes are validated by
        the runtime against its granted capability set.
        """

        if not isinstance(execution_graph, ExecutionGraph):
            raise TypeError("execution_graph must be ExecutionGraph")

        diagnostics: list[DiagnosticError] = []
        span = point_span(file="<capability>", line=1, column=1)

        for node in execution_graph.nodes:
            for key, value in node.metadata:
                capability = self.capabilities.get(key)
                if capability is None:
                    continue

                if capability.required and value is None:
                    diagnostics.append(
                        CapabilityDenied(
                            f"Required capability '{key}' is unavailable",
                            span=span,
                        )
                    )
                    continue

                if capability.optional and value is None:
                    continue

                if not self._is_scalar(value):
                    diagnostics.append(
                        CapabilityError(
                            f"Invalid value for capability '{key}': {value!r}",
                            span=span,
                        )
                    )

        return diagnostics

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Capability name must be a non-empty string")

    @staticmethod
    def _is_scalar(value: object) -> bool:
        return isinstance(value, (str, int, float, bool, type(None)))


class CapabilityChecker:
    """Compatibility wrapper around :class:`CapabilityRegistry`."""

    def __init__(self, model: CapabilityRegistry) -> None:
        if not isinstance(model, CapabilityRegistry):
            raise TypeError("model must be CapabilityRegistry")
        self.model = model

    def check(self, execution_graph: ExecutionGraph) -> list[DiagnosticError]:
        return self.model.check_capabilities(execution_graph)


class CapabilityResolver:
    """Resolve declared capability metadata from an execution graph."""

    def __init__(self, model: CapabilityRegistry) -> None:
        if not isinstance(model, CapabilityRegistry):
            raise TypeError("model must be CapabilityRegistry")
        self.model = model

    def resolve(self, execution_graph: ExecutionGraph) -> dict[str, Any]:
        if not isinstance(execution_graph, ExecutionGraph):
            raise TypeError("execution_graph must be ExecutionGraph")

        result: dict[str, Any] = {}
        for node in execution_graph.nodes:
            for key, value in node.metadata:
                capability = self.model.capabilities.get(key)
                if capability is None:
                    continue
                result[key] = value
        return result


# v0.0.x compatibility alias. CapabilityRegistry is canonical.
CapabilityModel = CapabilityRegistry
