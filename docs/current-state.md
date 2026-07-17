# Current development state

This document distinguishes the coherent export path from the experimental
host-side code. It is an evidence-based snapshot of the repository on
14-07-2026, not a promise that every script forms one supported workflow.

## Supported baseline

The best foundation for continued development is:

1. Run `run_exporter.py` in Ghidra.
2. Run `tools/validate_export.py <export> --full`, then validate
   `export_report.json` and the raw JSON data, especially
   `functions/`, `imports.json`, `strings.json`, and `callgraph.json`.
3. Use `binary_agent_server.py`, `binary_agent_mcp_server.py`, or
   `tools/evidence_tools.py` for normal read-only local evidence queries.
   Build `local_evidence.sqlite3` with `tools/build_local_index.py` when
   decompiler-body search is needed often. Build `class_registry.json` and
   `name_review_queue.json` when class/vtable context or name-triage context
   is needed; both are derived review artifacts and neither changes an active
   annotation.
4. Use `tools/start_investigation.py <export>` for deterministic report-style
   analysis, or consume the JSON directly from another tool.

This path does not require Chroma or an LLM API.  It is also the path whose
outputs are easiest to reproduce from a saved Ghidra export.

`EvidenceCollector` version 2 streams function records and joins imports and
strings through their exported function references. The full 73,927-function
target export completed this stage in about 11 seconds during the initial
validation run; it no longer performs a cross-product scan of every function
against every string and import.

## Intentional distinctions

- `AISummaryExporter` writes Markdown pages.  It does **not** call an AI model.
- `FunctionSummaryExporter` writes simple API-name heuristics such as "Likely
  network related function."  It does **not** produce a semantic model
  analysis.
- `ai_instructions.md` is a prompt/reference guide for analysing an exported
  binary; it is not consumed automatically by the scripts.
- `function_ghidra_binary_analyst.py` only returns a prompt template for an
  Open WebUI/Ollama-style function integration.  It does not read the export
  folder or invoke a search service.

## Known integration gaps

These are the remaining backlog items after the initial target reliability
pass.

| Area | Observed behaviour | Consequence |
| --- | --- | --- |
| Post-processing | `post_process.py` rebuilds Markdown, `index.json`, and function summaries only. | It cannot create `ai_context.json`, which depends on a live `Program`. |
| Chroma implementations | The normal host route now uses `host_config.py`, but the Docker-oriented `ai_tools/build_embeddings.py` still has separate `/data` settings. | The Docker helper must be deliberately aligned before it is used. |
| Docker embedding helper | `ai_tools/build_embeddings.py` imports `USE_FUNCTION_RANKER` and `RANK_LIMIT` from the sibling `ai_tools/config.py`, which does not define them. | That helper will raise an import error when run from its own directory. |
| LLM agents | `tool_agent.py` implements the interactive JSON tool loop over `EvidenceTools`, which uses the same `LocalEvidenceStore` core as the HTTP and MCP adapters. `local_agent.py` is only a compatibility entry point for the same agent. | Agent evidence, HTTP evidence, and MCP evidence now share accepted annotations and derived context. |
| Packaging | Dependencies are split into `requirements-core.txt` (baseline), `requirements-optional.txt` (experimental semantic/vector), and a pinned `requirements.lock` for the baseline. | The baseline is now reproducible; the optional stack remains unpinned. A fixture *export* for end-to-end regression is still absent (unit fixtures exist in `tests/`). |

## Recommended development order

1. Add a fixture *export* so the validated schema and search behaviour are
   regression-tested end to end. (A pinned `requirements.lock` for the baseline
   now exists; the `tests/` fixtures cover the store contract but not a full
   on-disk export.)
2. Decide whether `ai_chunks.json` should be enabled by default for a target
   export; it is wired into the pipeline but remains opt-in because it can be
   large.
3. Choose one semantic-search implementation (local vectors or Chroma) and
   retire or clearly isolate the other.
4. Expand the evidence-backed agent tests around real model tool-call
   transcripts before treating local LLM runs as a supported automated mode.

The local evidence layer exposes raw evidence plus accepted reversible
annotations and is the preferred interactive route, whether accessed through
HTTP, MCP, or in-process Python. Semantic/LLM endpoints remain optional leads
only. In particular, names and decompiler output are helpful clues, not ground
truth unless an accepted annotation records the concrete evidence.
