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

## Findings

| Area | Finding | Status |
| --- | --- | --- |
| Raw export | Portable address-keyed JSON is a sound durable boundary. | Keep stable; validate fully. |
| Query core | CLI, HTTP, MCP, and agents share `LocalEvidenceStore`. | Good; keep adapters thin. |
| Search | Metadata is linear; optional trigram FTS handles bodies. | Appropriate; benchmark huge targets. |
| Writes | Replace-based annotation/run writes are crash-resistant. | Concurrent-writer locking is backlog. |
| Networking | Packet tracing existed, but no lifecycle/recreation artifact. | Static pack implemented. |
| Naming | Guarded direct promotion was too weak for overnight trust. | Proposal/review stages implemented. |
| Optional stack | Hybrid helper eagerly imported experimental packages. | Fixed with lazy imports. |
| Packaging/docs | Shared layout was absent and fixture docs were stale. | Fixed. |

## Prioritised backlog

1. Add advisory locks or compare-and-swap revisions for concurrent writers.
2. Add an optional runtime-capture import schema for authorised correlation.
3. Add reviewed protocol-contract artifacts and recreation fixture tests.
4. Benchmark metadata search on several 100k-function exports before adding DB complexity.
5. Choose one semantic backend, pin it, and retire duplicates.
6. Repair/remove experimental `build_embeddings.py` config mismatch.
7. Add real local-model transcript fixtures for malformed calls, compaction,
   retries, and reviewer disagreement.
8. Add schema migration tools before changing raw/overlay formats.

## Validation standard

Run host tests, sample validation, CLI import/help smoke checks, and at least one
real export validation when exporter behavior changes. Separate “wired” from
“runtime/play-tested” in handoffs.
