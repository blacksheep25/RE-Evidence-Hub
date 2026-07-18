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
- `experimental/function_ghidra_binary_analyst.py` only returns a prompt
  template for an Open WebUI/Ollama-style function integration.  It does not read
  the export folder or invoke a search service.

## Supported surface vs experimental

Unsupported host-side code lives under `experimental/` (semantic/vector search,
embeddings, LLM/agent experiments, older duplicate implementations, and legacy
ad-hoc test scripts). See [experimental/README.md](../experimental/README.md).
Nothing in the supported workflow imports it at import time; the only link is the
optional semantic backend `tools/hybrid_search.py`, which imports
`experimental.ai_tools.*` lazily.

Some experimental analysis/agent modules **remain under `tools/`** because they
share dependencies with the supported deterministic report tool
`tools/start_investigation.py` through bare sibling imports; splitting them
cleanly is a separate change. Treat these as experimental (leads only):
`analyze_binary.py`, `tool_agent.py`, `local_agent.py`, `investigation_loop.py`,
`context_engine.py`, `query_engine.py`, `analysis_agent.py`, `callgraph_agent.py`,
`agent_controller.py`, `agent_executor.py`, `ai_answer.py`, `ai_planner.py`,
`build_chunks.py`, and `vector_indexer.py`.

The supported host surface is: the evidence store (`tools/local_evidence.py`)
and its adapters (`binary_agent_server.py`, `binary_agent_mcp_server.py`,
`tools/evidence_tools.py`, `tools/evidence_client.py`, `tools/analysis_tools.py`);
the validation, derived-index, and annotation tools (`tools/validate_export.py`,
`tools/build_local_index.py`, `tools/build_class_registry.py`,
`tools/build_name_review_queue.py`, `tools/function_annotations.py`); the
deterministic report tool (`tools/start_investigation.py` with
`tools/binary_triage.py`, `tools/startup_analyzer.py`,
`tools/investigation_memory.py`, `tools/evidence_collector.py`, and
`tools/report_generator.py`); and `tools/generate_evidence_pack.py`.

## Known integration gaps

These are the remaining backlog items after the initial target reliability
pass.

| Area | Observed behaviour | Consequence |
| --- | --- | --- |
| Post-processing | `post_process.py` rebuilds Markdown, `index.json`, and function summaries only. | It cannot create `ai_context.json`, which depends on a live `Program`. |
| Chroma implementations | The normal host route now uses `host_config.py`, but the Docker-oriented `experimental/ai_tools/build_embeddings.py` still has separate `/data` settings. | The Docker helper must be deliberately aligned before it is used. |
| Docker embedding helper | `experimental/ai_tools/build_embeddings.py` imports `USE_FUNCTION_RANKER` and `RANK_LIMIT` from the sibling `experimental/ai_tools/config.py`, which does not define them. | That helper will raise an import error when run from its own directory. (Now clearly under `experimental/`.) |
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
