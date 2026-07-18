# Project audit and roadmap

Snapshot: 18-07-2026. Scope: supported exporter, evidence store, CLI,
HTTP/MCP, derived tools, tests, packaging, docs, and experimental isolation.

## Completed in this pass

- Unified `%USERPROFILE%` defaults into repo-local per-project workspaces while
  keeping environment, pointer, and explicit-path compatibility.
- Added project discovery/selection and relocation/backup guidance.
- Added static networking lifecycle/reconstruction evidence packs.
- Split unattended naming into disposable runs and explicit review, including
  stale-function protection and per-run progress.
- Fixed eager experimental vector imports in `tools/hybrid_search.py`.
- Corrected stale fixture/path/overnight guidance and expanded user/agent docs.
- Added the supported budgeted local-model runner, runtime capture import,
  reviewed protocol contracts, cross-process locks/revisions, schema migration
  safeguards, performance benchmarking, and one portable semantic backend.
- Completed a real PyGhidra export and full validation of 104 functions into
  the repo-local ignored workspace.

## Findings

| Area | Finding | Status |
| --- | --- | --- |
| Raw export | Portable address-keyed JSON is a sound durable boundary. | Keep stable; validate fully. |
| Query core | CLI, HTTP, MCP, and agents share `LocalEvidenceStore`. | Good; keep adapters thin. |
| Search | Metadata is linear; optional trigram FTS handles bodies. | Appropriate; benchmark huge targets. |
| Writes | Mutable artifacts use advisory locks, revisions, and atomic replacement. | Implemented and cross-process tested. |
| Networking | Static maps, runtime observations, and reviewed protocol contracts are distinct artifacts. | Generic workflow implemented. |
| Naming | Guarded direct promotion was too weak for overnight trust. | Proposal/review stages implemented. |
| Optional stack | Hybrid helper eagerly imported experimental packages. | Fixed with lazy imports. |
| Packaging/docs | Shared layout was absent and fixture docs were stale. | Fixed. |

## Remaining target-specific work

The generic repository-level backlog is implemented: locking/revisions,
runtime-capture schema, reviewed protocol contracts, repeatable benchmarking,
one pinned portable semantic backend, compatibility wrappers for old embedding
builders, a supported budgeted local runner, and schema audit/migration tooling.

Remaining work depends on real targets and real local-model sessions:

1. Create reviewed protocol messages and encode/decode test vectors as evidence
   confirms them for each target.
2. Record benchmark baselines on several real 100k-function exports.
3. Add provider-specific transcript fixtures for edge cases encountered during
   real overnight runs.
4. Add future schema migrations only when a schema actually changes.

## Validation standard

Run host tests, sample validation, CLI import/help smoke checks, and at least one
real export validation when exporter behavior changes. Separate “wired” from
“runtime/play-tested” in handoffs.
