# GHOST FIVE // VECTIS
# Defines project-relative identity and binding metadata for module functions.
"""Module-scoped pure-function identity for resolved VECTIS programs."""

from __future__ import annotations

from dataclasses import dataclass

from vectis.source_span import SourceSpan


@dataclass(frozen=True, slots=True, order=True)
class ModuleFunctionId:
    """Stable project-relative identity for one pure function."""

    module: str
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.module, str) or not self.module:
            raise ValueError("ModuleFunctionId.module must not be empty")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("ModuleFunctionId.name must not be empty")

    @property
    def label(self) -> str:
        """Return a deterministic project-relative display label."""
        return f"{self.module}::{self.name}"


@dataclass(frozen=True, slots=True)
class FunctionSelectorBinding:
    """Bind one selective-import name to its module-scoped function."""

    span: SourceSpan
    name: str
    target: ModuleFunctionId

    def __post_init__(self) -> None:
        if not isinstance(self.span, SourceSpan):
            raise TypeError("FunctionSelectorBinding.span must be SourceSpan")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("FunctionSelectorBinding.name must not be empty")
        if not isinstance(self.target, ModuleFunctionId):
            raise TypeError(
                "FunctionSelectorBinding.target must be ModuleFunctionId"
            )


@dataclass(frozen=True, slots=True)
class ModuleFunctionScope:
    """Resolved declarations, calls, and selectors for one module graph."""

    declarations: tuple[
        tuple[SourceSpan, ModuleFunctionId],
        ...,
    ] = ()
    calls: tuple[
        tuple[SourceSpan, ModuleFunctionId],
        ...,
    ] = ()
    selectors: tuple[FunctionSelectorBinding, ...] = ()

    def declaration_id(
        self,
        span: SourceSpan,
    ) -> ModuleFunctionId | None:
        """Return the identity bound to one declaration span."""
        for candidate, identity in self.declarations:
            if candidate == span:
                return identity
        return None

    def call_target(
        self,
        span: SourceSpan,
    ) -> ModuleFunctionId | None:
        """Return the identity bound to one call span."""
        for candidate, identity in self.calls:
            if candidate == span:
                return identity
        return None

    def selector_target(
        self,
        span: SourceSpan,
        name: str,
    ) -> ModuleFunctionId | None:
        """Return the identity bound to one selective-import name."""
        for binding in self.selectors:
            if binding.span == span and binding.name == name:
                return binding.target
        return None
