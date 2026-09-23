<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->

# RFC 0016: Deterministic Project Templates

## Summary

VECTIS provides a small built-in catalog of deterministic project templates that can be inspected and explicitly materialized without remote discovery or implicit execution.

## Problem

Canonical examples demonstrate language syntax, and `vectis init` creates one fixed project scaffold. Operators also need reusable starting points for common project shapes without copying examples by hand or depending on an external template service.

A template system must preserve VECTIS determinism and explicit authority. Selecting a template must never download code, discover remote packages, execute a mission, or activate an action profile.

## Template contract

`vectis.templates` defines the built-in template catalog.

Each template has a stable identifier, title, description, and ordered set of relative file paths with UTF-8 text content.

The initial catalog contains:

1. `starter`, a small mission with one reusable pure function.
2. `release-gate`, a staged release decision workflow with no external authority.
3. `filesystem-action`, an explicit filesystem action plus a reviewable example action profile.

`template_catalog()` returns metadata and relative file names without materializing files.

`template_preview(NAME)` returns the deterministic file content and a SHA-256 digest for each file.

`write_project_template(NAME, ROOT)` writes exactly the selected built-in template. Existing files cause the operation to fail before template content is written unless `force=True` is selected.

## Path safety

Template file names must be relative paths without empty, current-directory, or parent-directory components.

Each destination is resolved against the requested root and must remain inside that root.

A template destination that is already a symbolic link is rejected. Existing regular files are replaced only when force mode is explicit.

## CLI

`vectis templates` lists the built-in template catalog.

`vectis templates NAME` returns one deterministic preview.

`vectis init PATH --template NAME` materializes one selected template.

`vectis init PATH` keeps its existing scaffold behavior for compatibility.

## Editor integration

The language server advertises `vectis.templates.inspect` through `workspace/executeCommand`.

Clients send one argument object. An omitted `name` returns the catalog. A string `name` returns one template preview.

The command is read-only and does not create project files.

## Authority and security

Templates are package-local data. No network request, remote registry lookup, repository clone, plugin execution, or package installation occurs.

An included action profile is an example file only. It is never selected automatically. Runtime authority still requires the existing explicit execution options.

Template inspection does not compile or execute template missions. Materialization writes text files only.

## Determinism

The catalog order is stable by template identifier.

Preview content is byte-stable UTF-8 text with per-file SHA-256 digests.

Materializing the same template into empty destinations produces the same file set and content.

## Compatibility

Source syntax, compiler IR, runtime scheduling, module loading, capability enforcement, action-profile selection, receipt schemas, package version, and published releases do not change.

The default `vectis init` scaffold remains available unchanged.

## Test strategy

Tests cover stable catalog ordering, deterministic previews and digests, path safety, collision behavior, compilation of every materialized template, CLI listing and creation, read-only editor inspection, repository policy, and the complete repository suite.
