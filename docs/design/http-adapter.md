<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# VECTIS HTTP Adapter

## Purpose

`HttpAdapter` provides the explicit VECTIS HTTP capability boundary. It accepts a structured HTTP request and returns a structured response without granting process execution or unrestricted external authority.

## Structured request model

Requests use `HttpRequest` rather than an opaque command or request string. The request records the HTTP method, URL, headers, and optional binary body as explicit fields.

Convenience request helpers construct the same structured request model before sending it.

## URL boundary

Only `http` and `https` URL schemes are accepted. A URL without a hostname is invalid.

The adapter must deny requests whose URL scheme falls outside the supported HTTP boundary. Invalid authority is reported through `HttpAccessDenied`.

## Method and body handling

The HTTP method is explicit in the request. Request headers are normalized deterministically, and binary request bodies are preserved without implicit text conversion.

JSON request data is encoded deterministically before transport and is accompanied by the appropriate content type when the helper API is used.

## Response handling

Every completed exchange produces an `HttpResponse` containing the final URL, integer HTTP status, reason text, response headers, and raw response body.

HTTP error status codes remain structured responses. They are not silently converted into transport failures.

Automatic redirect following is disabled so redirect status and location remain visible to the caller.

## JSON handling

`HttpResponse.json()` decodes the response body through the standard JSON decoder. JSON handling is explicit and deterministic; non-JSON response content is not silently reinterpreted as JSON.

## Timeout handling

Every request uses an explicit timeout. `HttpAdapter` defines a default timeout and a maximum timeout.

A per-request timeout must be positive and may not exceed the configured maximum. A network timeout is converted to `HttpTimeoutError`, which is a `TimeoutError` and retains the structured request and timeout value.

## Transport failures

Non-HTTP transport failures are represented by `HttpTransportError`. HTTP status responses are kept separate from connection and transport errors.

## Capability boundary

The public capability identifier is `http`.

Granting HTTP capability does not grant process execution, shell access, filesystem access, arbitrary URL schemes, implicit redirect authority, or unbounded network waits.

## Security and conformance coverage

The automated adapter tests verify the structured request model, explicit method handling, binary request bodies, request headers, JSON request and response handling, HTTP status handling, redirect visibility, URL scheme denial, hostname validation, deterministic repeated execution, timeout enforcement, and maximum-timeout validation.

## Architectural boundary

The HTTP adapter performs HTTP transport only. Process execution remains the responsibility of the process adapter. Filesystem access remains the responsibility of the filesystem adapter.
