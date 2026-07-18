# Current development state

This document distinguishes the coherent export path from the experimental
host-side code. It is an evidence-based snapshot of the repository on
18-07-2026, not a promise that every script forms one supported workflow.

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

Unsupported host-side code lives under `experimental/` (legacy semantic/vector
search, LLM/agent experiments, older duplicate implementations, and legacy
ad-hoc test scripts). See [experimental/README.md](../experimental/README.md).
Nothing in the supported workflow imports it. Optional semantic retrieval now
uses `tools/semantic_index.py` and `tools/hybrid_search.py` exclusively.

The analysis/agent cluster has now been moved to `experimental/` as well
(`analyze_binary.py`, `tool_agent.py`, `local_agent.py`, `investigation_loop.py`,
`context_engine.py`, `query_engine.py`, `analysis_agent.py`, `callgraph_agent.py`,
`agent_controller.py`, `agent_executor.py`, `ai_answer.py`, `ai_planner.py`,
`build_chunks.py`, and `vector_indexer.py`). These modules called into the
supported report subsystem through bare sibling imports; the move rewrote those
to package-qualified imports (`from tools.X` for the supported dependencies they
use, `from experimental.X` for their experimental siblings), so `tools/` now
holds only the supported surface.

The supported host surface is: the evidence store (`tools/local_evidence.py`)
and its adapters (`binary_agent_server.py`, `binary_agent_mcp_server.py`,
`tools/evidence_tools.py`, `tools/evidence_client.py`, `tools/analysis_tools.py`);
the validation, derived-index, and annotation tools (`tools/validate_export.py`,
`tools/build_local_index.py`, `tools/build_class_registry.py`,
`tools/build_name_review_queue.py`, `tools/function_annotations.py`); the
deterministic report tool (`tools/start_investigation.py` with
`tools/binary_triage.py`, `tools/startup_analyzer.py`,
`tools/investigation_memory.py`, `tools/evidence_collector.py`, and
`tools/report_generator.py`); `tools/generate_evidence_pack.py`; the shared
project layout (`project_layout.py`); networking reconstruction
(`tools/network_reconstruction.py`, `tools/network_capture.py`,
`tools/protocol_contract.py`); isolated unattended naming
(`tools/naming_candidates.py`, `tools/autonomous_naming_runner.py`) with an
explicit Ollama context-window control, compact prompts, and guard-compatible
evidence-reference lists; performance
benchmarking (`tools/benchmark_search.py`); and mutable-artifact schema tooling
(`tools/migrate_artifacts.py`).

## Known integration gaps

These are the remaining backlog items after the initial target reliability
pass.

| Area | Observed behaviour | Consequence |
| --- | --- | --- |
| Post-processing | `revhub post-process` rebuilds `ai_context.json`, Markdown, `index.json`, and function summaries from a completed export. | It does not require a live Ghidra `Program`. |
| Legacy semantic scripts | Older vector/query modules remain under `experimental/` for reference. | Supported routes use one portable per-export index; old embedding builders delegate to it. |
| LLM agents | The supported runner handles OpenAI-compatible and Ollama endpoints with budgets, retries, dry runs, and resumable state. | Unattended output remains disposable until separate review. |
| Packaging | Baseline dependencies are locked; the optional semantic backend pins sentence-transformers. | `samples/tiny_export` remains the end-to-end fixture. |

## Recommended development order

1. Decide whether `ai_chunks.json` should be enabled by default for a target
   export; it is wired into the pipeline but remains opt-in because it can be
   large.
2. Add provider-specific local-model transcript fixtures discovered during
   real long-running sessions.
3. Add target-specific protocol messages and recreation test vectors as each
   reverse-engineering project confirms them.

The local evidence layer exposes raw evidence plus accepted reversible
annotations and is the preferred interactive route, whether accessed through
HTTP, MCP, or in-process Python. Semantic/LLM endpoints remain optional leads
only. In particular, names and decompiler output are helpful clues, not ground
truth unless an accepted annotation records the concrete evidence.
