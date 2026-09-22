# GHOST FIVE // VECTIS
# Serves the Mission Readiness demo application powered by the VECTIS engine.

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import ipaddress
import json
import mimetypes
import threading
from typing import Any

from vectis import __version__
from vectis.browser import open_local_url
from vectis.compiler import compile_program
from vectis.parser import parse
from vectis.product import execution_report_html, execution_timeline, graph_summary
from vectis.runtime import Runtime


def _jsonable(value: Any) -> Any:
    """Convert runtime dataclasses and enums into JSON safe structures."""
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


def _is_loopback(host: str) -> bool:
    """Return whether a bind target is local to the current system."""
    if host in {"", "localhost"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validated_text(value: str, label: str) -> str:
    """Validate text that will be represented by the current string grammar."""
    clean = value.strip()
    if not clean:
        raise ValueError(f"{label} must not be empty")
    if len(clean) > 120:
        raise ValueError(f"{label} must be 120 characters or fewer")
    if any(character in clean for character in ('"', "\\", "\r", "\n")):
        raise ValueError(
            f"{label} cannot contain quotes, backslashes, or line breaks"
        )
    return clean


def _bounded_score(value: int, label: str) -> int:
    """Validate one percentage-style application input."""
    if not 0 <= value <= 100:
        raise ValueError(f"{label} must be between 0 and 100")
    return value


def build_readiness_source(
    *,
    mission: str,
    operator: str,
    ready: bool,
    quality: int,
    risk: int,
    navigation_ready: bool = True,
    communications_ready: bool = True,
    range_clear: bool = True,
    payload_ready: bool = True,
    fuel_percent: int = 96,
    weather_score: int = 92,
    vehicle: str = "VECTIS-01",
) -> str:
    """Build the Launch Control mission from structured application input."""
    quality = _bounded_score(quality, "quality")
    risk = _bounded_score(risk, "risk")
    fuel_percent = _bounded_score(fuel_percent, "fuel_percent")
    weather_score = _bounded_score(weather_score, "weather_score")

    mission_text = json.dumps(
        _validated_text(mission, "mission")
    )
    operator_text = json.dumps(
        _validated_text(operator, "operator")
    )
    vehicle_text = json.dumps(
        _validated_text(vehicle, "vehicle")
    )

    def boolean(value: bool) -> str:
        return "true" if value else "false"

    return (
        f"mission {mission_text} {{\n"
        "    stage \"Telemetry\" {\n"
        f"        source operator {operator_text};\n"
        f"        source vehicle {vehicle_text};\n"
        f"        source flight_systems_ready {boolean(ready)};\n"
        f"        source navigation_ready {boolean(navigation_ready)};\n"
        f"        source communications_ready {boolean(communications_ready)};\n"
        f"        source range_clear {boolean(range_clear)};\n"
        f"        source payload_ready {boolean(payload_ready)};\n"
        f"        source quality {quality};\n"
        f"        source risk {risk};\n"
        f"        source fuel_percent {fuel_percent};\n"
        f"        source weather_score {weather_score};\n"
        "    }\n"
        "\n"
        "    stage \"Gate computation\" {\n"
        "        let systems_gate all_true(flight_systems_ready, navigation_ready, communications_ready);\n"
        "        let environment_gate range_clear && weather_score >= 75;\n"
        "        let fuel_gate fuel_percent >= 90;\n"
        "        let payload_gate payload_ready && quality >= 85;\n"
        "        let risk_gate risk <= 30;\n"
        "        let readiness_score round(average(quality, weather_score, fuel_percent, 100 - risk), 1);\n"
        "        let launch_authorized all_true(systems_gate, environment_gate, fuel_gate, payload_gate, risk_gate);\n"
        "        let launch_status if_else(launch_authorized, \"GO\", \"HOLD\");\n"
        "    }\n"
        "\n"
        "    stage \"Input invariants\" {\n"
        "        assert quality >= 0 && quality <= 100;\n"
        "        assert risk >= 0 && risk <= 100;\n"
        "        assert fuel_percent >= 0 && fuel_percent <= 100;\n"
        "        assert weather_score >= 0 && weather_score <= 100;\n"
        "    }\n"
        "\n"
        "    stage \"Gate results\" {\n"
        "        when systems_gate {\n"
        "            publish \"SYSTEMS // GO\";\n"
        "        } otherwise {\n"
        "            publish \"SYSTEMS // HOLD\";\n"
        "        }\n"
        "\n"
        "        when environment_gate {\n"
        "            publish \"ENVIRONMENT // GO\";\n"
        "        } otherwise {\n"
        "            publish \"ENVIRONMENT // HOLD\";\n"
        "        }\n"
        "\n"
        "        when fuel_gate {\n"
        "            publish concat(\"FUEL // \", string(fuel_percent), \"%\");\n"
        "        } otherwise {\n"
        "            publish \"FUEL // HOLD\";\n"
        "        }\n"
        "\n"
        "        when payload_gate {\n"
        "            publish \"PAYLOAD // GO\";\n"
        "        } otherwise {\n"
        "            publish \"PAYLOAD // HOLD\";\n"
        "        }\n"
        "\n"
        "        when risk_gate {\n"
        "            publish concat(\"RISK // \", string(risk));\n"
        "        } otherwise {\n"
        "            publish \"RISK // HOLD\";\n"
        "        }\n"
        "    }\n"
        "\n"
        "    stage \"Launch decision\" {\n"
        "        when launch_authorized {\n"
        "            publish concat(vehicle, \" // \", launch_status, \" FOR LAUNCH // READINESS \", string(readiness_score));\n"
        "        } otherwise {\n"
        "            publish concat(vehicle, \" // HOLD // READINESS \", string(readiness_score));\n"
        "        }\n"
        "    }\n"
        "}\n"
    )


def _execute_readiness(
    *,
    mission: str,
    operator: str,
    ready: bool,
    quality: int,
    risk: int,
    navigation_ready: bool = True,
    communications_ready: bool = True,
    range_clear: bool = True,
    payload_ready: bool = True,
    fuel_percent: int = 96,
    weather_score: int = 92,
    vehicle: str = "VECTIS-01",
) -> tuple[str, object, object | None]:
    """Compile and execute one Launch Control scenario."""
    source = build_readiness_source(
        mission=mission,
        operator=operator,
        ready=ready,
        quality=quality,
        risk=risk,
        navigation_ready=navigation_ready,
        communications_ready=communications_ready,
        range_clear=range_clear,
        payload_ready=payload_ready,
        fuel_percent=fuel_percent,
        weather_score=weather_score,
        vehicle=vehicle,
    )
    program = parse(source, file="<vectis-launch-control>")
    compiled = compile_program(program)
    runtime = (
        Runtime(compiled.graph).execute()
        if compiled.graph is not None
        else None
    )
    return source, compiled, runtime


def run_readiness(
    *,
    mission: str,
    operator: str,
    ready: bool,
    quality: int,
    risk: int,
    navigation_ready: bool = True,
    communications_ready: bool = True,
    range_clear: bool = True,
    payload_ready: bool = True,
    fuel_percent: int = 96,
    weather_score: int = 92,
    vehicle: str = "VECTIS-01",
) -> dict[str, object]:
    """Compile and execute the Launch Control application through VECTIS."""
    source, compiled, runtime = _execute_readiness(
        mission=mission,
        operator=operator,
        ready=ready,
        quality=quality,
        risk=risk,
        navigation_ready=navigation_ready,
        communications_ready=communications_ready,
        range_clear=range_clear,
        payload_ready=payload_ready,
        fuel_percent=fuel_percent,
        weather_score=weather_score,
        vehicle=vehicle,
    )
    if compiled.graph is None or runtime is None:
        return {
            "source": source,
            "diagnostics": [
                item.to_dict()
                for item in compiled.diagnostics
            ],
            "graph": None,
            "runtime": None,
        }

    return {
        "source": source,
        "diagnostics": [
            item.to_dict()
            for item in compiled.diagnostics
        ],
        "graph": compiled.graph.to_dict(),
        "summary": graph_summary(compiled.graph),
        "timeline": execution_timeline(compiled.graph, runtime),
        "runtime": _jsonable(runtime),
    }


def readiness_report_html(
    *,
    mission: str,
    operator: str,
    ready: bool,
    quality: int,
    risk: int,
    navigation_ready: bool = True,
    communications_ready: bool = True,
    range_clear: bool = True,
    payload_ready: bool = True,
    fuel_percent: int = 96,
    weather_score: int = 92,
    vehicle: str = "VECTIS-01",
) -> str:
    """Return a standalone proof report for one Launch Control scenario."""
    _source, compiled, runtime = _execute_readiness(
        mission=mission,
        operator=operator,
        ready=ready,
        quality=quality,
        risk=risk,
        navigation_ready=navigation_ready,
        communications_ready=communications_ready,
        range_clear=range_clear,
        payload_ready=payload_ready,
        fuel_percent=fuel_percent,
        weather_score=weather_score,
        vehicle=vehicle,
    )
    if compiled.graph is None or runtime is None:
        raise ValueError("Launch Control mission did not compile")
    return execution_report_html(
        compiled.graph,
        runtime,
        mission_name=mission,
        source_name="<vectis-launch-control>",
    )

class DemoHandler(BaseHTTPRequestHandler):
    """Serve the branded demo UI and its VECTIS execution endpoint."""

    server_version = "VECTISDemo/0.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(
            _jsonable(payload),
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, payload: str) -> None:
        """Send a standalone VECTIS execution report."""
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 64_000:
            raise ValueError(
                "request body must be between 1 byte and 64 KB"
            )
        payload = json.loads(
            self.rfile.read(length).decode("utf-8")
        )
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(
                200,
                {
                    "service": "vectis-launch-control",
                    "version": __version__,
                    "status": "ok",
                },
            )
            return
        self._serve_asset()

    def do_POST(self) -> None:
        if self.path not in {"/api/run", "/api/report"}:
            self._send_json(404, {"error": "unknown API endpoint"})
            return

        try:
            data = self._read_json()
            kwargs = {
                "mission": str(data.get("mission", "")),
                "operator": str(data.get("operator", "")),
                "ready": bool(data.get("ready", False)),
                "quality": int(data.get("quality", 0)),
                "risk": int(data.get("risk", 0)),
                "navigation_ready": bool(data.get("navigation_ready", False)),
                "communications_ready": bool(data.get("communications_ready", False)),
                "range_clear": bool(data.get("range_clear", False)),
                "payload_ready": bool(data.get("payload_ready", False)),
                "fuel_percent": int(data.get("fuel_percent", 0)),
                "weather_score": int(data.get("weather_score", 0)),
                "vehicle": str(data.get("vehicle", "")),
            }

            if self.path == "/api/report":
                self._send_html(
                    200,
                    readiness_report_html(**kwargs),
                )
                return

            result = run_readiness(**kwargs)
            runtime = result.get("runtime")
            status = (
                200
                if isinstance(runtime, dict)
                and runtime.get("success") is True
                else 422
            )
            self._send_json(status, result)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})

    def _serve_asset(self) -> None:
        relative = (
            "index.html"
            if self.path in {"", "/"}
            else self.path.lstrip("/")
        )
        if ".." in relative.split("/"):
            self._send_json(404, {"error": "not found"})
            return

        root = files("vectis").joinpath("demo_assets")
        target = root.joinpath(relative)
        if not target.is_file():
            self._send_json(404, {"error": "not found"})
            return

        body = target.read_bytes()
        content_type = (
            mimetypes.guess_type(relative)[0]
            or "application/octet-stream"
        )
        if (
            content_type.startswith("text/")
            or content_type == "application/javascript"
        ):
            content_type += "; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_demo_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8775,
    open_browser: bool = True,
    allow_remote: bool = False,
) -> None:
    """Launch the VECTIS Launch Control demonstration application."""
    if not allow_remote and not _is_loopback(host):
        raise ValueError(
            "VECTIS Demo binds to loopback by default; "
            "use --allow-remote for another interface"
        )

    server = ThreadingHTTPServer((host, port), DemoHandler)
    visible_host = (
        "127.0.0.1"
        if host in {"0.0.0.0", "::"}
        else host
    )
    url = f"http://{visible_host}:{server.server_port}/"

    print(f"VECTIS Launch Control {__version__}")
    print(f"Listening on {url}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(
            0.25,
            lambda: open_local_url(url),
        ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
