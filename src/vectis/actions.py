# GHOST FIVE // VECTIS
# Defines explicit action registration and bounded standard adapter bindings.
"""Explicit external action registry for VECTIS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from vectis.adapters.filesystem import FileSystemAdapter
from vectis.adapters.http import HttpAdapter
from vectis.adapters.process import ProcessAdapter
from vectis.action_contract import (
    ActionContract,
    standard_action_contract,
    standard_action_manifest,
    validate_value,
)
from vectis.evaluator import Value, is_value


ActionHandler = Callable[[dict[str, Value]], Value]


STANDARD_ACTION_BINDINGS = tuple(
    (
        item["operation"],
        item["capability"],
    )
    for item in standard_action_manifest()
)


class ActionError(RuntimeError):
    """Base error for explicit VECTIS action execution."""


class ActionUnavailable(ActionError):
    """Raised when an action operation has not been registered."""


class ActionCapabilityMismatch(ActionError):
    """Raised when source authority disagrees with the registered operation."""


@dataclass(frozen=True, slots=True)
class ActionSpec:
    """One registered external operation and its required capability."""

    operation: str
    capability: str
    handler: ActionHandler
    contract: ActionContract | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("ActionSpec.operation must be a non-empty string")
        if not isinstance(self.capability, str) or not self.capability:
            raise ValueError("ActionSpec.capability must be a non-empty string")
        if not callable(self.handler):
            raise TypeError("ActionSpec.handler must be callable")
        if self.contract is not None:
            if not isinstance(
                self.contract,
                ActionContract,
            ):
                raise TypeError(
                    "ActionSpec.contract must be ActionContract or None"
                )
            if self.contract.operation != self.operation:
                raise ValueError(
                    "ActionSpec.contract operation must match registration"
                )
            if self.contract.capability != self.capability:
                raise ValueError(
                    "ActionSpec.contract capability must match registration"
                )


class ActionRegistry:
    """Registry that binds each action operation to one explicit capability."""

    def __init__(self) -> None:
        self._specs: dict[str, ActionSpec] = {}

    def register(
        self,
        operation: str,
        capability: str,
        handler: ActionHandler,
        *,
        contract: ActionContract | None = None,
    ) -> None:
        spec = ActionSpec(
            operation=operation,
            capability=capability,
            handler=handler,
            contract=contract,
        )
        if operation in self._specs:
            raise ValueError(
                f"Action operation is already registered: {operation!r}"
            )
        self._specs[operation] = spec

    def get(self, operation: str) -> ActionSpec | None:
        if not isinstance(operation, str) or not operation:
            raise ValueError("action operation must be a non-empty string")
        return self._specs.get(operation)

    def manifest(self) -> tuple[dict[str, object], ...]:
        items: list[dict[str, object]] = []
        for spec in sorted(
            self._specs.values(),
            key=lambda item: item.operation,
        ):
            item: dict[str, object] = {
                "operation": spec.operation,
                "capability": spec.capability,
            }
            if spec.contract is not None:
                item["contract"] = (
                    spec.contract.to_dict()
                )
            items.append(item)
        return tuple(items)

    def execute(
        self,
        operation: str,
        capability: str,
        arguments: object,
    ) -> Value:
        spec = self.get(operation)
        if spec is None:
            raise ActionUnavailable(
                f"Action operation {operation!r} is unavailable"
            )
        if capability != spec.capability:
            raise ActionCapabilityMismatch(
                (
                    f"Action operation {operation!r} requires capability "
                    f"{spec.capability!r}, not {capability!r}"
                )
            )
        if not isinstance(arguments, dict):
            raise ActionError(
                f"Action operation {operation!r} requires object input"
            )
        if spec.contract is not None:
            validate_value(
                spec.contract.input_schema,
                arguments,
                path=f"{operation} input",
            )
        result = spec.handler(arguments)
        if not is_value(result):
            raise ActionError(
                (
                    f"Action operation {operation!r} returned a value "
                    "outside the VECTIS value model"
                )
            )
        if spec.contract is not None:
            validate_value(
                spec.contract.result_schema,
                result,
                path=f"{operation} result",
            )
        return result

    def register_filesystem(
        self,
        adapter: FileSystemAdapter,
    ) -> None:
        if not isinstance(adapter, FileSystemAdapter):
            raise TypeError("adapter must be FileSystemAdapter")

        def read_text(arguments: dict[str, Value]) -> Value:
            path = _required_string(
                arguments,
                "path",
                "filesystem.read_text",
            )
            return adapter.read_text(path)

        def write_text(arguments: dict[str, Value]) -> Value:
            path = _required_string(
                arguments,
                "path",
                "filesystem.write_text",
            )
            content = _required_string(
                arguments,
                "content",
                "filesystem.write_text",
            )
            adapter.write_text(path, content)
            return {
                "path": path,
                "written": True,
                "characters": len(content),
            }

        self.register(
            "filesystem.read_text",
            adapter.capability,
            read_text,
            contract=standard_action_contract(
                "filesystem.read_text"
            ),
        )
        self.register(
            "filesystem.write_text",
            adapter.capability,
            write_text,
            contract=standard_action_contract(
                "filesystem.write_text"
            ),
        )

    def register_process(
        self,
        adapter: ProcessAdapter,
    ) -> None:
        if not isinstance(adapter, ProcessAdapter):
            raise TypeError("adapter must be ProcessAdapter")

        def run(arguments: dict[str, Value]) -> Value:
            executable = _required_string(
                arguments,
                "executable",
                "process.run",
            )
            raw_arguments = arguments.get("arguments", ())
            if not isinstance(raw_arguments, (list, tuple)):
                raise ActionError(
                    "process.run arguments must be a list of strings"
                )
            argv = tuple(raw_arguments)
            if not all(isinstance(item, str) for item in argv):
                raise ActionError(
                    "process.run arguments must be a list of strings"
                )
            raw_timeout = arguments.get("timeout")
            timeout = None
            if raw_timeout is not None:
                if isinstance(raw_timeout, bool) or not isinstance(
                    raw_timeout,
                    (int, float),
                ):
                    raise ActionError(
                        "process.run timeout must be numeric"
                    )
                timeout = float(raw_timeout)

            result = adapter.run(
                executable,
                argv,
                timeout=timeout,
            )
            return {
                "argv": tuple(result.argv),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        self.register(
            "process.run",
            adapter.capability,
            run,
            contract=standard_action_contract(
                "process.run"
            ),
        )

    def register_http(
        self,
        adapter: HttpAdapter,
    ) -> None:
        if not isinstance(adapter, HttpAdapter):
            raise TypeError("adapter must be HttpAdapter")

        def request(arguments: dict[str, Value]) -> Value:
            method = _required_string(
                arguments,
                "method",
                "http.request",
            )
            url = _required_string(
                arguments,
                "url",
                "http.request",
            )

            raw_headers = arguments.get("headers", {})
            if not isinstance(raw_headers, dict) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in raw_headers.items()
            ):
                raise ActionError(
                    "http.request headers must be an object of strings"
                )

            raw_timeout = arguments.get("timeout")
            timeout = None
            if raw_timeout is not None:
                if isinstance(raw_timeout, bool) or not isinstance(
                    raw_timeout,
                    (int, float),
                ):
                    raise ActionError(
                        "http.request timeout must be numeric"
                    )
                timeout = float(raw_timeout)

            raw_body = arguments.get("body")
            raw_json = arguments.get("json")
            if raw_body is not None and raw_json is not None:
                raise ActionError(
                    "http.request body and json are mutually exclusive"
                )

            kwargs: dict[str, object] = {
                "headers": raw_headers,
                "timeout": timeout,
            }
            if raw_body is not None:
                if not isinstance(raw_body, str):
                    raise ActionError(
                        "http.request body must be a string"
                    )
                kwargs["body"] = raw_body.encode("utf-8")
            elif raw_json is not None:
                kwargs["json_body"] = raw_json

            response = adapter.request(
                method,
                url,
                **kwargs,
            )
            return {
                "url": response.url,
                "status": response.status,
                "reason": response.reason,
                "headers": tuple(
                    {
                        "name": name,
                        "value": value,
                    }
                    for name, value in response.headers
                ),
                "body": response.body.decode(
                    "utf-8",
                    errors="replace",
                ),
                "ok": response.ok,
            }

        self.register(
            "http.request",
            adapter.capability,
            request,
            contract=standard_action_contract(
                "http.request"
            ),
        )


def _required_string(
    arguments: dict[str, Value],
    key: str,
    operation: str,
) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value:
        raise ActionError(
            f"{operation} requires non-empty string field {key!r}"
        )
    return value


__all__ = [
    "ActionCapabilityMismatch",
    "ActionError",
    "ActionRegistry",
    "ActionSpec",
    "ActionUnavailable",
    "standard_action_manifest",
]
